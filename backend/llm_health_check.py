"""
LLM Health Check Module

Provides simple health check functionality for LLM services by:
- Sending minimal prompts to get 1-token responses
- Running periodic health checks on a configurable schedule
- Logging health status and maintaining current state
- Exposing health status via API
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass

from utils import call_llm
from config import config_manager

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Result of an LLM health check."""
    model_name: str
    is_healthy: bool
    response_time_ms: Optional[float]
    last_check: datetime
    error_message: Optional[str] = None


class LLMHealthChecker:
    """Manages LLM health checks across all configured models."""
    
    def __init__(self):
        self.health_status: Dict[str, HealthCheckResult] = {}
        self._check_task: Optional[asyncio.Task] = None
        self._is_running = False
        
    async def check_model_health(self, model_name: str) -> HealthCheckResult:
        """
        Perform a health check on a single model.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            HealthCheckResult with the check outcome
        """
        start_time = datetime.now()
        
        try:
            # Use a minimal prompt that should generate a single token
            messages = [{"role": "user", "content": "Hi"}]
            
            # Call LLM and measure response time
            response = await call_llm(model_name, messages)
            
            end_time = datetime.now()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Check if we got a valid response
            is_healthy = bool(response and response.strip())
            
            result = HealthCheckResult(
                model_name=model_name,
                is_healthy=is_healthy,
                response_time_ms=response_time_ms,
                last_check=end_time,
                error_message=None if is_healthy else "Empty or invalid response"
            )
            
            logger.info(
                f"Health check for model '{model_name}': "
                f"{'âœ HEALTHY' if is_healthy else 'âœ UNHEALTHY'} "
                f"({response_time_ms:.1f}ms)"
            )
            
            return result
            
        except Exception as e:
            end_time = datetime.now()
            response_time_ms = (end_time - start_time).total_seconds() * 1000
            
            result = HealthCheckResult(
                model_name=model_name,
                is_healthy=False,
                response_time_ms=response_time_ms,
                last_check=end_time,
                error_message=str(e)
            )
            
            logger.error(
                f"Health check for model '{model_name}': âœ FAILED "
                f"({response_time_ms:.1f}ms) - {e}"
            )
            
            return result
    
    async def check_all_models(self) -> Dict[str, HealthCheckResult]:
        """
        Check health of all configured models.
        
        Returns:
            Dictionary mapping model names to their health check results
        """
        llm_config = config_manager.llm_config
        models = list(llm_config.models.keys())
        
        if not models:
            logger.warning("No models configured for health checks")
            return {}
        
        logger.info(f"Running health checks for {len(models)} models: {models}")
        
        # Run health checks for all models concurrently
        tasks = [self.check_model_health(model_name) for model_name in models]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and update status
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Health check task failed: {result}")
                continue
            
            self.health_status[result.model_name] = result
        
        healthy_count = sum(1 for r in self.health_status.values() if r.is_healthy)
        total_count = len(self.health_status)
        
        logger.info(f"Health check completed: {healthy_count}/{total_count} models healthy")
        
        return self.health_status.copy()
    
    async def start_periodic_checks(self) -> None:
        """Start the periodic health check task."""
        if self._is_running:
            logger.warning("Health checker is already running")
            return
        
        app_settings = config_manager.app_settings
        interval_minutes = app_settings.llm_health_check_interval
        
        if interval_minutes <= 0:
            logger.info("LLM health checks disabled (interval <= 0)")
            return
        
        logger.info(f"Starting LLM health checks every {interval_minutes} minutes")
        self._is_running = True
        
        # Run initial health check
        await self.check_all_models()
        
        # Start periodic checks
        self._check_task = asyncio.create_task(self._periodic_check_loop(interval_minutes))
    
    async def stop_periodic_checks(self) -> None:
        """Stop the periodic health check task."""
        if not self._is_running:
            return
        
        logger.info("Stopping LLM health checks")
        self._is_running = False
        
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
            self._check_task = None
    
    async def _periodic_check_loop(self, interval_minutes: int) -> None:
        """Internal loop for periodic health checks."""
        interval_seconds = interval_minutes * 60
        
        try:
            while self._is_running:
                await asyncio.sleep(interval_seconds)
                
                if self._is_running:  # Check again in case we were stopped during sleep
                    await self.check_all_models()
                    
        except asyncio.CancelledError:
            logger.info("Periodic health check loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Error in periodic health check loop: {e}", exc_info=True)
            self._is_running = False
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get the current health status of all models.
        
        Returns:
            Dictionary with health status information suitable for API responses
        """
        if not self.health_status:
            return {
                "status": "no_checks_run",
                "models": {},
                "overall_healthy": False,
                "healthy_count": 0,
                "total_count": 0,
                "last_check": None
            }
        
        models_status = {}
        healthy_count = 0
        latest_check = None
        
        for model_name, result in self.health_status.items():
            models_status[model_name] = {
                "healthy": result.is_healthy,
                "response_time_ms": result.response_time_ms,
                "last_check": result.last_check.isoformat(),
                "error": result.error_message
            }
            
            if result.is_healthy:
                healthy_count += 1
            
            if latest_check is None or result.last_check > latest_check:
                latest_check = result.last_check
        
        total_count = len(self.health_status)
        overall_healthy = healthy_count > 0  # At least one model is healthy
        
        return {
            "status": "healthy" if overall_healthy else "unhealthy",
            "models": models_status,
            "overall_healthy": overall_healthy,
            "healthy_count": healthy_count,
            "total_count": total_count,
            "last_check": latest_check.isoformat() if latest_check else None
        }


# Global health checker instance
health_checker = LLMHealthChecker()


async def get_llm_health_status() -> Dict[str, Any]:
    """Convenience function to get current LLM health status."""
    return health_checker.get_health_status()


async def run_health_check() -> Dict[str, HealthCheckResult]:
    """Convenience function to run an immediate health check."""
    return await health_checker.check_all_models()
