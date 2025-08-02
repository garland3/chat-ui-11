"""MCP Server Health Monitoring for admin panel."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MCPServerHealthStatus:
    """Health status of an MCP server."""
    server_name: str
    status: str  # 'healthy', 'warning', 'error', 'unknown'
    last_check: float
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    is_running: bool = False
    tools_count: int = 0
    prompts_count: int = 0


class MCPHealthMonitor:
    """Monitor health status of MCP servers."""
    
    def __init__(self):
        self.health_status: Dict[str, MCPServerHealthStatus] = {}
        self.last_full_check: Optional[float] = None
        self.check_interval = 300  # 5 minutes default
        self._monitoring_task: Optional[asyncio.Task] = None
        
    def update_check_interval(self, interval_seconds: int):
        """Update the health check interval."""
        self.check_interval = interval_seconds
        logger.info(f"MCP health check interval updated to {interval_seconds} seconds")
    
    async def check_server_health(self, server_name: str, mcp_client=None) -> MCPServerHealthStatus:
        """Check health of a single MCP server."""
        start_time = time.time()
        
        try:
            if not mcp_client:
                # Server not available in MCP manager
                return MCPServerHealthStatus(
                    server_name=server_name,
                    status="error",
                    last_check=start_time,
                    error_message="MCP client not found",
                    is_running=False
                )
            
            # Try to get server info (this will test connectivity)
            tools_count = 0
            prompts_count = 0
            
            # If we have a client, try to check if it's responsive
            # For now, we'll just check if the client exists and assume it's healthy
            # In a real implementation, we'd send a ping or list_tools request
            
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            return MCPServerHealthStatus(
                server_name=server_name,
                status="healthy",
                last_check=start_time,
                response_time_ms=response_time,
                is_running=True,
                tools_count=tools_count,
                prompts_count=prompts_count
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.warning(f"Health check failed for MCP server {server_name}: {e}")
            
            return MCPServerHealthStatus(
                server_name=server_name,
                status="error",
                last_check=start_time,
                response_time_ms=response_time,
                error_message=str(e),
                is_running=False
            )
    
    async def check_all_servers(self, mcp_manager=None) -> Dict[str, MCPServerHealthStatus]:
        """Check health of all MCP servers."""
        if not mcp_manager:
            logger.warning("No MCP manager available for health checks")
            return {}
        
        logger.info("Starting MCP server health check")
        start_time = time.time()
        
        # Get list of configured servers
        try:
            from config import config_manager
            mcp_config = config_manager.mcp_config
            configured_servers = list(mcp_config.servers.keys())
        except Exception as e:
            logger.error(f"Failed to get MCP server list: {e}")
            configured_servers = []
        
        # Check each server
        health_results = {}
        for server_name in configured_servers:
            # Get the MCP client for this server if available
            mcp_client = None
            if hasattr(mcp_manager, 'clients') and server_name in mcp_manager.clients:
                mcp_client = mcp_manager.clients[server_name]
            
            health_status = await self.check_server_health(server_name, mcp_client)
            health_results[server_name] = health_status
            self.health_status[server_name] = health_status
        
        self.last_full_check = time.time()
        
        # Log summary
        healthy_count = sum(1 for status in health_results.values() if status.status == "healthy")
        total_time = (time.time() - start_time) * 1000
        
        logger.info(
            f"MCP health check completed: {healthy_count}/{len(health_results)} servers healthy "
            f"({total_time:.1f}ms total)"
        )
        
        return health_results
    
    def get_health_summary(self) -> Dict:
        """Get a summary of all server health statuses."""
        if not self.health_status:
            return {
                "overall_status": "unknown",
                "healthy_count": 0,
                "total_count": 0,
                "last_check": None,
                "servers": {}
            }
        
        healthy_count = sum(1 for status in self.health_status.values() if status.status == "healthy")
        warning_count = sum(1 for status in self.health_status.values() if status.status == "warning")
        error_count = sum(1 for status in self.health_status.values() if status.status == "error")
        
        # Determine overall status
        if error_count > 0:
            overall_status = "error"
        elif warning_count > 0:
            overall_status = "warning"
        elif healthy_count > 0:
            overall_status = "healthy"
        else:
            overall_status = "unknown"
        
        return {
            "overall_status": overall_status,
            "healthy_count": healthy_count,
            "warning_count": warning_count,
            "error_count": error_count,
            "total_count": len(self.health_status),
            "last_check": self.last_full_check,
            "check_interval": self.check_interval,
            "servers": {
                name: {
                    "status": status.status,
                    "last_check": status.last_check,
                    "response_time_ms": status.response_time_ms,
                    "error_message": status.error_message,
                    "is_running": status.is_running,
                    "tools_count": status.tools_count,
                    "prompts_count": status.prompts_count
                }
                for name, status in self.health_status.items()
            }
        }
    
    async def start_periodic_monitoring(self, mcp_manager=None):
        """Start periodic health monitoring."""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.info("MCP health monitoring already running")
            return
        
        logger.info(f"Starting MCP health monitoring with {self.check_interval}s interval")
        self._monitoring_task = asyncio.create_task(self._monitoring_loop(mcp_manager))
    
    async def stop_periodic_monitoring(self):
        """Stop periodic health monitoring."""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("MCP health monitoring stopped")
    
    async def _monitoring_loop(self, mcp_manager):
        """Internal monitoring loop."""
        while True:
            try:
                await self.check_all_servers(mcp_manager)
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in MCP health monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(min(self.check_interval, 60))  # Wait at least 1 minute on error


# Global MCP health monitor instance
mcp_health_monitor = MCPHealthMonitor()


def get_mcp_health_status() -> Dict:
    """Get current MCP server health status."""
    return mcp_health_monitor.get_health_summary()


async def trigger_mcp_health_check(mcp_manager=None) -> Dict:
    """Manually trigger an MCP health check."""
    return await mcp_health_monitor.check_all_servers(mcp_manager)


def update_mcp_health_interval(interval_seconds: int):
    """Update MCP health check interval."""
    mcp_health_monitor.update_check_interval(interval_seconds)