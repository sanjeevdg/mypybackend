FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y \
        libreoffice \
        antiword \
        poppler-utils \
        tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install -r requirements.txt

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
