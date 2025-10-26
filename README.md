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
