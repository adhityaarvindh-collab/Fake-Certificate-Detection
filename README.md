# Fake Certificate Detection Using Machine Learning

A web application that analyses an uploaded certificate (JPG, JPEG, PNG or PDF) with **OCR, image processing, text analysis, layout analysis, QR-code decoding, metadata inspection and a Random Forest classifier**, and rates it as **GENUINE-LIKELY** or **SUSPICIOUS** with a model confidence percentage.

> **Important:** machine learning cannot mathematically prove that a certificate is forged or genuine. This project reports *suspicious patterns* and *model confidence*. Final verification must always be done with the issuing institution or a trusted database.

---

## 1. Project overview

| Stage | What happens | Library |
|------|--------------|---------|
| Upload | File type, size, content signature and integrity are validated | Flask, Pillow |
| PDF handling | Selectable text is extracted, pages are rendered to images | PyMuPDF |
| OCR | Text is read and cleaned; name, institution, ID, course, date, grade are extracted | Tesseract, pytesseract |
| Image analysis | Resize, grayscale, denoise, contrast (CLAHE), threshold, edges; brightness, contrast, edge density, sharpness, noise, colour | OpenCV |
| Layout analysis | Text blocks, logo-like and signature-like regions | OpenCV |
| QR code | Detected and decoded (never treated as proof) | OpenCV |
| Metadata | EXIF / PDF metadata shown as supporting information | Pillow, PyMuPDF |
| Classification | 24 features -> Random Forest -> prediction + confidence | scikit-learn |
| History | Every analysis is stored | SQLite |

## 2. Features

- Modern, responsive blue/white interface with drag-and-drop upload
- Prediction badge, confidence chart, feature-importance chart
- Extracted fields table, document checklist, plain-language "potential indicators"
- Visual evidence: original, edge map and detected layout regions
- QR decoding with safe (non-clickable) display of the URL
- Metadata panel with a clear disclaimer
- History page with search, view and delete; printable result page
- Friendly error messages (no Python stack traces shown to users)
- Charts also work offline (CSS fallback if Chart.js cannot be loaded)
- If no trained model exists the app trains a demo model automatically

## 3. Technology stack

Python 3.11+, Flask, scikit-learn (RandomForestClassifier), pandas, NumPy, OpenCV, Pillow, Tesseract OCR (pytesseract), PyMuPDF, SQLite, HTML5, CSS3, JavaScript, Chart.js, matplotlib (confusion-matrix picture only).

## 4. Folder structure

```
fake_certificate_detection/
|-- app.py                     Flask routes, upload validation, start-up
|-- config.py                  All settings (paths, limits, Tesseract path)
|-- requirements.txt
|-- README.md
|-- .gitignore
|-- database/
|   |-- database.py            SQLite functions (history)
|-- ml/
|   |-- feature_extractor.py   The 24 features (used for training AND prediction)
|   |-- dataset_generator.py   Creates the SYNTHETIC demo dataset (numbers only)
|   |-- train_model.py         Trains + evaluates the Random Forest, saves the model
|   |-- predictor.py           Loads model, predicts, builds indicators
|   |-- build_real_dataset.py  (optional) builds a dataset from your own labelled files
|   |-- model/certificate_model.pkl   <- created when you train
|-- services/
|   |-- analyzer.py            Runs the whole pipeline for one file
|   |-- ocr_service.py         Tesseract OCR + field extraction
|   |-- image_service.py       OpenCV preprocessing, features, layout
|   |-- pdf_service.py         PyMuPDF text + page rendering
|   |-- qr_service.py          QR detection / decoding
|   |-- metadata_service.py    EXIF / PDF metadata
|-- templates/                 base, index, result, history, about, error
|-- static/css/style.css
|-- static/js/script.js
|-- static/uploads/            uploaded files + generated pictures
|-- dataset/                   certificate_features.csv (generated)
|-- reports/                   model_metrics.json, confusion_matrix.png (generated)
```

## 5. Installation (Windows + VS Code)

### 5.1 Python version
You need **Python 3.11 or newer**. Check with:
```
python --version
```
If it is older (or missing), install from https://www.python.org/downloads/ and tick **"Add python.exe to PATH"** in the installer.

### 5.2 Create the project folder and open it in VS Code
```
mkdir fake_certificate_detection
cd fake_certificate_detection
code .
```
Copy all project files into this folder (keep the sub-folders exactly as shown above). In VS Code open **Terminal -> New Terminal**.

