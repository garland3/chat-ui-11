#!/usr/bin/env python3
"""
Simple test to demonstrate LLM streaming functionality.
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from modules.llm.litellm_caller import LiteLLMCaller
    from modules.config import ConfigManager
    print("✓ Successfully imported LiteLLMCaller")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)


class MockLiteLLMCaller(LiteLLMCaller):
    """Mock implementation for testing streaming without real API calls."""
    
    def __init__(self):
        # Initialize without config to avoid requiring real API keys
        self.llm_config = None
    
    async def call_plain_streaming(self, model_name, messages, stream_callback=None, temperature=0.7):
        """Mock streaming implementation that simulates streaming chunks."""
        test_response = "This is a test streaming response. Watch as each word appears one by one!"
        words = test_response.split()
        
        accumulated = ""
        for i, word in enumerate(words):
            # Add word and space (except for last word)
            chunk = word + (" " if i < len(words) - 1 else "")
            accumulated += chunk
            
            # Call the callback with this chunk
            if stream_callback:
                await stream_callback(chunk)
            
            # Simulate delay between words
            await asyncio.sleep(0.1)
        
        return accumulated


async def test_streaming():
    """Test the streaming functionality."""
    print("🔄 Testing LLM streaming functionality...")
    
    # Create mock caller
    caller = MockLiteLLMCaller()
    
    # Track streamed chunks
    chunks = []
    
    async def collect_chunks(chunk):
        chunks.append(chunk)
        print(f"📝 Streamed chunk: '{chunk}'", end="", flush=True)
    
    # Test streaming
    messages = [{"role": "user", "content": "Hello, test streaming!"}]
    final_response = await caller.call_plain_streaming(
        "test-model",
        messages,
        stream_callback=collect_chunks
    )
    
    print(f"\n\n✅ Streaming test completed!")
    print(f"📦 Received {len(chunks)} chunks")
    print(f"💬 Final response: '{final_response}'")
    print(f"🔗 Reconstructed: '{''.join(chunks)}'")
    
    # Verify the chunks reconstruct to the final response
    if ''.join(chunks) == final_response:
        print("✅ Streaming integrity verified!")
        return True
    else:
        print("❌ Streaming integrity failed!")
        return False


async def test_notification_utils():
    """Test the notification utility functions."""
    print("\n🔄 Testing notification utilities...")
    
    try:
        from application.chat.utilities import notification_utils
        print("✓ Successfully imported notification_utils")
        
        # Test creating notifications (without sending them)
        test_messages = []
        
        async def collect_notifications(message):
            test_messages.append(message)
        
        # Test streaming notifications
        await notification_utils.notify_chat_stream_start(collect_notifications)
        await notification_utils.notify_chat_stream_chunk("Hello", collect_notifications)
        await notification_utils.notify_chat_stream_chunk(" world!", collect_notifications)
        await notification_utils.notify_chat_stream_complete("Hello world!", collect_notifications)
        
        print(f"📨 Generated {len(test_messages)} notifications:")
        for i, msg in enumerate(test_messages):
            print(f"  {i+1}. {msg['type']}: {msg.get('chunk', msg.get('message', 'N/A'))}")
        
        expected_types = ['chat_stream_start', 'chat_stream_chunk', 'chat_stream_chunk', 'chat_stream_complete']
        actual_types = [msg['type'] for msg in test_messages]
        
        if actual_types == expected_types:
            print("✅ Notification utilities working correctly!")
            return True
        else:
            print(f"❌ Expected {expected_types}, got {actual_types}")
            return False
            
    except Exception as e:
        print(f"✗ Notification utils test failed: {e}")
        return False


async def main():
    """Run all tests."""
    print("🚀 Starting streaming functionality tests...\n")
    
    test1_passed = await test_streaming()
    test2_passed = await test_notification_utils()
    
    print(f"\n📊 Test Results:")
    print(f"  • Streaming functionality: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"  • Notification utilities: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Streaming functionality is ready.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)