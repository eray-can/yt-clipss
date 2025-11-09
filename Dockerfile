FROM python:3.11-slim

# FFmpeg kurulumu
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /app

# Bağımlılıkları kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Clips klasörünü oluştur
RUN mkdir -p clips

# Port
EXPOSE 5000

# Gunicorn ile çalıştır (timeout 900 saniye = 15 dakika)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "900", "app:app"]