### 5.3 Virtual environment
```
python -m venv venv
venv\Scripts\activate
```
You should now see `(venv)` at the start of the terminal line.
If PowerShell says *"running scripts is disabled"*, run this once and try again:
```
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
(Or use **Command Prompt** instead of PowerShell.)

In VS Code press `Ctrl+Shift+P` -> **Python: Select Interpreter** -> choose the one inside `venv`.

### 5.4 Install the dependencies
```
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5.5 Install Tesseract OCR (separate program, required for scanned images)
1. Download the Windows installer from https://github.com/UB-Mannheim/tesseract/wiki
2. Run it and keep the default folder `C:\Program Files\Tesseract-OCR`.
3. The app finds this folder automatically. Check with a **new** terminal: `tesseract --version`
4. If you installed it somewhere else, open `config.py` and set
   `TESSERACT_CMD = r"D:\Tools\Tesseract-OCR\tesseract.exe"`

(Text-based PDFs work even without Tesseract; images and scanned PDFs need it.)

### 5.6 Generate the demo dataset
```
python ml/dataset_generator.py
```
Creates `dataset/certificate_features.csv` (2000 rows, 24 features, label 0 = Suspicious, 1 = Genuine).

> **The demo dataset is synthetic.** It contains only generated numbers to demonstrate the ML pipeline. It does not contain any real or forged certificate. Replace it with a properly labelled, permission-based dataset for real deployment (section 9).

### 5.7 Train the model
```
python ml/train_model.py
```
This prints accuracy, precision, recall, F1-score, 5-fold cross-validation score and the confusion matrix, saves the model to `ml/model/certificate_model.pkl`, and writes `reports/model_metrics.json` and `reports/confusion_matrix.png`.
(If you skip steps 5.6 and 5.7, the app creates a demo model automatically on first start.)

### 5.8 Run the application
```
python app.py
```

### 5.9 Open it in the browser
Go to **http://127.0.0.1:5000** (stop the server with `Ctrl+C`).

## 6. Quick VS Code checklist

1. Open VS Code  2. Create folder `fake_certificate_detection` and open it  3. Create the sub-folders  4. Create each file  5. Paste the code  6. Open terminal  7. `python -m venv venv` and `venv\Scripts\activate`  8. `pip install -r requirements.txt`  9. `python ml/dataset_generator.py`  10. `python ml/train_model.py`  11. `python app.py`  12. Open http://127.0.0.1:5000

## 7. How the ML pipeline works

1. **Features** - `ml/feature_extractor.py` turns every document into the same 24 numbers:
   *text* (length, words, digits, special characters, ID/date/institution/name/course found, OCR confidence), *image* (width, height, aspect ratio, brightness, contrast, edge density, sharpness, noise, saturation) and *structure* (text density, text regions, QR, logo-like region, signature-like region).
2. **Training** - `train_model.py` loads the CSV, makes an 80/20 **stratified split before anything else** (no data leakage), trains `RandomForestClassifier(n_estimators=200, max_depth=12, class_weight="balanced", random_state=42)` and evaluates only on the unseen 20 %.
3. **Prediction** - `predictor.py` loads the saved model, builds the feature row in the **same column order**, calls `predict_proba` and returns the class with the higher probability. That probability is shown as **model confidence**.
4. **Explanation** - `build_indicators()` adds plain-language observations (low OCR confidence, missing ID, blur, noise...). These are simple rules for explanation only; they are not used by the model.

## 8. Important honesty note about the demo model

The bundled model learns from **synthetic numbers** whose patterns were chosen by the project author (for example genuine records have higher OCR confidence and less noise). It therefore demonstrates *how* the system works, but its accuracy figure says nothing about real certificates. The result page and About page show a "demo model" notice for this reason.

## 9. How to replace the demo dataset

1. Collect certificates **you have permission to use**, verified as genuine or confirmed as fake/tampered.
2. Create these folders and copy the files in:
   ```
   dataset/real/genuine/
   dataset/real/suspicious/
   ```
3. Extract features from them:
   ```
   python ml/build_real_dataset.py
   ```
   This writes `dataset/real_features.csv` (same 24 features + `label`).
4. Train on it:
   ```
   python ml/train_model.py --data dataset/real_features.csv
   ```
5. Restart `python app.py`. The About page now says "User-supplied dataset".

You can also build any CSV yourself as long as it has the 24 feature columns (see `FEATURE_NAMES` in `ml/feature_extractor.py`) and a `label` column (0/1). Use at least a few hundred balanced examples per class.

## 10. Limitations

