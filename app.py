from flask import Flask, request, jsonify
from flask_cors import CORS
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
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
        # CRITICAL: Use very low DPI and limit to first page only
        logger.info("Converting PDF to images with low DPI...")
        images = convert_from_path(
            pdf_path, 
            dpi=100,  # Very low DPI for speed (minimum readable quality)
            # first_page=1, 
            # last_page=1,  # ONLY first page for testing
            thread_count=1,
            grayscale=True  # Grayscale is faster
        )
        logger.info(f"Converted PDF to {len(images)} image(s)")

        text = ""
        for i, img in enumerate(images):
            page_start = time.time()
            logger.info(f"Processing page {i + 1}, original size: {img.size}")
            
            # Aggressively resize if still too large
            max_width = 1500
            width, height = img.size
            if width > max_width:
                ratio = max_width / width
                new_size = (max_width, int(height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"Resized to {new_size}")
            
            # Convert to grayscale if not already
            if img.mode != 'L':
                img = img.convert('L')
                logger.info("Converted to grayscale")
            
            # Use fastest Tesseract config with timeout
            logger.info(f"Running OCR on page {i + 1}...")
            try:
                page_text = pytesseract.image_to_string(
                    img,
                    config='--psm 6 --oem 1',  # Fast mode
                    timeout=30  # 30 second timeout per page
                )
                text += page_text
                logger.info(f"OCR successful, extracted {len(page_text)} characters")
            except RuntimeError as timeout_error:
                logger.error(f"OCR timeout on page {i + 1}: {timeout_error}")
                raise Exception("OCR took too long. Try a simpler PDF.")
            
            page_duration = time.time() - page_start
            logger.info(f"Page {i + 1} completed in {page_duration:.2f}s")
            
        duration = time.time() - start_time
        logger.info(f"Total OCR completed in {duration:.2f} seconds")
        logger.info(f"Total extracted text length: {len(text)} characters")

        if not text.strip():
            logger.warning("OCR returned empty text")
            raise Exception("Could not extract any text from PDF")

        return text
        
    except pytesseract.TesseractError as e:
        logger.error(f"Tesseract error: {e}", exc_info=True)
        raise Exception("OCR processing failed. The PDF may be an image or corrupted.")
    except Exception as e:
        logger.error(f"OCR failed: {e}", exc_info=True)
        raise

def parse_fields(text):
    logger.info("Parsing extracted text for fields")
    logger.info(f"Text preview (first 200 chars): {text[:200]}")
    
    data = {}
    
    # More flexible patterns
    patterns = {
        "owner": r"(?:Owner|Name):\s*(.+?)(?:\n|$)",
        "address": r"(?:Address|Property):\s*(.+?)(?:\n|$)",
        "tax_year": r"(?:Tax Year|Year):\s*(\d{4})",
        "amount_due": r"(?:Amount Due|Total Due|Balance):\s*\$?\s*([\d,]+\.?\d*)",
        "due_date": r"(?:Due Date|Payment Due):\s*(.+?)(?:\n|$)"
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            data[key] = value
            logger.info(f"Found {key}: {value}")
        else:
            data[key] = None
            logger.warning(f"Could not find {key}")
    
    logger.info(f"Extracted fields: {data}")
    return data

# ---------- Flask Routes ----------

@app.route("/upload", methods=["OPTIONS"])
def preflight_check():
    logger.info("Preflight OPTIONS received")
    return jsonify({"message": "CORS preflight OK"}), 200

@app.route("/upload", methods=["POST"])
def upload_pdf():
    logger.info("=" * 60)
    logger.info("NEW UPLOAD REQUEST RECEIVED")
    logger.info("=" * 60)
    start_time = time.time()
    file_path = None

    try:
        if "file" not in request.files:
            logger.error("No file part in the request")
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["file"]
        
        if not file.filename:
            return jsonify({"error": "No file selected"}), 400
            
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({"error": "Only PDF files allowed"}), 400

        # Generate unique filename
        timestamp = int(time.time())
        file_path = os.path.join("uploads", f"{timestamp}_{file.filename}")

        # Save uploaded file
        logger.info(f"Saving file: {file.filename} ({file.content_length} bytes)")
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        logger.info(f"File saved to: {file_path} (actual size: {file_size} bytes)")

        # Run OCR and extract fields
        logger.info("Starting OCR extraction...")
        text = extract_text(file_path)
        
        if not text.strip():
            logger.error("OCR returned empty text")
            return jsonify({"error": "Could not extract text from PDF. The file may be corrupted or contain only images."}), 400
            
        logger.info("OCR successful, parsing fields...")
        fields = parse_fields(text)

        # Mask numbers in address (compliance)
        if fields.get("address"):
            original_address = fields["address"]
            fields["address"] = re.sub(r"\d", "X", fields["address"])
            logger.info(f"Masked address: {original_address} -> {fields['address']}")

        duration = time.time() - start_time
        logger.info("=" * 60)
        logger.info(f"SUCCESS! Processing completed in {duration:.2f} seconds")
        logger.info(f"Final extracted fields: {fields}")
        logger.info("=" * 60)
        
        return jsonify(fields), 200

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"ERROR: {str(e)}", exc_info=True)
        logger.error("=" * 60)
        return jsonify({"error": str(e)}), 500
        
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

@app.route("/test-ocr", methods=["POST"])
def test_ocr():
    """Quick test without actual OCR"""
    logger.info("Received /test-ocr request")
    
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["file"]
    logger.info(f"File received: {file.filename}")
    
    mock_data = {
        "owner": "John Doe",
        "address": "123 Main St",
        "tax_year": "2024",
        "amount_due": "1234.56",
        "due_date": "2024-12-31"
    }
    
    return jsonify(mock_data), 200

# ---------- App Runner ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)