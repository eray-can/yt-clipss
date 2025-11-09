# YouTube Clip API - Kullanım Örnekleri

## 1. Clip Oluşturma (Async)

### Request
```bash
curl -X POST http://localhost:5000/api/create-clips \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "Z3TMbaX_X0k",
    "clips": [
      {"start": 0, "end": 10},
      {"start": 10, "end": 20},
      {"start": 20, "end": 30}
    ]
  }'
```

### Response (Hemen Döner)
```json
{
  "success": true,
  "job_id": "1b12d124-0aa5-48b6-9d05-e9ea7dd13373",
  "video_id": "Z3TMbaX_X0k",
  "status": "pending",
  "total_clips": 3,
  "message": "Job başlatıldı. /api/check-job/<job_id> ile durumu kontrol edin.",
  "clip_filenames": [
    "Z3TMbaX_X0k-0-10.mp4",
    "Z3TMbaX_X0k-10-20.mp4",
    "Z3TMbaX_X0k-20-30.mp4"
  ]
}
```

---

## 2. Job Durumu Kontrol Et

### Request
```bash
curl http://localhost:5000/api/check-job/1b12d124-0aa5-48b6-9d05-e9ea7dd13373
```

### Response (İşlem Devam Ediyor)
```json
{
  "success": true,
  "job_id": "1b12d124-0aa5-48b6-9d05-e9ea7dd13373",
  "video_id": "Z3TMbaX_X0k",
  "status": "processing",
  "created_at": "2025-11-09T23:57:32.843046",
  "total": 3,
  "processed": 2,
  "clip_filenames": [
    "Z3TMbaX_X0k-0-10.mp4",
    "Z3TMbaX_X0k-10-20.mp4",
    "Z3TMbaX_X0k-20-30.mp4"
  ]
}
```

### Response (İşlem Tamamlandı)
```json
{
  "success": true,
  "job_id": "1b12d124-0aa5-48b6-9d05-e9ea7dd13373",
  "video_id": "Z3TMbaX_X0k",
  "status": "completed",
  "created_at": "2025-11-09T23:57:32.843046",
  "completed_at": "2025-11-09T23:57:45.123456",
  "total": 3,
  "processed": 3,
  "clip_filenames": [
    "Z3TMbaX_X0k-0-10.mp4",
    "Z3TMbaX_X0k-10-20.mp4",
    "Z3TMbaX_X0k-20-30.mp4"
  ],
  "clips": [
    {
      "start": 0,
      "end": 10,
      "filename": "Z3TMbaX_X0k-0-10.mp4",
      "url": "http://localhost:5000/clips/Z3TMbaX_X0k-0-10.mp4",
      "video_title": "Video Başlığı",
      "resolution": "720p",
      "file_size_mb": 0.3
    },
    {
      "start": 10,
      "end": 20,
      "filename": "Z3TMbaX_X0k-10-20.mp4",
      "url": "http://localhost:5000/clips/Z3TMbaX_X0k-10-20.mp4",
      "video_title": "Video Başlığı",
      "resolution": "720p",
      "file_size_mb": 0.62
    },
    {
      "start": 20,
      "end": 30,
      "filename": "Z3TMbaX_X0k-20-30.mp4",
      "url": "http://localhost:5000/clips/Z3TMbaX_X0k-20-30.mp4",
      "video_title": "Video Başlığı",
      "resolution": "720p",
      "file_size_mb": 0.97
    }
  ],
  "errors": [],
  "error_count": 0
}
```

---

## 3. Tüm Clipleri Listele

### Request
```bash
curl http://localhost:5000/api/clips
```

### Response
```json
{
  "success": true,
  "clips": [
    {
      "filename": "Z3TMbaX_X0k-0-10.mp4",
      "url": "http://localhost:5000/clips/Z3TMbaX_X0k-0-10.mp4",
      "size": 314572
    }
  ],
  "total": 1
}
```

---

## 4. Clip İndir

### Request
```bash
curl -O http://localhost:5000/clips/Z3TMbaX_X0k-0-10.mp4
```

---

## 5. Tek Clip Sil

### Request
```bash
curl -X DELETE http://localhost:5000/api/clips/Z3TMbaX_X0k-0-10.mp4
```

### Response
```json
{
  "success": true,
  "message": "Z3TMbaX_X0k-0-10.mp4 silindi"
}
```

---

## 6. Tüm Clipleri Sil

### Request
```bash
curl -X DELETE http://localhost:5000/api/clips/all
```

### Response
```json
{
  "success": true,
  "deleted_count": 5,
  "errors": null
}
```

---

## Job Status Değerleri

- **`pending`** - Job başlatıldı, henüz işleme başlanmadı
- **`processing`** - Clipler işleniyor
- **`completed`** - Tüm clipler başarıyla oluşturuldu
- **`failed`** - Job başarısız oldu

---

## Polling Örneği (JavaScript)

```javascript
async function createAndWaitForClips(videoId, clips) {
  // 1. Job başlat
  const createResponse = await fetch('http://localhost:5000/api/create-clips', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_id: videoId, clips })
  });
  
  const { job_id, clip_filenames } = await createResponse.json();
  console.log('Job ID:', job_id);
  console.log('Clip dosyaları:', clip_filenames);
  
  // 2. Job durumunu kontrol et (polling)
  while (true) {
    const checkResponse = await fetch(`http://localhost:5000/api/check-job/${job_id}`);
    const jobStatus = await checkResponse.json();
    
    console.log(`Durum: ${jobStatus.status} | İşlenen: ${jobStatus.processed}/${jobStatus.total}`);
    
    if (jobStatus.status === 'completed') {
      console.log('✅ Tamamlandı!');
      return jobStatus.clips;
    } else if (jobStatus.status === 'failed') {
      throw new Error(jobStatus.error);
    }
    
    // 2 saniye bekle
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}

// Kullanım
const clips = await createAndWaitForClips('Z3TMbaX_X0k', [
  { start: 0, end: 10 },
  { start: 10, end: 20 }
]);
```

---

## Python Örneği

```python
import requests
import time

def create_and_wait_for_clips(video_id, clips):
    # 1. Job başlat
    response = requests.post('http://localhost:5000/api/create-clips', json={
        'video_id': video_id,
        'clips': clips
    })
    
    data = response.json()
    job_id = data['job_id']
    print(f"Job ID: {job_id}")
    print(f"Clip dosyaları: {data['clip_filenames']}")
    
    # 2. Job durumunu kontrol et (polling)
    while True:
        check_response = requests.get(f'http://localhost:5000/api/check-job/{job_id}')
        job_status = check_response.json()
        
        print(f"Durum: {job_status['status']} | İşlenen: {job_status['processed']}/{job_status['total']}")
        
        if job_status['status'] == 'completed':
            print('✅ Tamamlandı!')
            return job_status['clips']
        elif job_status['status'] == 'failed':
            raise Exception(job_status['error'])
        
        time.sleep(2)  # 2 saniye bekle

# Kullanım
clips = create_and_wait_for_clips('Z3TMbaX_X0k', [
    {'start': 0, 'end': 10},
    {'start': 10, 'end': 20}
])
```
