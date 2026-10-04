"""
Fake Certificate Detection Using Machine Learning - Flask web application.

Run:  python app.py      then open  http://127.0.0.1:5000
"""
import json
import os
import uuid

from flask import Flask, flash, redirect, render_template, request, url_for
from PIL import Image
from werkzeug.utils import secure_filename

from config import Config
from database import database as db
from ml.predictor import ModelNotFoundError
from services import ocr_service
from services.analyzer import analyze_file
from services.image_service import ImageProcessingError

app = Flask(__name__)
app.config.from_object(Config)

SIGNATURES = {
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "pdf": [b"%PDF-"],
}


# --------------------------------------------------------------------------
# Start-up: create database, train a demo model if none exists
# --------------------------------------------------------------------------
def bootstrap():
    try:
        db.init_db()
    except db.DatabaseError as exc:
        print(f"[WARNING] Database could not be initialised: {exc}")
    if not os.path.exists(Config.MODEL_PATH):
        print("[INFO] No trained model found - creating a demo model automatically...")
        try:
            from ml.dataset_generator import generate_dataset
            from ml.train_model import train_model
            generate_dataset()
            train_model()
        except Exception as exc:  # keep the app running, show a friendly message later
            print(f"[WARNING] Automatic training failed: {exc}")


def load_model_info():
    try:
        with open(Config.METRICS_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


# --------------------------------------------------------------------------
# Upload validation
# --------------------------------------------------------------------------
def validate_and_save(file):
    """Returns (saved_path, extension, error_message)."""
    if file is None or not file.filename:
        return None, None, "Please choose a certificate file first."

    original = secure_filename(file.filename)
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in Config.ALLOWED_EXTENSIONS:
        return None, None, "Unsupported file type. Please upload a JPG, JPEG, PNG or PDF file."

    header = file.stream.read(16)
    file.stream.seek(0, os.SEEK_END)
    size = file.stream.tell()
    file.stream.seek(0)
    if size == 0:
        return None, None, "The uploaded file is empty."
    if size > Config.MAX_FILE_SIZE_MB * 1024 * 1024:
        return None, None, f"The file is too large. Maximum allowed size is {Config.MAX_FILE_SIZE_MB} MB."
    if not any(header.startswith(sig) for sig in SIGNATURES[ext]):
        return None, None, "The file content does not match its extension. Upload a real image or PDF."

    stored = f"{uuid.uuid4().hex[:10]}_{original}"
    path = os.path.join(Config.UPLOAD_FOLDER, stored)
    file.save(path)

    if ext in ("jpg", "jpeg", "png"):
        try:
            with Image.open(path) as img:
                img.verify()
        except Exception:
            os.remove(path)
            return None, None, "The image is corrupt or not a valid image file."
    return path, ext, None


def _cleanup(path):
    """Remove an upload (and files generated from it) after a failed analysis."""
    stem = os.path.splitext(os.path.basename(path))[0]
    for name in os.listdir(Config.UPLOAD_FOLDER):
        if name.startswith(stem):
            try:
                os.remove(os.path.join(Config.UPLOAD_FOLDER, name))
            except OSError:
                pass


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@app.route("/")
def index():
    try:
        stats = db.get_stats()
    except db.DatabaseError:
        stats = {"total": 0, "suspicious": 0, "genuine": 0}
    return render_template("index.html", stats=stats, model_info=load_model_info(),
                           tesseract_ok=ocr_service.is_tesseract_available(),
                           max_mb=Config.MAX_FILE_SIZE_MB)


@app.route("/analyze", methods=["POST"])
def analyze():
    path, ext, error = validate_and_save(request.files.get("certificate"))
    if error:
        flash(error, "error")
        return redirect(url_for("index"))

    original_name = secure_filename(request.files["certificate"].filename)
    try:
        result = analyze_file(path, original_name, ext)
    except ocr_service.OCRUnavailableError as exc:
        _cleanup(path)
        flash(str(exc), "error")
        return redirect(url_for("index"))
    except ModelNotFoundError as exc:
        _cleanup(path)
        flash(str(exc), "error")
        return redirect(url_for("index"))
    except ImportError:
        _cleanup(path)
        flash("A required library is missing (PyMuPDF for PDFs). Run: pip install -r requirements.txt", "error")
        return redirect(url_for("index"))
    except Exception as exc:
        _cleanup(path)
        if exc.__class__.__name__ == "PDFProcessingError" or isinstance(exc, ImageProcessingError):
            flash(str(exc), "error")
        else:
            app.logger.exception("Analysis failed")
            flash("Something went wrong while analysing this file. Please try another file.", "error")
        return redirect(url_for("index"))

    try:
        analysis_id = db.save_analysis(result)
    except db.DatabaseError:
        app.logger.exception("Could not save analysis")
        flash("The analysis worked, but it could not be saved to the history database.", "warning")
        return render_template("result.html", result=result, analysis_id=None,
                               model_info=load_model_info(), saved_at=None)
    return redirect(url_for("result", analysis_id=analysis_id))


@app.route("/result/<int:analysis_id>")
def result(analysis_id):
    try:
        row, data = db.get_analysis(analysis_id)
    except db.DatabaseError:
        flash("The history database could not be read.", "error")
        return redirect(url_for("index"))
    if row is None or data is None:
        flash("That analysis was not found. It may have been deleted.", "warning")
        return redirect(url_for("history"))
    return render_template("result.html", result=data, analysis_id=analysis_id,
                           model_info=load_model_info(), saved_at=row["upload_time"])


@app.route("/history")
def history():
    try:
        rows = db.get_all_analyses()
    except db.DatabaseError:
        flash("The history database could not be read.", "error")
        rows = []
    return render_template("history.html", rows=rows)


@app.route("/delete/<int:analysis_id>", methods=["POST"])
def delete(analysis_id):
    try:
        db.delete_analysis(analysis_id)
        flash("Analysis deleted.", "success")
    except db.DatabaseError:
        flash("Could not delete that record.", "error")
    return redirect(url_for("history"))


@app.route("/clear", methods=["POST"])
def clear():
    try:
        db.clear_all()
        flash("All history and stored files were deleted.", "success")
    except db.DatabaseError:
        flash("Could not clear the history.", "error")
    return redirect(url_for("history"))


@app.route("/about")
def about():
    return render_template("about.html", model_info=load_model_info())


# --------------------------------------------------------------------------
# Friendly error pages (no stack traces for normal users)
# --------------------------------------------------------------------------
@app.errorhandler(413)
def too_large(_):
    flash(f"The file is too large. Maximum allowed size is {Config.MAX_FILE_SIZE_MB} MB.", "error")
    return redirect(url_for("index"))


@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="That page does not exist."), 404


@app.errorhandler(500)
def server_error(_):
    return render_template("error.html", code=500,
                           message="Something went wrong on the server. Please try again."), 500


bootstrap()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("FLASK_HOST", "0.0.0.0"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
