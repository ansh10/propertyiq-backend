FROM python:3.11-slim

# Install system dependencies (Tesseract + Poppler)
RUN apt-get update && apt-get install -y tesseract-ocr poppler-utils && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Set the port Render expects
ENV PORT=10000
EXPOSE 10000

CMD ["python", "app.py"]
