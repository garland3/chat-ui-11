#!/usr/bin/env python3
"""
Integration test script for the S3 mock service.

This script tests the S3 mock service end-to-end by actually starting
the service and making HTTP requests to it.

Run this script to verify the S3 mock service works correctly:
    python test_s3_mock_integration.py
"""

import asyncio
import base64
import json
import subprocess
import time
import httpx
import signal
import os
from datetime import datetime


class S3MockTester:
    """Test harness for S3 mock service integration tests."""
    
    def __init__(self):
        self.base_url = "http://127.0.0.1:8003"
        self.user_email = "test@example.com"
        self.mock_process = None
    
    def start_mock_service(self):
        """Start the S3 mock service."""
        print("🚀 Starting S3 mock service...")
        
        # Change to the mock directory
        mock_dir = os.path.join(os.path.dirname(__file__), "..", "..", "mocks", "s3-mock")
        
        try:
            self.mock_process = subprocess.Popen(
                ["python", "main.py"],
                cwd=mock_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, "HOST": "127.0.0.1", "PORT": "8003"}
            )
            
            # Wait for service to start
            print("⏳ Waiting for service to start...")
            time.sleep(3)
            
            if self.mock_process.poll() is not None:
                stdout, stderr = self.mock_process.communicate()
                print(f"❌ Mock service failed to start!")
                print(f"STDOUT: {stdout.decode()}")
                print(f"STDERR: {stderr.decode()}")
                return False
            
            print("✅ S3 mock service started successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start mock service: {e}")
            return False
    
    def stop_mock_service(self):
        """Stop the S3 mock service."""
        if self.mock_process:
            print("🛑 Stopping S3 mock service...")
            self.mock_process.terminate()
            try:
                self.mock_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.mock_process.kill()
                self.mock_process.wait()
            print("✅ S3 mock service stopped")
    
    async def test_health_check(self):
        """Test the health check endpoint."""
        print("\n🔍 Testing health check...")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Health check passed: {data['status']}")
                    print(f"   Service: {data['service']}")
                    print(f"   Total files: {data['total_files']}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def test_upload_file(self):
        """Test file upload functionality."""
        print("\n📤 Testing file upload...")
        
        # Create test file content
        test_content = "Hello, S3 Mock World!"
        content_base64 = base64.b64encode(test_content.encode()).decode()
        
        payload = {
            "filename": "test.txt",
            "content_base64": content_base64,
            "content_type": "text/plain",
            "tags": {"source": "user", "test": "true"}
        }
        
        headers = {
            "Authorization": f"Bearer {self.user_email}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/files",
                    json=payload,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ File uploaded successfully")
                    print(f"   Key: {data['key']}")
                    print(f"   Size: {data['size']} bytes")
                    print(f"   ETag: {data['etag']}")
                    return data["key"]
                else:
                    print(f"❌ Upload failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return None
    
    async def test_get_file(self, file_key):
        """Test file retrieval functionality."""
        print("\n📥 Testing file download...")
        
        headers = {
            "Authorization": f"Bearer {self.user_email}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/files/{file_key}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = base64.b64decode(data["content_base64"]).decode()
                    print(f"✅ File retrieved successfully")
                    print(f"   Filename: {data['filename']}")
                    print(f"   Content: {content}")
                    print(f"   Content Type: {data['content_type']}")
                    return True
                else:
                    print(f"❌ Download failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Download error: {e}")
            return False
    
    async def test_list_files(self):
        """Test file listing functionality."""
        print("\n📋 Testing file listing...")
        
        headers = {
            "Authorization": f"Bearer {self.user_email}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/files",
                    headers=headers
                )
                
                if response.status_code == 200:
                    files = response.json()
                    print(f"✅ Files listed successfully")
                    print(f"   Found {len(files)} files")
                    for file in files:
                        print(f"   - {file['filename']} ({file['size']} bytes)")
                    return files
                else:
                    print(f"❌ List failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return []
                    
        except Exception as e:
            print(f"❌ List error: {e}")
            return []
    
    async def test_user_stats(self):
        """Test user statistics functionality."""
        print("\n📊 Testing user statistics...")
        
        headers = {
            "Authorization": f"Bearer {self.user_email}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/users/{self.user_email}/files/stats",
                    headers=headers
                )
                
                if response.status_code == 200:
                    stats = response.json()
                    print(f"✅ Statistics retrieved successfully")
                    print(f"   Total files: {stats['total_files']}")
                    print(f"   Total size: {stats['total_size']} bytes")
                    print(f"   Uploaded: {stats['upload_count']}")
                    print(f"   Generated: {stats['generated_count']}")
                    return True
                else:
                    print(f"❌ Stats failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Stats error: {e}")
            return False
    
    async def test_delete_file(self, file_key):
        """Test file deletion functionality."""
        print("\n🗑️ Testing file deletion...")
        
        headers = {
            "Authorization": f"Bearer {self.user_email}"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/files/{file_key}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ File deleted successfully")
                    print(f"   Message: {data['message']}")
                    return True
                else:
                    print(f"❌ Delete failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Delete error: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all integration tests."""
        print("🧪 Running S3 Mock Service Integration Tests")
        print("=" * 50)
        
        # Start the service
        if not self.start_mock_service():
            return False
        
        try:
            # Run tests
            tests_passed = 0
            total_tests = 6
            
            # Test 1: Health check
            if await self.test_health_check():
                tests_passed += 1
            
            # Test 2: Upload file
            file_key = await self.test_upload_file()
            if file_key:
                tests_passed += 1
                
                # Test 3: Get file (only if upload succeeded)
                if await self.test_get_file(file_key):
                    tests_passed += 1
                
                # Test 4: List files
                if await self.test_list_files():
                    tests_passed += 1
                
                # Test 5: User stats
                if await self.test_user_stats():
                    tests_passed += 1
                
                # Test 6: Delete file
                if await self.test_delete_file(file_key):
                    tests_passed += 1
            
            # Results
            print("\n" + "=" * 50)
            print(f"🏁 Tests completed: {tests_passed}/{total_tests} passed")
            
            if tests_passed == total_tests:
                print("🎉 All tests passed! S3 mock service is working correctly.")
                return True
            else:
                print(f"⚠️  {total_tests - tests_passed} test(s) failed.")
                return False
                
        finally:
            self.stop_mock_service()


async def main():
    """Main test function."""
    tester = S3MockTester()
    
    try:
        success = await tester.run_all_tests()
        exit_code = 0 if success else 1
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        exit_code = 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        exit_code = 1
    finally:
        tester.stop_mock_service()
    
    exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())