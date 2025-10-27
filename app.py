from flask import Flask, request, jsonify
from flask_cors import CORS
import pytesseract
from pdf2image import convert_from_path
import re, os, time

# Explicitly set tesseract path (Render Docker image installs it here)
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

app = Flask(__name__)
CORS(
    app,
    origins=["https://v0-property-iq-dashboard.vercel.app"],
    methods=["GET", "POST", "OPTIONS"],
)
# ---------- OCR + Parsing Logic ----------

def extract_text(pdf_path):
    print(f"[INFO] Starting OCR for file: {pdf_path}")
    start_time = time.time()

    try:
        images = convert_from_path(pdf_path)
        print(f"[INFO] Converted PDF to {len(images)} image(s)")

        text = ""
        for i, img in enumerate(images):
            print(f"[INFO] Running pytesseract on page {i + 1}")
            text += pytesseract.image_to_string(img)
        duration = time.time() - start_time
        print(f"[INFO] OCR completed in {duration:.2f} seconds")

        return text
    except Exception as e:
        print(f"[ERROR] OCR failed: {e}")
        return ""

def parse_fields(text):
    print("[INFO] Parsing extracted text for fields")
    data = {}
    patterns = {
        "owner": r"Owner:\s*(.*)",
        "address": r"Address:\s*(.*)",
        "tax_year": r"Tax Year:\s*(\d{4})",
        "amount_due": r"Amount Due:\s*\$?([\d,]+\.\d{2})",
        "due_date": r"Due Date:\s*(.*)"
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        data[key] = match.group(1).strip() if match else None
    print("[INFO] Extracted fields:", data)
    return data

# ---------- Flask Routes ----------

@app.route("/upload", methods=["POST"])
def upload_pdf():
    print("[INFO] Received /upload request")
    start_time = time.time()

    if "file" not in request.files:
        print("[ERROR] No file part in the request")
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    file_path = os.path.join("uploads", file.filename)

    # Save uploaded file
    try:
        file.save(file_path)
        print(f"[INFO] Saved file to: {file_path}")
    except Exception as e:
        print(f"[ERROR] Failed to save file: {e}")
        return jsonify({"error": "Failed to save file"}), 500

    # Run OCR and extract fields
    text = extract_text(file_path)
    if not text.strip():
        print("[WARN] OCR returned no text.")
    fields = parse_fields(text)

    # Mask numbers in address (compliance)
    if fields.get("address"):
        fields["address"] = re.sub(r"\d", "X", fields["address"])
        print("[INFO] Masked address for privacy")

    print(f"[INFO] Finished processing in {time.time() - start_time:.2f} seconds")
    print("[INFO] Final extracted fields:", fields)
    return jsonify(fields)

@app.route("/")
def home():
    return "✅ PropertyIQ backend is running! Use /upload to POST a PDF."

@app.route("/test")
def test():
    print("[INFO] /test endpoint hit successfully")
    return {"message": "API is working fine!"}

@app.route("/ping")
def ping():
    print("[INFO] /ping check hit.")
    return "pong from render", 200

# ---------- App Runner ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)