from flask import Flask, request, jsonify, send_from_directory, url_for
from pytubefix import YouTube
from pytubefix.cli import on_progress
import subprocess
import os
import hashlib
import time
from pathlib import Path

app = Flask(__name__)

# Kesitlerin kaydedileceği klasör
CLIPS_FOLDER = "clips"
Path(CLIPS_FOLDER).mkdir(exist_ok=True)

def generate_clip_filename(video_id, start, end):
    """Dosya adı oluştur: videoID_start-end.mp4"""
    # Dosya adı için güvenli format
    return f"{video_id}_{start}-{end}.mp4"

def download_and_cut_clip(video_id, start, end):
    """YouTube videosundan kesit indir ve kes"""
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Dosya adı oluştur: videoID_start-end.mp4
        output_file = generate_clip_filename(video_id, start, end)
        output_path = os.path.join(CLIPS_FOLDER, output_file)
        
        # Eğer dosya zaten varsa, tekrar indirme
        if os.path.exists(output_path):
            print(f"✅ Kesit zaten mevcut: {output_file}")
            return {"success": True, "filename": output_file}
        
        print(f"İndiriliyor: {video_id} ({start}s - {end}s)")
        
        # YouTube videosunu indir
        # client='IOS' - Yüksek kalite için daha iyi, adaptive stream'leri destekler
        print("🔄 YouTube'dan video indiriliyor (IOS client)...")
        
        # Retry mekanizması - bazen ilk denemede bot koruması devreye girebilir
        max_retries = 3
        yt = None
        last_error = None
        
        for attempt in range(max_retries):
            try:
                yt = YouTube(video_url, client='IOS', on_progress_callback=on_progress)
                print(f"✅ YouTube nesnesi oluşturuldu: {yt.title}")
                break
            except Exception as e:
                last_error = str(e)
                print(f"⚠️ Deneme {attempt + 1}/{max_retries} başarısız: {last_error}")
                if attempt < max_retries - 1:
                    time.sleep(2)  # 2 saniye bekle
        
        if not yt:
            error_msg = f"YouTube nesnesi oluşturulamadı ({max_retries} deneme): {last_error}"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        
        # En yüksek kalitede video stream (adaptive - sadece video)
        video_stream = yt.streams.filter(adaptive=True, file_extension='mp4', only_video=True).order_by('resolution').desc().first()
        
        # En yüksek kalitede audio stream
        audio_stream = yt.streams.filter(adaptive=True, only_audio=True).order_by('abr').desc().first()
        
        if not video_stream:
            error_msg = "Uygun video stream bulunamadı"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Geçici dosyalar
        temp_video = f"temp_video_{output_file}"
        temp_audio = f"temp_audio_{output_file.replace('.mp4', '.m4a')}"
        temp_merged = f"temp_merged_{output_file}"
        
        print(f"📥 Video indiriliyor: {video_stream.resolution} ({video_stream.filesize_mb:.1f} MB)")
        video_stream.download(filename=temp_video)
        
        if audio_stream:
            print(f"🔊 Audio indiriliyor: {audio_stream.abr}")
            audio_stream.download(filename=temp_audio)
            
            # FFmpeg ile video ve audio'yu birleştir
            print(f"🔗 Video ve audio birleştiriliyor...")
            merge_cmd = [
                "ffmpeg",
                "-i", temp_video,
                "-i", temp_audio,
                "-c", "copy",
                "-y",
                temp_merged
            ]
            merge_result = subprocess.run(merge_cmd, capture_output=True, text=True)
            
            # Geçici dosyaları temizle
            if os.path.exists(temp_video):
                os.remove(temp_video)
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
            
            if merge_result.returncode != 0:
                error_msg = f"Video birleştirme hatası: {merge_result.stderr}"
                print(f"❌ {error_msg}")
                return {"success": False, "error": error_msg}
            
            temp_file = temp_merged
        else:
            # Audio yoksa sadece video kullan
            print("⚠️ Audio stream bulunamadı, sadece video kullanılıyor")
            temp_file = temp_video
        
        if not os.path.exists(temp_file):
            error_msg = "Video indirilemedi"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        
        # FFmpeg ile kesit oluştur
        # -c copy yerine re-encode kullan (daha doğru kesim için)
        print(f"✂️ FFmpeg ile kesiliyor: {start}s - {end}s")
        cmd = [
            "ffmpeg",
            "-i", temp_file,
            "-ss", str(start),
            "-to", str(end),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-preset", "fast",
            "-y",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Geçici dosyayı sil
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        if result.returncode == 0:
            print(f"✅ Kesit oluşturuldu: {output_file}")
            
            # Video bilgilerini de döndür
            file_size = os.path.getsize(output_path)
            return {
                "success": True, 
                "filename": output_file,
                "video_info": {
                    "title": yt.title,
                    "author": yt.author,
                    "length": yt.length,
                    "resolution": video_stream.resolution,
                    "file_size": file_size,
                    "file_size_mb": round(file_size / (1024 * 1024), 2)
                }
            }
        else:
            error_msg = f"FFmpeg hatası: {result.stderr}"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
            
    except Exception as e:
        error_msg = f"Hata: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}

@app.route('/api/create-clips', methods=['POST'])
def create_clips():
    """
    Kesitler oluştur ve URL'lerini döndür
    
    Request body:
    {
        "video_id": "KDV_-rXGy7A",
        "clips": [
            {
                "start": 0.32,
                "end": 41.56
            }
        ]
    }
    """
    try:
        data = request.json
        video_id = data.get('video_id')
        clips = data.get('clips', [])
        
        if not video_id or not clips:
            return jsonify({
                'success': False,
                'error': 'video_id ve clips gerekli'
            }), 400
        
        results = []
        errors = []
        
        for idx, clip in enumerate(clips):
            start = clip.get('start')
            end = clip.get('end')
            
            if start is None or end is None:
                errors.append({
                    'index': idx,
                    'error': 'start ve end değerleri gerekli',
                    'clip': clip
                })
                continue
            
            # Kesit oluştur
            result = download_and_cut_clip(video_id, start, end)
            
            if result.get('success'):
                filename = result['filename']
                video_info = result.get('video_info', {})
                
                # URL oluştur
                clip_url = url_for('serve_clip', filename=filename, _external=True)
                
                results.append({
                    'start': start,
                    'end': end,
                    'url': clip_url,
                    'filename': filename,
                    'video_title': video_info.get('title'),
                    'video_author': video_info.get('author'),
                    'resolution': video_info.get('resolution'),
                    'file_size_mb': video_info.get('file_size_mb')
                })
            else:
                errors.append({
                    'index': idx,
                    'error': result.get('error', 'Bilinmeyen hata'),
                    'clip': {'start': start, 'end': end}
                })
        
        return jsonify({
            'success': len(results) > 0,
            'video_id': video_id,
            'clips': results,
            'total': len(results),
            'errors': errors if errors else None,
            'error_count': len(errors)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/clips/<filename>')
def serve_clip(filename):
    """Kesit dosyasını sun"""
    return send_from_directory(CLIPS_FOLDER, filename)

@app.route('/api/clips', methods=['GET'])
def list_clips():
    """Mevcut kesitleri listele"""
    clips = []
    for filename in os.listdir(CLIPS_FOLDER):
        if filename.endswith('.mp4'):
            file_path = os.path.join(CLIPS_FOLDER, filename)
            file_size = os.path.getsize(file_path)
            clips.append({
                'filename': filename,
                'url': url_for('serve_clip', filename=filename, _external=True),
                'size': file_size
            })
    
    return jsonify({
        'success': True,
        'clips': clips,
        'total': len(clips)
    })

@app.route('/')
def index():
    """API bilgisi"""
    return jsonify({
        'name': 'YouTube Clip API',
        'version': '1.0',
        'endpoints': {
            'POST /api/create-clips': 'Kesitler oluştur',
            'GET /api/clips': 'Mevcut kesitleri listele',
            'GET /clips/<filename>': 'Kesit dosyasını indir'
        }
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
