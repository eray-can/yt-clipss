# YouTube Clip API 🎬

YouTube videolarından belirli zaman aralıklarında kesitler oluşturup URL olarak sunan Flask API.

## ✨ Version 2.1.0 - Multi-Video Processing Fix

**Yeni Özellikler:**
- ✅ Robust exception handling - Bir video hata verse bile diğerleri işlenir
- ✅ FFmpeg timeout protection (5 dakika) - Takılma sorunu çözüldü
- ✅ Enhanced logging - Her adım detaylı loglanır
- ✅ File validation - Boş dosyalar otomatik temizlenir
- ✅ Comprehensive test suite - 13 unit test ile doğrulandı

**Detaylı bilgi için:**
- 📖 [FIXES.md](FIXES.md) - Yapılan düzeltmeler
- 📖 [TESTING_GUIDE.md](TESTING_GUIDE.md) - Test rehberi
- 📖 [ARCHITECTURE.md](ARCHITECTURE.md) - Sistem mimarisi
- 📖 [SUMMARY.md](SUMMARY.md) - Özet rapor

## 🚀 Kurulum

```bash
pip install -r requirements.txt
```

## 📦 Gereksinimler

- Python 3.9+
- FFmpeg (sistemde kurulu olmalı)

## 🧪 Testing

### Tüm Testleri Çalıştır
```bash
python run_tests.py
```

### Sadece Unit Testler
```bash
python test_unit.py
```

### Integration Testler (Server gerekli)
```bash
# Terminal 1: Server'ı başlat
python app.py

# Terminal 2: Testleri çalıştır
python test_async.py
python test_multi_video.py
```

**Test Coverage:**
- ✅ Job management (save/get/delete)
- ✅ Filename generation
- ✅ Async clip processing
- ✅ Exception handling
- ✅ Multi-video scenarios
- ✅ Error recovery

Detaylı test rehberi için: [TESTING_GUIDE.md](TESTING_GUIDE.md)

## 🎯 Kullanım

### API'yi Başlat

**Geliştirme:**
```bash
python app.py
```

**Production (Gunicorn):**
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

API `http://localhost:5000` adresinde çalışacak.

---

## 📡 API Endpoints

### 1️⃣ Ana Sayfa
```bash
curl http://localhost:5000/
```

**Response:**
```json
{
  "name": "YouTube Clip API",
  "version": "1.0",
  "endpoints": {
    "POST /api/create-clips": "Kesitler oluştur",
    "GET /api/clips": "Mevcut kesitleri listele",
    "GET /clips/<filename>": "Kesit dosyasını indir"
  }
}
```

---

### 2️⃣ Kesit Oluşturma

**Endpoint:** `POST /api/create-clips`

**cURL Örneği:**
```bash
curl -X POST http://localhost:5000/api/create-clips \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "KDV_-rXGy7A",
    "clips": [
      {
        "start": 0.32,
        "end": 41.56,
        "duration": 41.24,
        "text": "Oh. την έρθει να παραλάβει το διπλωμά",
        "caption": "Taşacak Bu Deniz 1.Bölüm: Diplomasını teslim alma anı."
      },
      {
        "start": 126.36,
        "end": 179.8,
        "duration": 53.44,
        "text": "yine Gregor...",
        "caption": "Taşacak Bu Deniz 1.Bölüm: Melina'\''nın zorlu doktorluk kararı."
      }
    ]
  }'
```

**PowerShell Örneği:**
```powershell
$body = @{
    video_id = "KDV_-rXGy7A"
    clips = @(
        @{
            start = 0.32
            end = 41.56
            duration = 41.24
            text = "Oh. την έρθει να παραλάβει το διπλωμά"
            caption = "Taşacak Bu Deniz 1.Bölüm: Diplomasını teslim alma anı."
        },
        @{
            start = 126.36
            end = 179.8
            duration = 53.44
            text = "yine Gregor..."
            caption = "Taşacak Bu Deniz 1.Bölüm: Melina'nın zorlu doktorluk kararı."
        }
    )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://localhost:5000/api/create-clips" -Method Post -Body $body -ContentType "application/json"
```

