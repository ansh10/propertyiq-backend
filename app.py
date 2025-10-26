from flask import Flask, request, jsonify
import pytesseract
from pdf2image import convert_from_path
import re, os
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

app = Flask(__name__)

def extract_text(pdf_path):
    images = convert_from_path(pdf_path)
    text = ""
    for i, img in enumerate(images):
        text += pytesseract.image_to_string(img)
    return text

def parse_fields(text):
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
    return data

@app.route("/upload", methods=["POST"])
def upload_pdf():
    file = request.files["file"]
    file_path = os.path.join("uploads", file.filename)
    file.save(file_path)

    text = extract_text(file_path)
    fields = parse_fields(text)
    # compliance step: mask address numbers
    if fields.get("address"):
        fields["address"] = re.sub(r"\d", "X", fields["address"])
    return jsonify(fields)

@app.route("/")
def home():
    return "✅ PropertyIQ backend is running! Use /upload to POST a PDF."

@app.route("/test")
def test():
    return {"message": "API is working fine!"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

