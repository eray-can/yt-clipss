# Testing Guide

## Quick Start

### 1. Run All Tests
```bash
python run_tests.py
```

Bu script tüm testleri otomatik çalıştırır ve özet sunar.

## Individual Tests

### Unit Tests (Server Gerekmez)
```bash
python test_unit.py
```

**Test edilen:**
- ✅ Job save/get/delete operations
- ✅ Filename generation
- ✅ Async clip processing logic
- ✅ Exception handling
- ✅ Invalid data handling

**Süre:** ~5 saniye

### Integration Tests (Server Gerekir)

#### 1. Async Processing Test
```bash
python test_async.py
```

**Test edilen:**
- 5 clip ile async processing
- Job status monitoring
- Progress tracking

**Süre:** ~30-60 saniye

#### 2. Multiple Checks Test
```bash
python test_multiple_checks.py
```

**Test edilen:**
- Job durumunun birden fazla kez sorgulanması
- Job persistence
- Status consistency

**Süre:** ~20 saniye

#### 3. Multi-Video Test (En Kapsamlı)
```bash
python test_multi_video.py
```

**Test edilen:**
- 3 farklı video sequential processing
- Concurrent same video processing
- Error recovery (invalid → valid video)

**Süre:** ~5-10 dakika (3 video indirme + processing)

## Test Scenarios

### Scenario 1: Normal Operation
```python
# 1 video, 3 clips
data = {
    "video_id": "Z3TMbaX_X0k",
    "clips": [
        {"start": 0, "end": 10},
        {"start": 10, "end": 20},
        {"start": 20, "end": 30}
    ]
}
```

**Beklenen:**
- ✅ Job başarıyla tamamlanır
- ✅ 3 clip oluşturulur
- ✅ Hata yok

### Scenario 2: Partial Failure
```python
# Invalid clip data mixed with valid
data = {
    "video_id": "Z3TMbaX_X0k",
    "clips": [
        {"start": 0, "end": 10},      # ✅ Valid
        {"start": None, "end": 20},   # ❌ Invalid
        {"start": 20, "end": 30}      # ✅ Valid
    ]
}
```

**Beklenen:**
- ✅ Job tamamlanır
- ✅ 2 clip oluşturulur
- ✅ 1 error kaydedilir
- ✅ Status = 'finished'

### Scenario 3: Complete Failure
```python
# Invalid video ID
data = {
    "video_id": "INVALID_VIDEO_12345",
    "clips": [{"start": 0, "end": 10}]
}
```

**Beklenen:**
- ✅ Job başlar
- ❌ API'den video URL alınamaz
- ✅ Status = 'failed' veya finished with errors
- ✅ Error message kaydedilir

### Scenario 4: Sequential Videos
```python
# Video 1
job1 = create_clips(video_id="VIDEO_1", clips=[...])

# Video 2 (Video 1 bitmeden)
job2 = create_clips(video_id="VIDEO_2", clips=[...])

# Video 3 (Video 1,2 bitmeden)
job3 = create_clips(video_id="VIDEO_3", clips=[...])
```

**Beklenen:**
- ✅ Her 3 job da bağımsız çalışır
- ✅ Birinin hatası diğerini etkilemez
- ✅ Tüm joblar tamamlanır

## Manual Testing

### Test 1: Single Video
```bash
curl -X POST http://localhost:5000/api/create-clips \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "Z3TMbaX_X0k",
    "clips": [{"start": 0, "end": 5}]
  }'
```

Response:
```json
{
  "success": true,
  "job_id": "abc-123-def",
  "status": "pending",
  "total_clips": 1
}
```

### Test 2: Check Job Status
```bash
curl http://localhost:5000/api/check-job/abc-123-def
```

Response (processing):
```json
{
  "success": true,
  "job_id": "abc-123-def",
  "status": "processing",
  "processed": 0,
  "total": 1
}
```

Response (finished):
```json
{
  "success": true,
  "job_id": "abc-123-def",
  "status": "finished",
  "processed": 1,
  "total": 1,
  "clips": [
    {
      "start": 0,
      "end": 5,
      "filename": "Z3TMbaX_X0k-0-5.mp4",
      "url": "http://localhost:5000/clips/Z3TMbaX_X0k-0-5.mp4"
    }
  ],
  "errors": []
}
```

