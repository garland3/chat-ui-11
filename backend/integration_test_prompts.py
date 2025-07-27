#!/usr/bin/env python3
"""
Comprehensive integration test for custom prompting functionality.
"""

import asyncio
import logging
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_client import MCPToolManager

# Set up logging
logging.basicConfig(level=logging.WARNING)  # Reduce noise
logger = logging.getLogger(__name__)


async def integration_test():
    """Run comprehensive integration test for custom prompting."""
    
    print("🧪 COMPREHENSIVE INTEGRATION TEST")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: MCP Manager Initialization
    total_tests += 1
    print(f"Test {total_tests}: MCP Manager Initialization...")
    try:
        mcp_manager = MCPToolManager()
        assert hasattr(mcp_manager, 'available_prompts')
        print("✅ PASS")
        tests_passed += 1
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 2: Client Initialization
    total_tests += 1
    print(f"Test {total_tests}: Client Initialization...")
    try:
        await mcp_manager.initialize_clients()
        assert 'prompts' in mcp_manager.clients
        print("✅ PASS")
        tests_passed += 1
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 3: Tools Discovery
    total_tests += 1
    print(f"Test {total_tests}: Tools Discovery...")
    try:
        await mcp_manager.discover_tools()
        assert 'prompts' in mcp_manager.available_tools
        print("✅ PASS")
        tests_passed += 1
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 4: Prompts Discovery
    total_tests += 1
    print(f"Test {total_tests}: Prompts Discovery...")
    try:
        await mcp_manager.discover_prompts()
        assert 'prompts' in mcp_manager.available_prompts
        prompts_info = mcp_manager.available_prompts['prompts']
        assert len(prompts_info['prompts']) >= 3  # Should have at least our 3 expert prompts
        print("✅ PASS")
        tests_passed += 1
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 5: Available Prompts Retrieval
    total_tests += 1
    print(f"Test {total_tests}: Available Prompts Retrieval...")
    try:
        available_prompts = mcp_manager.get_available_prompts_for_servers(['prompts'])
        assert 'prompts_financial_tech_wizard' in available_prompts
        assert 'prompts_expert_dog_trainer' in available_prompts
        assert 'prompts_creative_writer' in available_prompts
        print("✅ PASS")
        tests_passed += 1
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 6: Specific Prompt Retrieval
    total_tests += 1
    print(f"Test {total_tests}: Specific Prompt Retrieval...")
    try:
        prompt_result = await mcp_manager.get_prompt('prompts', 'financial_tech_wizard')
        assert prompt_result is not None
        assert hasattr(prompt_result, 'messages')
        assert len(prompt_result.messages) > 0
        assert 'financial technology wizard' in prompt_result.messages[0].content.text.lower()
        print("✅ PASS")
        tests_passed += 1
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 7: Multiple Prompt Types
    total_tests += 1
    print(f"Test {total_tests}: Multiple Prompt Types...")
    try:
        dog_trainer_prompt = await mcp_manager.get_prompt('prompts', 'expert_dog_trainer')
        creative_writer_prompt = await mcp_manager.get_prompt('prompts', 'creative_writer')
        
        assert 'dog trainer' in dog_trainer_prompt.messages[0].content.text.lower()
        assert 'creative writing' in creative_writer_prompt.messages[0].content.text.lower()
        print("✅ PASS")
        tests_passed += 1
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Test 8: Prompt Content Format
    total_tests += 1
    print(f"Test {total_tests}: Prompt Content Format...")
    try:
        prompt_result = await mcp_manager.get_prompt('prompts', 'financial_tech_wizard')
        content = prompt_result.messages[0].content.text
        assert 'System:' in content
        assert 'User:' in content
        # Should be structured as expected for our system prompt extraction
        print("✅ PASS")
        tests_passed += 1
    except Exception as e:
        print(f"❌ FAIL: {e}")
    
    # Cleanup
    await mcp_manager.cleanup()
    
    # Results
    print()
    print("=" * 50)
    print(f"INTEGRATION TEST RESULTS: {tests_passed}/{total_tests} PASSED")
    
    if tests_passed == total_tests:
        print("🎉 ALL TESTS PASSED! Custom prompting system is fully functional.")
        print()
        print("📋 VERIFIED FEATURES:")
        print("• MCP client initialization and discovery")
        print("• Prompts server connection and communication")
        print("• Multiple expert prompt types (financial, dog training, creative writing)")
        print("• Correct prompt content format and structure")
        print("• Integration with existing MCP tool system")
        return True
    else:
        print(f"❌ {total_tests - tests_passed} tests failed. Check implementation.")
        return False


if __name__ == "__main__":
    success = asyncio.run(integration_test())
    sys.exit(0 if success else 1)