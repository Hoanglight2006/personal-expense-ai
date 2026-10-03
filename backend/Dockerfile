FROM python:3.11-slim

# Thiết lập biến môi trường
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Cài đặt các gói hệ thống cần thiết (tesseract OCR, libmagic, curl, mysql client)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libmagic1 \
    tesseract-ocr \
    tesseract-ocr-vie \
    default-mysql-client \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt Python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy mã nguồn các phân hệ
COPY backend /app/backend
COPY config /app/config
COPY database /app/database
COPY scripts /app/scripts

# Tạo sẵn thư mục static và backups
RUN mkdir -p /app/backend/static/avatars /app/backups

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
