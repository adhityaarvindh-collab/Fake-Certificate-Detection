"""Central configuration for the Fake Certificate Detection project."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # --- Flask ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-secret-key-for-production")

    # --- Paths ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    DATABASE_PATH = os.path.join(BASE_DIR, "database", "certificates.db")
    MODEL_PATH = os.path.join(BASE_DIR, "ml", "model", "certificate_model.pkl")
    DATASET_PATH = os.path.join(BASE_DIR, "dataset", "certificate_features.csv")
    REPORTS_DIR = os.path.join(BASE_DIR, "reports")
    METRICS_PATH = os.path.join(BASE_DIR, "reports", "model_metrics.json")

    # --- Upload rules ---
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf"}
    MAX_FILE_SIZE_MB = 8
    MAX_CONTENT_LENGTH = (MAX_FILE_SIZE_MB + 1) * 1024 * 1024  # Flask hard limit

    # --- Processing ---
    MAX_PDF_PAGES = 5          # only the first N pages of a PDF are analysed
    PDF_RENDER_DPI = 200       # resolution used when a PDF page is turned into an image
    MAX_IMAGE_SIDE = 2000      # larger images are scaled down to this many pixels

    # --- Tesseract ---
    # Prefer an explicit environment variable; otherwise use the standard Windows
    # install path if it exists. This makes the app work immediately after the
    # default Tesseract install without editing code.
    _candidate = os.environ.get("TESSERACT_CMD")
    if not _candidate:
        for _path in (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
        ):
            if os.path.exists(_path):
                _candidate = _path
                break
    TESSERACT_CMD = _candidate or ""

    # --- Labels (0 = suspicious, 1 = genuine) ---
    LABEL_SUSPICIOUS = "SUSPICIOUS"
    LABEL_GENUINE = "GENUINE-LIKELY"


for _folder in (Config.UPLOAD_FOLDER, Config.REPORTS_DIR,
                os.path.dirname(Config.DATABASE_PATH),
                os.path.dirname(Config.MODEL_PATH),
                os.path.dirname(Config.DATASET_PATH)):
    os.makedirs(_folder, exist_ok=True)