## Debugging

### Check Logs
Server loglarını kontrol edin:

```
🔄 Processing started for job abc-123 with 3 clips
🎬 Processing clip 1/3: 0s - 10s
🔄 FFmpeg başlatılıyor...
📋 FFmpeg log: ...
✅ Kesit oluşturuldu: Z3TMbaX_X0k-0-10.mp4 (1024000 bytes, 1.0 MB)
✅ Clip 1 processed successfully
🎬 Processing clip 2/3: 10s - 20s
...
✅ Job abc-123 completed: 3 clips, 0 errors
```

### Check Job Files
```bash
# Windows
dir jobs

# Linux/Mac
ls -la jobs/
```

Her job için bir JSON dosyası:
```
abc-123-def.json
xyz-456-ghi.json
```

### Check Clip Files
```bash
# Windows
dir clips

# Linux/Mac
ls -la clips/
```

Oluşturulan clipler:
```
Z3TMbaX_X0k-0-10.mp4
Z3TMbaX_X0k-10-20.mp4
KDV_-rXGy7A-0-5.mp4
```

## Common Issues

### Issue 1: Server Not Running
```
❌ Server is NOT running!
```

**Çözüm:**
```bash
python app.py
```

### Issue 2: FFmpeg Not Found
```
❌ FFmpeg hatası: 'ffmpeg' is not recognized
```

**Çözüm:**
- FFmpeg'i yükleyin: https://ffmpeg.org/download.html
- PATH'e ekleyin

### Issue 3: Timeout Errors
```
❌ FFmpeg timeout (>5 dakika): 100s - 200s
```

**Çözüm:**
- Daha kısa clipler kullanın
- İnternet bağlantınızı kontrol edin
- Timeout süresini artırın (app.py, line 193)

### Issue 4: API Rate Limiting
```
❌ API hatası: 429 Too Many Requests
```

**Çözüm:**
- Requestler arasında bekleme ekleyin
- Farklı API kullanın
- Cache mekanizması ekleyin

## Performance Benchmarks

### Single Clip (10 seconds)
- API call: ~2-3 seconds
- FFmpeg processing: ~5-10 seconds
- **Total: ~7-13 seconds**

### Multiple Clips (5 clips, 10s each)
- API call: ~2-3 seconds (once)
- FFmpeg processing: ~5-10 seconds per clip
- **Total: ~27-53 seconds**

### Multiple Videos (3 videos, 1 clip each)
- API calls: ~6-9 seconds (3x)
- FFmpeg processing: ~15-30 seconds (3x)
- **Total: ~21-39 seconds**

## Best Practices

1. **Always check job status before assuming completion**
   ```python
   while True:
       status = check_job(job_id)
       if status['status'] in ['finished', 'failed']:
           break
       time.sleep(2)
   ```

2. **Handle errors gracefully**
   ```python
   if status['status'] == 'finished':
       clips = status['clips']
       errors = status['errors']
       if errors:
           print(f"⚠️  {len(errors)} clips failed")
   ```

3. **Use appropriate timeouts**
   - Short clips (<30s): 2 dakika timeout
   - Medium clips (30-120s): 5 dakika timeout
   - Long clips (>120s): 10 dakika timeout

4. **Monitor disk space**
   ```python
   # Cleanup old clips periodically
   DELETE /api/clips/all
   ```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Install FFmpeg
        run: sudo apt-get install -y ffmpeg
      
      - name: Install Python dependencies
        run: pip install -r requirements.txt
      
      - name: Run unit tests
        run: python test_unit.py
      
      - name: Start server
        run: python app.py &
        
      - name: Wait for server
        run: sleep 5
      
      - name: Run integration tests
        run: python test_async.py
```

## Conclusion

Test suite ile sistem güvenilirliği doğrulandı:
- ✅ Unit tests: Core functionality
- ✅ Integration tests: Real-world scenarios
- ✅ Multi-video tests: Concurrent processing
- ✅ Error handling: Graceful degradation

Herhangi bir değişiklik sonrası testleri çalıştırın:
```bash
python run_tests.py
```