**Response:**
```json
{
  "success": true,
  "video_id": "KDV_-rXGy7A",
  "clips": [
    {
      "caption": "Taşacak Bu Deniz 1.Bölüm: Diplomasını teslim alma anı.",
      "start": 0.32,
      "end": 41.56,
      "duration": 41.24,
      "url": "http://localhost:5000/clips/abc123def456.mp4",
      "filename": "abc123def456.mp4"
    }
  ],
  "total": 2
}
```

---

### 3️⃣ Kesitleri Listele

**Endpoint:** `GET /api/clips`

**cURL:**
```bash
curl http://localhost:5000/api/clips
```

**Response:**
```json
{
  "success": true,
  "clips": [
    {
      "filename": "abc123def456.mp4",
      "url": "http://localhost:5000/clips/abc123def456.mp4",
      "size": 3147264
    }
  ],
  "total": 1
}
```

---

### 4️⃣ Kesit İndir

**Endpoint:** `GET /clips/<filename>`

**cURL:**
```bash
curl -O http://localhost:5000/clips/abc123def456.mp4
```

---

### 5️⃣ Job Yönetimi

#### Tüm Job'ları Listele
**Endpoint:** `GET /api/jobs`

```bash
curl http://localhost:5000/api/jobs
```

#### Belirli Bir Job'u Sil
**Endpoint:** `DELETE /api/jobs/<job_id>`

```bash
curl -X DELETE http://localhost:5000/api/jobs/abc-123-def
```

#### Tüm Job'ları Sil
**Endpoint:** `DELETE /api/jobs/all`

```bash
curl -X DELETE http://localhost:5000/api/jobs/all
```

**Detaylı örnekler için:** [JOB_API_EXAMPLES.md](JOB_API_EXAMPLES.md)

---

## 🎨 Özellikler

- ✅ YouTube videolarından otomatik kesit oluşturma
- ✅ **Async job processing** - Hemen job ID döner, arka planda işler
- ✅ **Multi-video support** - Birden fazla video aynı anda işlenebilir
- ✅ **Robust error handling** - Bir hata tüm sistemi durdurmaz
- ✅ **Timeout protection** - FFmpeg 5 dakikadan fazla takılmaz
- ✅ **Smart file validation** - Boş dosyalar otomatik temizlenir
- ✅ Benzersiz ID ile dosya yönetimi (aynı kesit tekrar indirilmez)
- ✅ FFmpeg ile hızlı kesit oluşturma
- ✅ URL üzerinden kesitlere erişim
- ✅ Facebook Graph API ile uyumlu URL formatı
- ✅ Production-ready (Gunicorn desteği)
- ✅ **Comprehensive test suite** - 13 unit test

---

## 🌐 Deploy

### Render.com
1. `requirements.txt` ve `app.py` dosyalarını yükle
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `gunicorn -w 4 -b 0.0.0.0:$PORT app:app`

### Railway
1. GitHub'a push yap
2. Railway'de projeyi bağla
3. Otomatik deploy olacak

### Heroku
```bash
heroku create your-app-name
git push heroku main
```

---

## 📝 Notlar

- FFmpeg sistemde kurulu olmalı
- Kesitler `clips/` klasöründe saklanır
- Aynı `video_id`, `start` ve `end` değerleri için tekrar indirme yapılmaz
- Production'da `gunicorn` kullanın

---

## 🔗 Facebook Graph API Entegrasyonu

Oluşturulan URL'leri doğrudan Facebook Graph API'ye verebilirsiniz:

```bash
curl -X POST "https://graph.facebook.com/v18.0/{page-id}/videos" \
  -F "file_url=http://your-domain.com/clips/abc123.mp4" \
  -F "description=Video açıklaması" \
  -F "access_token=YOUR_ACCESS_TOKEN"
```
