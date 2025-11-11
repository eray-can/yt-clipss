"""
Unit tests for the YouTube clip API
Tests individual functions and edge cases
"""
import unittest
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import (
    generate_clip_filename,
    get_job,
    save_job,
    delete_job,
    process_clips_async
)

class TestJobManagement(unittest.TestCase):
    """Test job file management functions"""
    
    def setUp(self):
        """Create temporary jobs folder for testing"""
        self.test_jobs_folder = tempfile.mkdtemp()
        self.original_jobs_folder = os.environ.get('JOBS_FOLDER')
        
        # Patch JOBS_FOLDER in app module
        import app
        self.original_app_jobs_folder = app.JOBS_FOLDER
        app.JOBS_FOLDER = self.test_jobs_folder
    
    def tearDown(self):
        """Clean up temporary folder"""
        import app
        app.JOBS_FOLDER = self.original_app_jobs_folder
        
        if os.path.exists(self.test_jobs_folder):
            shutil.rmtree(self.test_jobs_folder)
    
    def test_save_and_get_job(self):
        """Test saving and retrieving a job"""
        job_id = "test-job-123"
        job_data = {
            'job_id': job_id,
            'video_id': 'test-video',
            'status': 'pending',
            'total': 5,
            'processed': 0
        }
        
        # Save job
        save_job(job_id, job_data)
        
        # Retrieve job
        retrieved_job = get_job(job_id)
        
        self.assertIsNotNone(retrieved_job)
        self.assertEqual(retrieved_job['job_id'], job_id)
        self.assertEqual(retrieved_job['video_id'], 'test-video')
        self.assertEqual(retrieved_job['status'], 'pending')
    
    def test_get_nonexistent_job(self):
        """Test retrieving a job that doesn't exist"""
        result = get_job("nonexistent-job")
        self.assertIsNone(result)
    
    def test_delete_job(self):
        """Test deleting a job"""
        job_id = "test-job-delete"
        job_data = {'job_id': job_id, 'status': 'finished'}
        
        # Save and then delete
        save_job(job_id, job_data)
        self.assertIsNotNone(get_job(job_id))
        
        delete_job(job_id)
        self.assertIsNone(get_job(job_id))
    
    def test_update_job_status(self):
        """Test updating job status"""
        job_id = "test-job-update"
        job_data = {
            'job_id': job_id,
            'status': 'pending',
            'processed': 0
        }
        
        # Save initial job
        save_job(job_id, job_data)
        
        # Update status
        job = get_job(job_id)
        job['status'] = 'processing'
        job['processed'] = 3
        save_job(job_id, job)
        
        # Verify update
        updated_job = get_job(job_id)
        self.assertEqual(updated_job['status'], 'processing')
        self.assertEqual(updated_job['processed'], 3)

class TestFilenameGeneration(unittest.TestCase):
    """Test filename generation"""
    
    def test_generate_clip_filename(self):
        """Test clip filename generation"""
        video_id = "dQw4w9WgXcQ"
        start = 10.5
        end = 25.3
        
        filename = generate_clip_filename(video_id, start, end)
        
        self.assertEqual(filename, "dQw4w9WgXcQ-10.5-25.3.mp4")
    
    def test_generate_clip_filename_integers(self):
        """Test clip filename with integer timestamps"""
        video_id = "test123"
        start = 0
        end = 60
        
        filename = generate_clip_filename(video_id, start, end)
        
        self.assertEqual(filename, "test123-0-60.mp4")

