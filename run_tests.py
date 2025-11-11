"""
Test runner script
Runs all tests and provides a summary
"""
import subprocess
import sys
import time

def run_command(cmd, description):
    """Run a command and return success status"""
    print("\n" + "="*60)
    print(f"🧪 {description}")
    print("="*60)
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED")
            return False
    except subprocess.TimeoutExpired:
        print(f"⏱️ {description} - TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {str(e)}")
        return False

def check_server_running():
    """Check if Flask server is running"""
    import requests
    try:
        response = requests.get("http://localhost:5000/", timeout=2)
        return response.status_code == 200
    except:
        return False

def main():
    print("="*60)
    print("🚀 YOUTUBE CLIP API - TEST SUITE")
    print("="*60)
    
    results = {}
    
    # 1. Run unit tests
    print("\n📋 Running unit tests...")
    results['unit_tests'] = run_command(
        f"{sys.executable} test_unit.py",
        "Unit Tests"
    )
    
    # 2. Check if server is running for integration tests
    print("\n🔍 Checking if Flask server is running...")
    server_running = check_server_running()
    
    if server_running:
        print("✅ Server is running on http://localhost:5000")
        
        # 3. Run integration tests
        print("\n📋 Running integration tests...")
        
        # Test async processing
        results['async_test'] = run_command(
            f"{sys.executable} test_async.py",
            "Async Processing Test"
        )
        
        time.sleep(2)
        
        # Test multiple checks
        results['multiple_checks'] = run_command(
            f"{sys.executable} test_multiple_checks.py",
            "Multiple Job Checks Test"
        )
        
        time.sleep(2)
        
        # Test multi-video processing
        print("\n⚠️  Multi-video test will take several minutes...")
        print("This test processes 3 different videos sequentially")
        user_input = input("Do you want to run it? (y/n): ")
        
        if user_input.lower() == 'y':
            results['multi_video'] = run_command(
                f"{sys.executable} test_multi_video.py",
                "Multi-Video Processing Test"
            )
        else:
            print("⏭️  Skipping multi-video test")
            results['multi_video'] = None
    else:
        print("❌ Server is NOT running!")
        print("\nTo run integration tests:")
        print("1. Start the Flask server: python app.py")
        print("2. Run this script again")
        results['integration_tests'] = False
    
    # Summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    skipped_tests = 0
    
    for test_name, result in results.items():
        if result is None:
            status = "⏭️  SKIPPED"
            skipped_tests += 1
        elif result:
            status = "✅ PASSED"
            passed_tests += 1
        else:
            status = "❌ FAILED"
            failed_tests += 1
        
        total_tests += 1
        print(f"{test_name:30s} {status}")
    
    print("\n" + "-"*60)
    print(f"Total: {total_tests} | Passed: {passed_tests} | Failed: {failed_tests} | Skipped: {skipped_tests}")
    print("="*60)
    
    if failed_tests > 0:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        sys.exit(1)
    elif skipped_tests == total_tests:
        print("\n⚠️  All tests were skipped.")
        sys.exit(0)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
