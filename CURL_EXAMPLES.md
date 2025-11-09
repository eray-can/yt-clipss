# 🔥 cURL Örnekleri

## 1. Ana Sayfa (Health Check)

```bash
curl http://localhost:5000/
```

---

## 2. Kesit Oluşturma (Tek Kesit)

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
        "caption": "Taşacak Bu Deniz 1.Bölüm: Diplomasını teslim alma anı."
      }
    ]
  }'
```

---

## 3. Kesit Oluşturma (Çoklu Kesit)

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
        "text": "yine Gregor. Elene yalızlıktan ölmez ama ameliyat etmezsek bu hasta ölür.",
        "caption": "Taşacak Bu Deniz 1.Bölüm: Melina'\''nın zorlu doktorluk kararı."
      },
      {
        "start": 179.8,
        "end": 210.45,
        "duration": 30.65,
        "text": "gregor Gregori. >> Bizler Konstantinopoli'\''nin evlatlarıyız.",
        "caption": "Taşacak Bu Deniz 1.Bölüm: İstanbullu Rumların Araf'\''ı."
      }
    ]
  }'
```

---

## 4. Mevcut Kesitleri Listele

```bash
curl http://localhost:5000/api/clips
```

---

## 5. Kesit İndir

```bash
# Dosya adını değiştir
curl -O http://localhost:5000/clips/abc123def456.mp4

# Özel isimle kaydet
curl -o my_clip.mp4 http://localhost:5000/clips/abc123def456.mp4
```

---

## 6. PowerShell Örnekleri (Windows)

### Kesit Oluştur
```powershell
$body = @{
    video_id = "KDV_-rXGy7A"
    clips = @(
        @{
            start = 0.32
            end = 41.56
            duration = 41.24
            caption = "Taşacak Bu Deniz 1.Bölüm: Diplomasını teslim alma anı."
        }
    )
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "http://localhost:5000/api/create-clips" -Method Post -Body $body -ContentType "application/json"
```

### Kesitleri Listele
```powershell
Invoke-RestMethod -Uri "http://localhost:5000/api/clips" -Method Get
```

### Kesit İndir
```powershell
Invoke-WebRequest -Uri "http://localhost:5000/clips/abc123def456.mp4" -OutFile "clip.mp4"
```

---

## 7. Production URL ile Kullanım

Deployment sonrası domain'inizi değiştirin:

```bash
# Örnek: Render.com
curl -X POST https://your-app.onrender.com/api/create-clips \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "KDV_-rXGy7A",
    "clips": [{"start": 0.32, "end": 41.56, "caption": "Test"}]
  }'
```

---

## 8. Facebook Graph API Entegrasyonu

Oluşturulan URL'i Facebook'a yükle:

```bash
curl -X POST "https://graph.facebook.com/v18.0/{page-id}/videos" \
  -F "file_url=https://your-app.onrender.com/clips/abc123.mp4" \
  -F "description=Video açıklaması" \
  -F "access_token=YOUR_ACCESS_TOKEN"
```

---

## 9. Python ile Kullanım

```python
import requests

response = requests.post(
    "http://localhost:5000/api/create-clips",
    json={
        "video_id": "KDV_-rXGy7A",
        "clips": [
            {
                "start": 0.32,
                "end": 41.56,
                "caption": "Test kesit"
            }
        ]
    }
)

print(response.json())
```

---

## 10. JavaScript/Node.js ile Kullanım

```javascript
fetch('http://localhost:5000/api/create-clips', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    video_id: 'KDV_-rXGy7A',
    clips: [
      {
        start: 0.32,
        end: 41.56,
        caption: 'Test kesit'
      }
    ]
  })
})
.then(res => res.json())
.then(data => console.log(data));
```