class TestProcessClipsAsync(unittest.TestCase):
    """Test async clip processing logic"""
    
    def setUp(self):
        """Set up test environment"""
        self.test_jobs_folder = tempfile.mkdtemp()
        self.test_clips_folder = tempfile.mkdtemp()
        
        import app
        self.original_jobs_folder = app.JOBS_FOLDER
        self.original_clips_folder = app.CLIPS_FOLDER
        app.JOBS_FOLDER = self.test_jobs_folder
        app.CLIPS_FOLDER = self.test_clips_folder
    
    def tearDown(self):
        """Clean up"""
        import app
        app.JOBS_FOLDER = self.original_jobs_folder
        app.CLIPS_FOLDER = self.original_clips_folder
        
        if os.path.exists(self.test_jobs_folder):
            shutil.rmtree(self.test_jobs_folder)
        if os.path.exists(self.test_clips_folder):
            shutil.rmtree(self.test_clips_folder)
    
    @patch('app.cut_clip_from_url')
    def test_process_clips_all_success(self, mock_cut_clip):
        """Test processing clips when all succeed"""
        # Mock successful clip creation
        mock_cut_clip.return_value = {
            'success': True,
            'filename': 'test-0-10.mp4',
            'video_info': {
                'title': 'Test Video',
                'resolution': '720p',
                'file_size': 1024000,
                'file_size_mb': 1.0
            }
        }
        
        job_id = "test-job-success"
        video_id = "test-video"
        clips = [
            {'start': 0, 'end': 10},
            {'start': 10, 'end': 20}
        ]
        
        # Create initial job
        job_data = {
            'job_id': job_id,
            'video_id': video_id,
            'status': 'pending',
            'total': len(clips),
            'processed': 0
        }
        save_job(job_id, job_data)
        
        # Process clips
        process_clips_async(
            job_id, video_id, clips,
            'http://video.url', 'http://audio.url',
            'Test Video', '720p'
        )
        
        # Check job status
        final_job = get_job(job_id)
        self.assertEqual(final_job['status'], 'finished')
        self.assertEqual(final_job['processed'], 2)
        self.assertEqual(len(final_job['results']), 2)
        self.assertEqual(len(final_job['errors']), 0)
    
    @patch('app.cut_clip_from_url')
    def test_process_clips_with_errors(self, mock_cut_clip):
        """Test processing clips when some fail"""
        # Mock mixed results
        def side_effect(*args, **kwargs):
            # cut_clip_from_url(video_url, audio_url, video_id, start, end, title, resolution)
            start = args[3]  # start is the 4th argument (index 3)
            if start == 0:
                return {'success': True, 'filename': 'test-0-10.mp4', 'video_info': {'title': 'Test', 'resolution': '720p', 'file_size': 1024, 'file_size_mb': 0.001}}
            else:
                return {'success': False, 'error': 'Failed to process'}
        
        mock_cut_clip.side_effect = side_effect
        
        job_id = "test-job-errors"
        video_id = "test-video"
        clips = [
            {'start': 0, 'end': 10},
            {'start': 10, 'end': 20},
            {'start': 20, 'end': 30}
        ]
        
        # Create initial job
        job_data = {
            'job_id': job_id,
            'video_id': video_id,
            'status': 'pending',
            'total': len(clips),
            'processed': 0
        }
        save_job(job_id, job_data)
        
        # Process clips
        process_clips_async(
            job_id, video_id, clips,
            'http://video.url', 'http://audio.url',
            'Test Video', '720p'
        )
        
        # Check job status
        final_job = get_job(job_id)
        self.assertEqual(final_job['status'], 'finished')
        self.assertEqual(final_job['processed'], 3)
        self.assertEqual(len(final_job['results']), 1)
        self.assertEqual(len(final_job['errors']), 2)
    
    @patch('app.cut_clip_from_url')
    def test_process_clips_invalid_data(self, mock_cut_clip):
        """Test processing clips with invalid data"""
        job_id = "test-job-invalid"
        video_id = "test-video"
        clips = [
            {'start': 0, 'end': 10},
            {'start': None, 'end': 20},  # Invalid: missing start
            {'start': 20},  # Invalid: missing end
        ]
        
        # Create initial job
        job_data = {
            'job_id': job_id,
            'video_id': video_id,
            'status': 'pending',
            'total': len(clips),
            'processed': 0
        }
        save_job(job_id, job_data)
        
        # Mock successful clip creation for valid clip
        mock_cut_clip.return_value = {
            'success': True,
            'filename': 'test-0-10.mp4',
            'video_info': {'title': 'Test', 'resolution': '720p', 'file_size': 1024, 'file_size_mb': 0.001}
        }
        
        # Process clips
        process_clips_async(
            job_id, video_id, clips,
            'http://video.url', 'http://audio.url',
            'Test Video', '720p'
        )
        
        # Check job status
        final_job = get_job(job_id)
        self.assertEqual(final_job['status'], 'finished')
        self.assertEqual(final_job['processed'], 3)
        self.assertEqual(len(final_job['results']), 1)  # Only 1 valid clip
        self.assertEqual(len(final_job['errors']), 2)  # 2 invalid clips
    
    @patch('app.cut_clip_from_url')
    def test_process_clips_exception_handling(self, mock_cut_clip):
        """Test that exceptions during clip processing are handled"""
        # Mock exception
        mock_cut_clip.side_effect = Exception("Unexpected error")
        
        job_id = "test-job-exception"
        video_id = "test-video"
        clips = [{'start': 0, 'end': 10}]
        
        # Create initial job
        job_data = {
            'job_id': job_id,
            'video_id': video_id,
            'status': 'pending',
            'total': len(clips),
            'processed': 0
        }
        save_job(job_id, job_data)
        
        # Process clips - should not crash
        process_clips_async(
            job_id, video_id, clips,
            'http://video.url', 'http://audio.url',
            'Test Video', '720p'
        )
        
        # Check job status - should be finished with errors
        final_job = get_job(job_id)
        self.assertEqual(final_job['status'], 'finished')
        self.assertEqual(final_job['processed'], 1)
        self.assertEqual(len(final_job['errors']), 1)
        self.assertIn('exception', final_job['errors'][0]['error'].lower())

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error scenarios"""
    
    def test_empty_clips_list(self):
        """Test processing with empty clips list"""
        # This should be handled gracefully
        pass
    
    def test_very_long_clip(self):
        """Test processing a very long clip"""
        # Should handle long durations
        pass
    
    def test_zero_duration_clip(self):
        """Test clip with start == end"""
        # Should handle or reject gracefully
        pass

if __name__ == '__main__':
    print("="*60)
    print("UNIT TESTS FOR YOUTUBE CLIP API")
    print("="*60)
    unittest.main(verbosity=2)
