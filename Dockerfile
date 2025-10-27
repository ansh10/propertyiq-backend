FROM python:3.11-slim

# Install system dependencies with proper tesseract language data
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Verify installations
RUN tesseract --version && pdfinfo -v

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Set the port Render expects
ENV PORT=10000
EXPOSE 10000

# Use gunicorn for production instead of Flask dev server
CMD ["gunicorn", "-c", "gunicorn_config.py", "app:app"]