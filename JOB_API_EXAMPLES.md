# Job Management API Examples

## Yeni Eklenen Endpoint'ler

### 1. Tüm Job'ları Listele
**Endpoint:** `GET /api/jobs`

**cURL:**
```bash
curl http://localhost:5000/api/jobs
```

**Response:**
```json
{
  "success": true,
  "jobs": [
    {
      "job_id": "abc-123-def",
      "video_id": "Z3TMbaX_X0k",
      "status": "finished",
      "created_at": "2024-11-11T20:30:00",
      "total": 5,
      "processed": 5
    },
    {
      "job_id": "xyz-456-ghi",
      "video_id": "KDV_-rXGy7A",
      "status": "processing",
      "created_at": "2024-11-11T20:35:00",
      "total": 3,
      "processed": 1
    }
  ],
  "total": 2
}
```

**Python:**
```python
import requests

response = requests.get('http://localhost:5000/api/jobs')
jobs = response.json()

print(f"Toplam job sayısı: {jobs['total']}")
for job in jobs['jobs']:
    print(f"- {job['job_id']}: {job['status']} ({job['processed']}/{job['total']})")
```

---

### 2. Belirli Bir Job'u Sil
**Endpoint:** `DELETE /api/jobs/<job_id>`

**cURL:**
```bash
curl -X DELETE http://localhost:5000/api/jobs/abc-123-def
```

**Response:**
```json
{
  "success": true,
  "message": "Job abc-123-def silindi"
}
```

**Python:**
```python
import requests

job_id = "abc-123-def"
response = requests.delete(f'http://localhost:5000/api/jobs/{job_id}')

if response.json()['success']:
    print(f"✅ Job {job_id} silindi")
else:
    print(f"❌ Hata: {response.json()['error']}")
```

**PowerShell:**
```powershell
$jobId = "abc-123-def"
Invoke-RestMethod -Uri "http://localhost:5000/api/jobs/$jobId" -Method Delete
```

---

### 3. Tüm Job'ları Sil
**Endpoint:** `DELETE /api/jobs/all`

**cURL:**
```bash
curl -X DELETE http://localhost:5000/api/jobs/all
```

**Response:**
```json
{
  "success": true,
  "deleted_count": 15,
  "errors": null,
  "message": "15 job silindi"
}
```

**Python:**
```python
import requests

response = requests.delete('http://localhost:5000/api/jobs/all')
result = response.json()

if result['success']:
    print(f"✅ {result['deleted_count']} job silindi")
    if result['errors']:
        print(f"⚠️ {len(result['errors'])} hata oluştu")
else:
    print(f"❌ Hata: {result['error']}")
```

**PowerShell:**
```powershell
Invoke-RestMethod -Uri "http://localhost:5000/api/jobs/all" -Method Delete
```

---

## Kullanım Senaryoları

### Senaryo 1: Tamamlanan Job'ları Temizle

```python
import requests

# Tüm job'ları listele
response = requests.get('http://localhost:5000/api/jobs')
jobs = response.json()['jobs']

# Tamamlanan job'ları sil
deleted_count = 0
for job in jobs:
    if job['status'] == 'finished':
        delete_response = requests.delete(
            f"http://localhost:5000/api/jobs/{job['job_id']}"
        )
        if delete_response.json()['success']:
            deleted_count += 1
            print(f"✅ {job['job_id']} silindi")

print(f"\nToplam {deleted_count} tamamlanmış job silindi")
```

### Senaryo 2: Eski Job'ları Temizle (24 saatten eski)

```python
import requests
from datetime import datetime, timedelta

# Tüm job'ları listele
response = requests.get('http://localhost:5000/api/jobs')
jobs = response.json()['jobs']

# 24 saatten eski job'ları sil
cutoff_time = datetime.now() - timedelta(hours=24)
deleted_count = 0

for job in jobs:
    created_at = datetime.fromisoformat(job['created_at'])
    if created_at < cutoff_time:
        delete_response = requests.delete(
            f"http://localhost:5000/api/jobs/{job['job_id']}"
        )
        if delete_response.json()['success']:
            deleted_count += 1
            print(f"✅ {job['job_id']} silindi (oluşturulma: {created_at})")

print(f"\nToplam {deleted_count} eski job silindi")
```

### Senaryo 3: Başarısız Job'ları Temizle

```python
import requests

# Tüm job'ları listele
response = requests.get('http://localhost:5000/api/jobs')
jobs = response.json()['jobs']

# Başarısız job'ları sil
deleted_count = 0
for job in jobs:
    if job['status'] == 'failed':
        delete_response = requests.delete(
            f"http://localhost:5000/api/jobs/{job['job_id']}"
        )
        if delete_response.json()['success']:
            deleted_count += 1
            print(f"✅ {job['job_id']} silindi (başarısız)")

print(f"\nToplam {deleted_count} başarısız job silindi")
```

