"""MCP client for connecting to MCP servers."""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
import subprocess
import os

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for connecting to MCP servers."""
    
    def __init__(self, config_path: str = "mcp.json"):
        self.config_path = config_path
        self.servers = {}
        self.processes = {}
        self.load_config()
        
    def load_config(self):
        """Load MCP server configuration."""
        config_paths = [
            self.config_path,          # Default: mcp.json
            f"../{self.config_path}",  # Parent directory
            os.path.join(os.path.dirname(__file__), "..", self.config_path)  # Relative to script
        ]
        
        for config_path in config_paths:
            try:
                if os.path.exists(config_path):
                    logger.info(f"Found MCP config at: {os.path.abspath(config_path)}")
                    with open(config_path, 'r') as f:
                        self.servers = json.load(f)
                        if isinstance(self.servers, dict):
                            logger.info(f"Loaded MCP config with {len(self.servers)} servers: {list(self.servers.keys())}")
                            return
                        else:
                            logger.error(f"Invalid JSON format in {config_path}: expected dict, got {type(self.servers)}")
                            self.servers = {}
                            return
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error in {config_path}: {e}")
                self.servers = {}
                return
            except Exception as e:
                logger.error(f"Error reading {config_path}: {e}")
                continue
        
        logger.warning(f"MCP config file not found in any of these locations: {config_paths}")
        logger.info("Create mcp.json with your MCP server configurations to enable tool support")
        self.servers = {}
    
    async def start_server(self, server_name: str) -> bool:
        """Start an MCP server process."""
        if server_name not in self.servers:
            logger.error(f"Server {server_name} not found in config")
            return False
            
        if server_name in self.processes:
            logger.info(f"Server {server_name} already running")
            return True
            
        server_config = self.servers[server_name]
        try:
            # Start the MCP server process
            cmd = server_config.get("command", [])
            cwd = server_config.get("cwd", ".")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.processes[server_name] = process
            logger.info(f"Started MCP server: {server_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting MCP server {server_name}: {e}")
            return False
    
    async def stop_server(self, server_name: str):
        """Stop an MCP server process."""
        if server_name in self.processes:
            process = self.processes[server_name]
            process.terminate()
            await process.wait()
            del self.processes[server_name]
            logger.info(f"Stopped MCP server: {server_name}")
    
    async def send_request(self, server_name: str, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send a request to an MCP server."""
        if server_name not in self.processes:
            logger.error(f"Server {server_name} not running")
            return None
            
        try:
            process = self.processes[server_name]
            request_json = json.dumps(request) + '\n'
            
            process.stdin.write(request_json.encode())
            await process.stdin.drain()
            
            # Read response
            response_line = await process.stdout.readline()
            if response_line:
                response = json.loads(response_line.decode().strip())
                return response
            else:
                logger.error(f"No response from server {server_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error communicating with server {server_name}: {e}")
            return None
    
    def get_server_groups(self, server_name: str) -> List[str]:
        """Get required groups for a server."""
        if server_name in self.servers:
            return self.servers[server_name].get("groups", [])
        return []
    
    def is_server_exclusive(self, server_name: str) -> bool:
        """Check if server is exclusive (cannot run with others)."""
        if server_name in self.servers:
            return self.servers[server_name].get("is_exclusive", False)
        return False
    
    def get_available_servers(self) -> List[str]:
        """Get list of configured servers."""
        return list(self.servers.keys())
    
    async def cleanup(self):
        """Stop all running servers."""
        for server_name in list(self.processes.keys()):
            await self.stop_server(server_name)