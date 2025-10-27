from flask import Flask, request, jsonify
from flask_cors import CORS
import pytesseract
from pdf2image import convert_from_path
import re, os, time
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

os.makedirs("uploads", exist_ok=True)

# Explicitly set tesseract path
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, methods=["GET", "POST", "OPTIONS"])

# Set max content length (10MB)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# ---------- OCR + Parsing Logic ----------

def extract_text(pdf_path):
    logger.info(f"Starting OCR for file: {pdf_path}")
    start_time = time.time()

    try:
        # Optimize: Lower DPI and limit pages
        logger.info("Converting PDF to images...")
        images = convert_from_path(
            pdf_path, 
            dpi=100,  # Lower DPI = faster (was 150-200 by default)
            first_page=1, 
            last_page=2,  # Only process first 2 pages
            thread_count=1  # Single thread to avoid memory issues
        )
        logger.info(f"Converted PDF to {len(images)} image(s)")

        text = ""
        for i, img in enumerate(images):
            page_start = time.time()
            logger.info(f"Running pytesseract on page {i + 1}")
            
            # Resize image to speed up OCR
            width, height = img.size
            if width > 2000:  # If image is too large
                ratio = 2000 / width
                new_size = (2000, int(height * ratio))
                img = img.resize(new_size)
                logger.info(f"Resized image to {new_size}")
            
            # Use faster Tesseract config with timeout
            page_text = pytesseract.image_to_string(
                img, 
                config='--psm 6 --oem 1',  # Faster engine mode
                timeout=20  # 20 second timeout per page
            )
            text += page_text
            
            page_duration = time.time() - page_start
            logger.info(f"Page {i + 1} completed in {page_duration:.2f}s")
            
        duration = time.time() - start_time
        logger.info(f"OCR completed in {duration:.2f} seconds")
        logger.info(f"Extracted text length: {len(text)} characters")

        return text
        
    except pytesseract.TesseractError as e:
        logger.error(f"Tesseract OCR failed: {e}", exc_info=True)
        raise Exception("OCR processing failed. The PDF may be corrupted or too complex.")
    except Exception as e:
        logger.error(f"OCR failed: {e}", exc_info=True)
        raise

def parse_fields(text):
    logger.info("Parsing extracted text for fields")
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
    logger.info(f"Extracted fields: {data}")
    return data

# ---------- Flask Routes ----------

@app.route("/test-ocr", methods=["POST"])
def test_ocr():
    """Quick test without actual OCR"""
    logger.info("Received /test-ocr request")
    
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["file"]
    logger.info(f"File received: {file.filename}")
    
    # Return mock data immediately to test if the issue is OCR
    mock_data = {
        "owner": "John Doe",
        "address": "123 Main St",
        "tax_year": "2024",
        "amount_due": "1234.56",
        "due_date": "2024-12-31"
    }
    
    return jsonify(mock_data), 200

@app.route("/upload", methods=["OPTIONS"])
def preflight_check():
    logger.info("Preflight OPTIONS received")
    return jsonify({"message": "CORS preflight OK"}), 200

@app.route("/upload", methods=["POST"])
def upload_pdf():
    logger.info("Received /upload request")
    start_time = time.time()
    file_path = None

    try:
        if "file" not in request.files:
            logger.error("No file part in the request")
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        
        if not file.filename:
            return jsonify({"error": "No file selected"}), 400
            
        if not file.filename.endswith('.pdf'):
            return jsonify({"error": "Only PDF files allowed"}), 400

        # Generate unique filename to avoid collisions
        timestamp = int(time.time())
        file_path = os.path.join("uploads", f"{timestamp}_{file.filename}")

        # Save uploaded file
        file.save(file_path)
        logger.info(f"Saved file to: {file_path}")

        # Run OCR and extract fields
        text = extract_text(file_path)
        
        if not text.strip():
            logger.warning("OCR returned no text")
            return jsonify({"error": "Could not extract text from PDF"}), 400
            
        fields = parse_fields(text)

        # Mask numbers in address (compliance)
        if fields.get("address"):
            fields["address"] = re.sub(r"\d", "X", fields["address"])
            logger.info("Masked address for privacy")

        duration = time.time() - start_time
        logger.info(f"Finished processing in {duration:.2f} seconds")
        logger.info(f"Final extracted fields: {fields}")
        
        return jsonify(fields), 200

    except Exception as e:
        logger.error(f"Error processing upload: {e}", exc_info=True)
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500
        
    finally:
        # Cleanup uploaded file
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to cleanup file: {e}")

@app.route("/")
def home():
    return "✅ PropertyIQ backend is running! Use /upload to POST a PDF."

@app.route("/health")
def health():
    return {"status": "healthy", "timestamp": time.time()}, 200

# ---------- App Runner ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # Disable debug in production
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)