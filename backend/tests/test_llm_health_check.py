"""
Tests for LLM Health Check functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from llm_health_check import LLMHealthChecker, HealthCheckResult, health_checker


class TestLLMHealthChecker:
    """Test the LLMHealthChecker class."""
    
    def test_health_check_result_creation(self):
        """Test HealthCheckResult creation."""
        result = HealthCheckResult(
            model_name="test-model",
            is_healthy=True,
            response_time_ms=150.5,
            last_check=datetime.now()
        )
        
        assert result.model_name == "test-model"
        assert result.is_healthy is True
        assert result.response_time_ms == 150.5
        assert result.error_message is None
    
    @pytest.mark.asyncio
    async def test_check_model_health_success(self):
        """Test successful model health check."""
        checker = LLMHealthChecker()
        
        with patch('llm_health_check.call_llm') as mock_call_llm:
            mock_call_llm.return_value = "Hello"
            
            result = await checker.check_model_health("test-model")
            
            assert result.model_name == "test-model"
            assert result.is_healthy is True
            assert result.response_time_ms is not None
            assert result.response_time_ms > 0
            assert result.error_message is None
            
            # Verify the LLM was called with correct parameters
            mock_call_llm.assert_called_once_with(
                "test-model",
                [{"role": "user", "content": "Hi"}]
            )
    
    @pytest.mark.asyncio
    async def test_check_model_health_failure(self):
        """Test model health check failure."""
        checker = LLMHealthChecker()
        
        with patch('llm_health_check.call_llm') as mock_call_llm:
            mock_call_llm.side_effect = Exception("Connection failed")
            
            result = await checker.check_model_health("test-model")
            
            assert result.model_name == "test-model"
            assert result.is_healthy is False
            assert result.response_time_ms is not None
            assert result.error_message == "Connection failed"
    
    @pytest.mark.asyncio
    async def test_check_model_health_empty_response(self):
        """Test model health check with empty response."""
        checker = LLMHealthChecker()
        
        with patch('llm_health_check.call_llm') as mock_call_llm:
            mock_call_llm.return_value = ""
            
            result = await checker.check_model_health("test-model")
            
            assert result.model_name == "test-model"
            assert result.is_healthy is False
            assert result.error_message == "Empty or invalid response"
    
    @pytest.mark.asyncio
    async def test_check_all_models(self):
        """Test checking all configured models."""
        checker = LLMHealthChecker()
        
        # Mock config with two models
        mock_config = MagicMock()
        mock_config.models = {
            "model1": MagicMock(),
            "model2": MagicMock()
        }
        
        with patch('llm_health_check.config_manager') as mock_config_manager:
            mock_config_manager.llm_config = mock_config
            
            with patch.object(checker, 'check_model_health') as mock_check:
                # Mock health check results
                mock_check.side_effect = [
                    HealthCheckResult("model1", True, 100, datetime.now()),
                    HealthCheckResult("model2", False, 200, datetime.now(), "Error")
                ]
                
                results = await checker.check_all_models()
                
                assert len(results) == 2
                assert "model1" in results
                assert "model2" in results
                assert results["model1"].is_healthy is True
                assert results["model2"].is_healthy is False
    
    @pytest.mark.asyncio
    async def test_check_all_models_no_models(self):
        """Test checking when no models are configured."""
        checker = LLMHealthChecker()
        
        # Mock config with no models
        mock_config = MagicMock()
        mock_config.models = {}
        
        with patch('llm_health_check.config_manager') as mock_config_manager:
            mock_config_manager.llm_config = mock_config
            
            results = await checker.check_all_models()
            
            assert results == {}
    
    def test_get_health_status_no_checks(self):
        """Test getting health status when no checks have been run."""
        checker = LLMHealthChecker()
        
        status = checker.get_health_status()
        
        assert status["status"] == "no_checks_run"
        assert status["models"] == {}
        assert status["overall_healthy"] is False
        assert status["healthy_count"] == 0
        assert status["total_count"] == 0
        assert status["last_check"] is None
    
    def test_get_health_status_with_results(self):
        """Test getting health status with check results."""
        checker = LLMHealthChecker()
        
        # Add some mock results
        now = datetime.now()
        checker.health_status = {
            "model1": HealthCheckResult("model1", True, 100, now),
            "model2": HealthCheckResult("model2", False, 200, now, "Error")
        }
        
        status = checker.get_health_status()
        
        assert status["status"] == "healthy"  # At least one model is healthy
        assert status["overall_healthy"] is True
        assert status["healthy_count"] == 1
        assert status["total_count"] == 2
        assert len(status["models"]) == 2
        assert status["models"]["model1"]["healthy"] is True
        assert status["models"]["model2"]["healthy"] is False
        assert status["models"]["model2"]["error"] == "Error"
    
    @pytest.mark.asyncio
    async def test_start_stop_periodic_checks(self):
        """Test starting and stopping periodic checks."""
        checker = LLMHealthChecker()
        
        # Mock config
        mock_settings = MagicMock()
        mock_settings.llm_health_check_interval = 1  # 1 minute for testing
        
        with patch('llm_health_check.config_manager') as mock_config_manager:
            mock_config_manager.app_settings = mock_settings
            
            with patch.object(checker, 'check_all_models') as mock_check:
                mock_check.return_value = {}
                
                # Start periodic checks
                await checker.start_periodic_checks()
                assert checker._is_running is True
                assert checker._check_task is not None
                
                # Stop periodic checks
                await checker.stop_periodic_checks()
                assert checker._is_running is False
                assert checker._check_task is None
    
    @pytest.mark.asyncio
    async def test_start_periodic_checks_disabled(self):
        """Test that periodic checks don't start when interval is 0."""
        checker = LLMHealthChecker()
        
        # Mock config with disabled interval
        mock_settings = MagicMock()
        mock_settings.llm_health_check_interval = 0
        
        with patch('llm_health_check.config_manager') as mock_config_manager:
            mock_config_manager.app_settings = mock_settings
            
            await checker.start_periodic_checks()
            assert checker._is_running is False
            assert checker._check_task is None


class TestHealthCheckModule:
    """Test module-level functions."""
    
    @pytest.mark.asyncio
    async def test_get_llm_health_status(self):
        """Test the convenience function for getting health status."""
        from llm_health_check import get_llm_health_status
        
        with patch.object(health_checker, 'get_health_status') as mock_get_status:
            mock_get_status.return_value = {"status": "healthy"}
            
            result = await get_llm_health_status()
            
            assert result == {"status": "healthy"}
            mock_get_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_health_check(self):
        """Test the convenience function for running health checks."""
        from llm_health_check import run_health_check
        
        with patch.object(health_checker, 'check_all_models') as mock_check:
            mock_results = {"model1": HealthCheckResult("model1", True, 100, datetime.now())}
            mock_check.return_value = mock_results
            
            result = await run_health_check()
            
            assert result == mock_results
            mock_check.assert_called_once()