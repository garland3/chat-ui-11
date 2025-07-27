#!/usr/bin/env python3
"""Test script to verify custom prompting functionality."""

import asyncio
import logging
import sys
import os

# Add the backend directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_client import MCPToolManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_prompts_functionality():
    """Test the custom prompts functionality."""
    logger.info("Testing custom prompts functionality...")
    
    # Initialize MCP manager
    mcp_manager = MCPToolManager()
    
    try:
        # Initialize clients
        logger.info("Initializing MCP clients...")
        await mcp_manager.initialize_clients()
        
        # Discover tools
        logger.info("Discovering tools...")
        await mcp_manager.discover_tools()
        
        # Discover prompts
        logger.info("Discovering prompts...")
        await mcp_manager.discover_prompts()
        
        # Check if prompts server is available
        if "prompts" in mcp_manager.available_prompts:
            prompts_info = mcp_manager.available_prompts["prompts"]
            logger.info(f"Found prompts server with {len(prompts_info['prompts'])} prompts")
            
            for prompt in prompts_info['prompts']:
                logger.info(f"  - {prompt.name}: {prompt.description}")
        else:
            logger.warning("Prompts server not found in available_prompts")
            logger.info(f"Available servers: {list(mcp_manager.available_prompts.keys())}")
        
        # Test getting available prompts for the prompts server
        if "prompts" in mcp_manager.available_prompts:
            available_prompts = mcp_manager.get_available_prompts_for_servers(["prompts"])
            logger.info(f"Available prompts: {list(available_prompts.keys())}")
            
            # Test getting a specific prompt
            if available_prompts:
                first_prompt_key = list(available_prompts.keys())[0]
                prompt_info = available_prompts[first_prompt_key]
                logger.info(f"Testing prompt: {prompt_info['name']}")
                
                try:
                    prompt_result = await mcp_manager.get_prompt(
                        prompt_info['server'], 
                        prompt_info['name']
                    )
                    logger.info(f"Successfully retrieved prompt: {prompt_result}")
                    
                    if hasattr(prompt_result, 'messages'):
                        for message in prompt_result.messages:
                            logger.info(f"  Message role: {message.role}")
                            if hasattr(message.content, 'text'):
                                logger.info(f"  Content: {message.content.text[:100]}...")
                    
                except Exception as e:
                    logger.error(f"Error retrieving prompt: {e}")
        
        logger.info("Custom prompts functionality test completed!")
        
    except Exception as e:
        logger.error(f"Error during testing: {e}", exc_info=True)
    
    finally:
        await mcp_manager.cleanup()


if __name__ == "__main__":
    asyncio.run(test_prompts_functionality())