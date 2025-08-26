"""
Basic compilation test for backend - Phase 1A prototype.
Tests that all backend code can be imported without syntax errors.
"""

import sys
import importlib
import traceback
from pathlib import Path
import pytest


def test_all_imports_compile():
    """Test that all backend modules can be imported without syntax errors."""
    # print the current dir.
    print(f"Current directory: {Path.cwd()}")

    # Add the backend directory to the Python path
    backend_dir = Path(__file__).parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    # print the added dir
    print(f"Added backend directory to sys.path: {backend_dir}")

    # List of all modules to test for compilation
    modules_to_test = [
        # Main entry point
        'main',
        
        # App factory
        'managers.app_factory',
        
        # Config module
        'managers.config.config_manager',
        'managers.config.config_models',
        
        # Service coordinator
        'managers.service_coordinator.service_coordinator',
        
        # LLM module
        'managers.llm.llm_manager',
        
        # Session module
        'managers.session.session_manager',
        'managers.session.session_models',
        
        # Logger module (empty but should compile)
        'managers.logger.logger_coordinator',
        
        # UI callback module (empty but should compile)
        'managers.ui_callback.ui_callback_handler',
        
        # Other manager modules (empty but should compile)
        'managers.auth.auth_manager',
        'managers.storage.storage_manager',
        'managers.tools.tool_caller',
        'managers.agent.agent_manager',
        'managers.mcp.mcp_manager',
        'managers.rag.rag_manager',
        'managers.admin.admin_manager',
    ]
    
    failed_imports = []
    successful_imports = []
    
    for module_name in modules_to_test:
        try:
            # Try to import the module
            importlib.import_module(module_name)
            successful_imports.append(module_name)
            print(f"✓ {module_name}")
            
        except Exception as e:
            failed_imports.append((module_name, str(e), traceback.format_exc()))
            print(f"✗ {module_name}: {e}")
    
    # Print summary
    print(f"\n=== COMPILATION TEST RESULTS ===")
    print(f"Successful imports: {len(successful_imports)}")
    print(f"Failed imports: {len(failed_imports)}")
    
    if failed_imports:
        print(f"\nFAILED MODULES:")
        for module, error, tb in failed_imports:
            print(f"  {module}: {error}")
            print(f"    Traceback: {tb}")
    
    # Assert that all imports succeeded
    assert len(failed_imports) == 0, f"Failed to import {len(failed_imports)} modules: {[m[0] for m in failed_imports]}"
    
    print(f"\n🎉 All {len(successful_imports)} modules compiled successfully!")


@pytest.mark.asyncio
async def test_basic_app_factory_instantiation():
    """Test that the app factory can be instantiated and basic methods work."""
    from managers.app_factory.app_factory import app_factory
    
    # Test that we can get managers without errors
    config_manager = app_factory.get_config_manager()
    assert config_manager is not None, "Config manager should not be None"
    
    llm_manager = app_factory.get_llm_manager()
    assert llm_manager is not None, "LLM manager should not be None"
    
    session_manager = app_factory.get_session_manager()
    assert session_manager is not None, "Session manager should not be None"
    
    service_coordinator = await app_factory.get_service_coordinator()
    assert service_coordinator is not None, "Service coordinator should not be None"
    
    print("✓ App factory instantiation and basic methods work")


if __name__ == "__main__":
    print("Running basic compilation tests for backend...")
    
    try:
        test_all_imports_compile()
        test_basic_app_factory_instantiation()
        print("\n🎉 All tests passed! Backend code compiles successfully.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        traceback.print_exc()
        sys.exit(1)