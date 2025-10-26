# 🧾 PropertyIQ Backend

**PropertyIQ** is a lightweight Flask-based backend prototype inspired by **Ampliwork’s AI document-processing pipeline**.
It simulates how property tax bills can be parsed and processed automatically using OCR (Optical Character Recognition) while supporting compliance and human-in-the-loop review.

---

## 🚀 Overview

**Goal:** Automate property tax data extraction for accounting and audit clients.
The backend takes a property tax bill PDF, converts it to text, parses key fields, and returns structured JSON data.

---

## ⚙️ Tech Stack

- **Flask** — REST API framework
- **pdf2image + Poppler** — Convert PDF pages into images
- **pytesseract (Tesseract OCR)** — Extract text from images
- **Regex Parsing** — Identify structured fields from unstructured text

---

## 📡 API Endpoint

### `POST /upload`

**Description:** Upload a property tax bill (PDF) for OCR and data extraction.
**Request:**
```bash
curl -X POST -F "file=@sample.pdf" http://127.0.0.1:5000/upload
```

### Response (JSON):
```bash
{
  "owner": "John Doe",
  "address": "XXXX Main Street, Miami, FL",
  "tax_year": "2024",
  "amount_due": "1420.00",
  "due_date": "March 31, 2025"
}
```

## 🧱 Architecture
```bash
[PDF Upload] → [pdf2image] → [pytesseract OCR] → [Regex Parser] → [Compliance Filter] → [JSON Output]
```

## 🔒 Compliance Simulation
```bash
Mask sensitive details (addresses, account numbers)
Local-only storage (uploads/ folder is ignored by git)
```

## 🧪 Setup Instructions
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run server
python app.py

Make sure Poppler and Tesseract are installed and added to your PATH.

Poppler: https://github.com/oschwartz10612/poppler-windows/releases

Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
```