- Demo model is trained on synthetic data (see section 8).
- Blur, noise and brightness change with cameras and scanners, not only with tampering.
- OCR depends on image quality; field extraction uses simple rules and can miss fields.
- Logo and signature detection are shape heuristics.
- Metadata is often missing or can be edited. A decoded QR code proves nothing by itself.
- The tool cannot confirm that a certificate was really issued; only the issuer can.
- Uploaded files are kept in `static/uploads/` so results can be viewed again; delete them from the History page.
- Only the first 5 pages of a PDF are analysed.

## 11. Future improvements

- Train on a real labelled dataset; try gradient boosting and compare models
- CNN-based tamper / forgery detection and error-level analysis
- Verify extracted ID against an institution API or blockchain registry
- Multi-language OCR, PDF report download, user login
- Deploy with a production server (gunicorn / waitress) and HTTPS

## 12. Viva explanation (questions and short answers)

**Q1. What does your project do?**
It takes a certificate image or PDF, extracts text with OCR, measures image and layout properties, decodes any QR code, and a Random Forest model classifies the document as Genuine-likely or Suspicious with a confidence score.

**Q2. Why do you say "Suspicious" and not "Fake"?**
Machine learning only learns statistical patterns. It cannot prove forgery. A suspicious result means "verify this with the issuer".

**Q3. Why Random Forest?**
It works well on small tabular data, handles features of different scales without normalisation, resists over-fitting by averaging many trees, gives feature importances, and is easy to explain.

**Q4. What is OCR and which tool did you use?**
Optical Character Recognition converts text in images to digital text. I used Tesseract through pytesseract, after OpenCV preprocessing (grayscale, upscaling, CLAHE, denoising).

**Q5. Which features do you use?**
24 features in three groups: text, image and structure (listed in section 7).

**Q6. How do you avoid data leakage?**
The train/test split happens first, with a stratified split and `random_state=42`; the test set is used only for the final metrics, and cross-validation uses only the training part.

**Q7. What do accuracy, precision, recall and F1 mean?**
Accuracy = correct predictions / all predictions. Precision = of the documents predicted genuine, how many truly are. Recall = of the truly genuine, how many were found. F1 = harmonic mean of precision and recall.

**Q8. What is a confusion matrix?**
A 2x2 table of actual versus predicted classes (true/false positives and negatives). It shows which mistakes the model makes.

**Q9. Your dataset is synthetic - is that a problem?**
For a real deployment yes. Here it is used only to demonstrate the pipeline without handling real or forged documents, and the project shows how to replace it (section 9). I state this clearly in the app.

**Q10. How does PDF handling work?**
PyMuPDF opens the PDF, extracts selectable text, and renders pages to PNG. If the PDF is scanned (no text layer), the rendered pages go through OCR.

**Q11. How is the QR code handled?**
OpenCV's QRCodeDetector finds and decodes it. The data is only displayed (never opened automatically) and labelled "external verification required".

**Q12. How is the upload kept secure?**
Extension whitelist, content signature check (magic bytes), Pillow integrity check, size limit, `secure_filename`, unique stored names, files are never executed, no server paths or stack traces are shown.

**Q13. What are the main limitations and future scope?**
See sections 10 and 11.

## 13. Troubleshooting

| Problem | Fix |
|--------|-----|
| `'python' is not recognized` | Reinstall Python and tick *Add to PATH*, or use `py -m venv venv` |
| `venv\Scripts\activate` blocked in PowerShell | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` or use Command Prompt |
| `ModuleNotFoundError: No module named 'cv2'` (or flask, sklearn...) | Activate the venv first, then `pip install -r requirements.txt` |
| Yellow banner "Tesseract OCR was not found" | Install Tesseract (section 5.5) and restart `python app.py`; or set `TESSERACT_CMD` in `config.py` |
| `TesseractNotFoundError` after installing | Open a new terminal, or set `TESSERACT_CMD` to the full path of `tesseract.exe` |
| "The trained model was not found" | Run `python ml/dataset_generator.py` then `python ml/train_model.py` |
| `pip install` fails for PyMuPDF / OpenCV | `python -m pip install --upgrade pip`, then retry; make sure you use 64-bit Python 3.11+ |
| Charts look different / are simple bars | Chart.js loads from the internet; without internet the built-in fallback charts are used |
| "File too large" | Max is 8 MB; change `MAX_FILE_SIZE_MB` in `config.py` |
| Port 5000 already in use | Change `port=5000` at the bottom of `app.py` |
| OCR text is poor | Upload a sharper, higher-resolution image (at least 1000 px wide), straight and well lit |
| Want to reset everything | Stop the app, delete `database/certificates.db`, and the files in `static/uploads/` (or use *Clear all history*) |

---
*Academic project. Not a legal or forensic verification tool.*
