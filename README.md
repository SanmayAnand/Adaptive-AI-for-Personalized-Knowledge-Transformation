# 🤖 Unified AI System for OCR and Custom Text Transformation
**by Hriday Jadhav & Sanmay Anand**

---

## What This Project Does

Based on your presentation, this is a **full AI pipeline** that:
1. Takes any PDF or image (scanned, photographed, digital)
2. Preprocesses it with computer vision (deskew, denoise, contrast)
3. Detects document layout (headings, paragraphs, tables)
4. Extracts text using Tesseract OCR
5. Analyzes confidence and flags errors
6. Runs NLP analysis (keywords, named entities, classification)
7. Applies custom text transformations (summarize, extract, redact, format)

---

## SETUP (Do This First)

### Step 1: Install Python packages
```bash
pip install -r requirements.txt
```

### Step 2: Install Tesseract OCR (the engine)

**Windows:**
1. Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install it (default path: `C:\Program Files\Tesseract-OCR\`)
3. Add to PATH, or add this line to `ocr_engine.py`:
   ```python
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

**Ubuntu/Linux:**
```bash
sudo apt install tesseract-ocr poppler-utils
```

**Mac:**
```bash
brew install tesseract poppler
```

### Step 3: Run the app
```bash
python app.py
```
Then open: **http://localhost:5000**

---

## Project Files Explained

```
ocr_project/
│
├── app.py              ← Main web application (run this!)
├── ocr_engine.py       ← OCR pipeline (preprocessing + layout + Tesseract)
├── nlp_engine.py       ← NLP + text transformations (no external ML needed)
├── train.py            ← Training & improvement tool (run separately)
├── requirements.txt    ← Python dependencies
│
├── uploads/            ← Temporary upload storage (auto-created)
├── outputs/            ← Saved outputs (auto-created)
└── models/
    └── corrections.json ← Learned corrections (grows as you train)
```

---

## How to Use the App

1. **Upload** a PDF or image (any quality — scanned, photographed, etc.)
2. Click **"Run OCR Pipeline"** — it will:
   - Preprocess the image (fix skew, denoise, enhance contrast)
   - Detect layout regions
   - Extract text
   - Show confidence score
3. Check **Confidence Panel** — see if OCR quality is HIGH/MEDIUM/LOW
4. Check **NLP Analysis** — keywords, entities, document type auto-detected
5. In **Custom Text Transformation**, pick a mode:
   - **Summarization** → key sentences extracted
   - **Information Extraction** → structured JSON of entities, stats, key-values
   - **Redaction** → emails, phones, financial data removed
   - **Classify & Tag** → document type + semantic tags
   - **Bullet Points** → formatted bullets
   - **Markdown** → clean markdown output

---

## HOW TO TRAIN THE SYSTEM

This is the **ML Feedback Loop** from your presentation:
```
Errors → Analysis → Retraining → Improved Performance
```

### Run the training tool:
```bash
python train.py
```

### What you do:
1. Run the OCR on a document
2. Notice a mistake (e.g., OCR read "rn" as "m" in a word)
3. Open `train.py` and select **Option 1: Add a manual correction**
4. Enter the wrong text and the correct text
5. The system learns this correction and applies it automatically next time

### Example training session:
```
OCR said:   "The algorithrn processes irnages"
Correct is: "The algorithm processes images"
→ System learns: rn→m, irn→im
→ Next time it sees these patterns, it auto-corrects them
```

### How much training data do you need?
- **50–100 corrections**: System starts becoming noticeably better
- **200–500 corrections**: Good accuracy on your document type
- **1000+ corrections**: Reliable on most documents

### Evaluating accuracy:
Select **Option 3** in `train.py` to see:
- **CER** (Character Error Rate): lower is better, 0 = perfect
- **WER** (Word Error Rate): lower is better, 0 = perfect
- **Accuracy %**: overall quality score

---

## Architecture (as per your presentation)

```
Input PDF/Image
     ↓
Vision Preprocessing Module (Perception Layer)
  - CNN-style deskew, denoise, CLAHE contrast, adaptive binarization
     ↓
Layout & Region Detection (Structural Intelligence)
  - Text blocks, headings, tables, reading order preservation
     ↓
OCR Intelligence Engine (Learning Core)
  - Tesseract 5 + LSTM (baseline)
  - Post-processing with learned corrections
     ↓
Confidence & Error Analysis (Uncertainty Reasoning)
  - Per-word confidence scores, ambiguous char detection (O/0, l/1, rn/m)
     ↓
NLP Reasoning Engine (Understanding Layer)
  - Tokenization, normalization, NER, keyword extraction
     ↓
Custom Text Transformation (Action Layer)
  - Summarize, Extract, Redact, Format, Classify
     ↓
Structured Intelligent Output
```

---

## For Your Presentation Demo

**Impressive demo flow:**
1. Upload a scanned PDF (ideally something handwritten or old/noisy)
2. Show the confidence score drop (proves system detects hard documents)
3. Show the layout regions (headings, text detected separately)
4. Run Summarization → show how long doc becomes short
5. Run Information Extraction → show structured JSON output
6. Run Redaction → show PII being masked
7. Open `train.py`, add a correction live → show ML feedback loop

**Key talking points:**
- "We use adaptive preprocessing unlike traditional fixed-threshold systems"
- "Layout detection means we understand structure, not just characters"
- "Confidence scoring lets us know WHERE the OCR is uncertain"
- "The ML feedback loop means the system improves with use"

---

## Future Improvements (for viva questions)

1. **Replace Tesseract with TrOCR** (Microsoft's transformer-based OCR) for higher accuracy
2. **Add GPU support** with EasyOCR for multi-language documents
3. **Table extraction** using CV2 contour detection
4. **Fine-tune a model** with your domain-specific data using Hugging Face
5. **Active learning**: Let users mark corrections directly in the UI