### Senaryo 4: Tüm Job'ları ve Clip'leri Temizle

```python
import requests

# Tüm job'ları sil
jobs_response = requests.delete('http://localhost:5000/api/jobs/all')
jobs_result = jobs_response.json()

# Tüm clip'leri sil
clips_response = requests.delete('http://localhost:5000/api/clips/all')
clips_result = clips_response.json()

print(f"✅ {jobs_result['deleted_count']} job silindi")
print(f"✅ {clips_result['deleted_count']} clip silindi")
print("\n🧹 Sistem temizlendi!")
```

---

## Otomatik Temizleme Script'i

Periyodik olarak eski job'ları temizlemek için:

```python
#!/usr/bin/env python3
"""
Job Cleanup Script
Tamamlanmış ve 1 saatten eski job'ları otomatik siler
"""
import requests
import time
from datetime import datetime, timedelta

API_URL = "http://localhost:5000"
CHECK_INTERVAL = 3600  # 1 saat (saniye)
MAX_AGE_HOURS = 1  # 1 saatten eski job'ları sil

def cleanup_old_jobs():
    """Eski job'ları temizle"""
    try:
        # Tüm job'ları listele
        response = requests.get(f"{API_URL}/api/jobs")
        if not response.json()['success']:
            print("❌ Job'lar listelenemedi")
            return
        
        jobs = response.json()['jobs']
        cutoff_time = datetime.now() - timedelta(hours=MAX_AGE_HOURS)
        deleted_count = 0
        
        for job in jobs:
            # Sadece tamamlanmış job'ları kontrol et
            if job['status'] != 'finished':
                continue
            
            created_at = datetime.fromisoformat(job['created_at'])
            if created_at < cutoff_time:
                # Job'u sil
                delete_response = requests.delete(
                    f"{API_URL}/api/jobs/{job['job_id']}"
                )
                if delete_response.json()['success']:
                    deleted_count += 1
                    print(f"🗑️  {job['job_id']} silindi")
        
        if deleted_count > 0:
            print(f"✅ {deleted_count} eski job temizlendi")
        else:
            print("ℹ️  Silinecek eski job yok")
    
    except Exception as e:
        print(f"❌ Hata: {str(e)}")

if __name__ == "__main__":
    print("🧹 Job Cleanup Script başlatıldı")
    print(f"⏰ Her {CHECK_INTERVAL} saniyede bir kontrol edilecek")
    print(f"🕐 {MAX_AGE_HOURS} saatten eski job'lar silinecek\n")
    
    while True:
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Kontrol ediliyor...")
        cleanup_old_jobs()
        time.sleep(CHECK_INTERVAL)
```

**Kullanım:**
```bash
# Arka planda çalıştır
python cleanup_jobs.py &

# Veya cron job olarak (her saat)
# crontab -e
# 0 * * * * /usr/bin/python3 /path/to/cleanup_jobs.py
```

---

## API Endpoint Özeti

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| `GET` | `/api/jobs` | Tüm job'ları listele |
| `DELETE` | `/api/jobs/<job_id>` | Belirli bir job'u sil |
| `DELETE` | `/api/jobs/all` | Tüm job'ları sil |
| `GET` | `/api/clips` | Tüm clip'leri listele |
| `DELETE` | `/api/clips/<filename>` | Belirli bir clip'i sil |
| `DELETE` | `/api/clips/all` | Tüm clip'leri sil |

---

## Hata Durumları

### Job Bulunamadı
```json
{
  "success": false,
  "error": "Job bulunamadı"
}
```

### Silme Hatası
```json
{
  "success": true,
  "deleted_count": 10,
  "errors": [
    {
      "job_id": "abc-123",
      "error": "Permission denied"
    }
  ],
  "message": "10 job silindi"
}
```

---

## Best Practices

1. **Periyodik Temizleme**
   - Tamamlanan job'ları düzenli olarak temizleyin
   - Disk alanı tasarrufu sağlar

2. **Seçici Silme**
   - Tüm job'ları silmek yerine, tamamlananları silin
   - İşlem gören job'ları koruyun

3. **Backup**
   - Önemli job'ları silmeden önce yedekleyin
   - Job verilerini loglayın

4. **Monitoring**
   - Job sayısını takip edin
   - Disk kullanımını izleyin

---

## Güvenlik Notları

⚠️ **Dikkat:** Bu endpoint'ler authentication gerektirmez. Production'da:

1. API key veya JWT token ekleyin
2. Rate limiting uygulayın
3. Admin yetkisi gerektirin
4. Audit log tutun

**Örnek güvenlik implementasyonu:**
```python
from functools import wraps
from flask import request

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if api_key != 'YOUR_SECRET_KEY':
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/jobs/all', methods=['DELETE'])
@require_api_key
def delete_all_jobs():
    # ...
```
