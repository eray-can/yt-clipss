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

# YouTube po_token ve visitor_data (environment variables'dan oku)
PO_TOKEN = os.getenv('YOUTUBE_PO_TOKEN')
VISITOR_DATA = os.getenv('YOUTUBE_VISITOR_DATA')

def generate_clip_id(video_id, start, end):
    """Benzersiz clip ID oluştur"""
    unique_string = f"{video_id}_{start}_{end}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:12]

def download_and_cut_clip(video_id, start, end, caption):
    """YouTube videosundan kesit indir ve kes"""
    try:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Clip ID ve dosya adı oluştur
        clip_id = generate_clip_id(video_id, start, end)
        output_file = f"{clip_id}.mp4"
        output_path = os.path.join(CLIPS_FOLDER, output_file)
        
        # Eğer dosya zaten varsa, tekrar indirme
        if os.path.exists(output_path):
            print(f"✅ Kesit zaten mevcut: {output_file}")
            return {"success": True, "filename": output_file}
        
        print(f"İndiriliyor: {video_id} ({start}s - {end}s)")
        
        # YouTube videosunu indir (po_token ile)
        if PO_TOKEN and VISITOR_DATA:
            yt = YouTube(video_url, po_token=PO_TOKEN, visitor_data=VISITOR_DATA, on_progress_callback=on_progress)
            print("✅ po_token kullanılıyor")
        else:
            yt = YouTube(video_url, on_progress_callback=on_progress)
            print("⚠️ po_token yok, bot koruması ile karşılaşabilirsiniz")
        
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        
        if not stream:
            error_msg = "Uygun video stream bulunamadı"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        
        # Geçici dosya
        temp_file = f"temp_{clip_id}.mp4"
        print(f"Video indiriliyor: {stream.resolution}")
        stream.download(filename=temp_file)
        
        if not os.path.exists(temp_file):
            error_msg = "Video indirilemedi"
            print(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
        
        # FFmpeg ile kesit oluştur
        print(f"FFmpeg ile kesiliyor: {start}s - {end}s")
        cmd = [
            "ffmpeg",
            "-i", temp_file,
            "-ss", str(start),
            "-to", str(end),
            "-c", "copy",
            "-y",
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Geçici dosyayı sil
        if os.path.exists(temp_file):
            os.remove(temp_file)
        
        if result.returncode == 0:
            print(f"✅ Kesit oluşturuldu: {output_file}")
            return {"success": True, "filename": output_file}
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
                "end": 41.56,
                "duration": 41.24,
                "text": "...",
                "caption": "..."
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
            caption = clip.get('caption', '')
            
            if start is None or end is None:
                errors.append({
                    'index': idx,
                    'error': 'start ve end değerleri gerekli',
                    'clip': clip
                })
                continue
            
            # Kesit oluştur
            result = download_and_cut_clip(video_id, start, end, caption)
            
            if result.get('success'):
                filename = result['filename']
                # URL oluştur
                clip_url = url_for('serve_clip', filename=filename, _external=True)
                
                results.append({
                    'caption': caption,
                    'start': start,
                    'end': end,
                    'duration': clip.get('duration'),
                    'url': clip_url,
                    'filename': filename
                })
            else:
                errors.append({
                    'index': idx,
                    'error': result.get('error', 'Bilinmeyen hata'),
                    'clip': {'start': start, 'end': end, 'caption': caption}
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
