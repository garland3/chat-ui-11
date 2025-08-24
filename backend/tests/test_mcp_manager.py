import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from managers.mcp.mcp_manager import MCPManager
from common.models.mcp_models import MCPServer, MCPTool, MCPServerConfig
from managers.mcp.server_registry import ServerRegistry
from managers.mcp.tool_registry import ToolRegistry

# Mocking necessary components
@pytest.fixture
def mock_config_manager():
    mock_cm = MagicMock(spec=ConfigManager)
    mock_cm.get_mcp_config.return_value.servers = {
        "test_server_1": MagicMock(
            name="test_server_1",
            config=MagicMock(
                transport="stdio",
                command="echo",
                args=["hello"],
                cwd="/tmp",
                env={"TEST_ENV": "1"},
                groups=["admin"],
                description="A test server",
                short_description="Test server",
                author="Test Author",
                help_email="test@example.com",
                enabled=True,
                url=None
            )
        ),
        "test_server_2": MagicMock(
            name="test_server_2",
            config=MagicMock(
                transport="http",
                url="http://localhost:8000",
                groups=["user"],
                description="Another test server",
                short_description="Another test server",
                author="Another Test Author",
                help_email="another@example.com",
                enabled=True,
                command=None,
                args=None,
                cwd=None,
                env=None
            )
        )
    }
    return mock_cm

@pytest.fixture
def mock_fastmcp_client():
    mock_client = AsyncMock(spec=Client)
    
    # Mock the 'get' method for the meta object
    mock_meta_get = MagicMock()
    # Configure the return value for the 'get' method when called with 'tags'
    mock_meta_get.side_effect = lambda key, default: set() if key == 'tags' else default

    # Create mock tools with proper attributes
    mock_tool1 = MagicMock()
    mock_tool1.name = "tool1"
    mock_tool1.inputSchema = {}
    mock_tool1.meta = MagicMock(get=mock_meta_get)
    
    mock_tool2 = MagicMock()
    mock_tool2.name = "tool2"
    mock_tool2.inputSchema = {}
    mock_tool2.meta = MagicMock(get=mock_meta_get)
    
    mock_client.list_tools.return_value = [mock_tool1, mock_tool2]
    mock_client.call_tool.return_value = {"result": "success"}
    return mock_client

@pytest.fixture
def mcp_manager(mock_config_manager):
    return MCPManager(mock_config_manager)

# Helper to mock MCPServerConfig.from_pydantic
def create_mock_mcp_server_config_objects():
    # Mock for stdio transport
    mock_config_stdio = MagicMock()
    mock_config_stdio.transport = "stdio"
    mock_config_stdio.command = "echo"
    mock_config_stdio.args = ["hello"]
    mock_config_stdio.cwd = "/tmp"
    mock_config_stdio.env = {"TEST_ENV": "1"}
    mock_config_stdio.groups = ["admin"]
    mock_config_stdio.description = "A test server"
    mock_config_stdio.short_description = "Test server"
    mock_config_stdio.author = "Test Author"
    mock_config_stdio.help_email = "test@example.com"
    mock_config_stdio.enabled = True
    mock_config_stdio.url = None

    # Mock for http transport
    mock_config_http = MagicMock()
    mock_config_http.transport = "http"
    mock_config_http.command = None
    mock_config_http.args = None
    mock_config_http.cwd = None
    mock_config_http.env = None
    mock_config_http.groups = ["user"]
    mock_config_http.description = "Another test server"
    mock_config_http.short_description = "Another test server"
    mock_config_http.author = "Another Test Author"
    mock_config_http.help_email = "another@example.com"
    mock_config_http.enabled = True
    mock_config_http.url = "http://localhost:8000"

    return mock_config_stdio, mock_config_http

# Tests
@pytest.mark.asyncio
async def test_mcp_manager_initialization(mcp_manager, mock_config_manager):
    """Test initialization of MCPManager."""
    mock_config_stdio, mock_config_http = create_mock_mcp_server_config_objects()
    
    # Mock MCPServerConfig.from_pydantic to return the correct mock object
    def mock_from_pydantic(pydantic_obj):
        if hasattr(pydantic_obj, 'transport') and pydantic_obj.transport == "stdio":
            return mock_config_stdio
        elif hasattr(pydantic_obj, 'config') and pydantic_obj.config.transport == "stdio":
            return mock_config_stdio
        else:
            return mock_config_http
    
    mock_mcp_server_config_from_pydantic = MagicMock(side_effect=mock_from_pydantic)

    with patch('common.models.mcp_models.MCPServerConfig.from_pydantic', mock_mcp_server_config_from_pydantic), \
         patch.object(mcp_manager, '_initialize_clients', new_callable=AsyncMock) as mock_init_clients, \
         patch.object(mcp_manager, '_load_server_configs', new_callable=AsyncMock) as mock_load_configs, \
         patch.object(mcp_manager, '_discover_tools', new_callable=AsyncMock) as mock_discover_tools:
        
        await mcp_manager.initialize()
        
        mock_load_configs.assert_called_once()
        mock_init_clients.assert_called_once()
        mock_discover_tools.assert_called_once()
        assert mcp_manager._initialized is True

@pytest.mark.asyncio
async def test_mcp_manager_load_server_configs(mcp_manager, mock_config_manager):
    """Test loading server configurations."""
    mock_config_stdio, mock_config_http = create_mock_mcp_server_config_objects()
    
    # Mock MCPServerConfig.from_pydantic to return the correct mock object
    def mock_from_pydantic(pydantic_obj):
        if hasattr(pydantic_obj, 'transport') and pydantic_obj.transport == "stdio":
            return mock_config_stdio
        elif hasattr(pydantic_obj, 'config') and pydantic_obj.config.transport == "stdio":
            return mock_config_stdio
        else:
            return mock_config_http
    
    mock_mcp_server_config_from_pydantic = MagicMock(side_effect=mock_from_pydantic)

    with patch('common.models.mcp_models.MCPServerConfig.from_pydantic', mock_mcp_server_config_from_pydantic):
        await mcp_manager._load_server_configs()

    assert len(mcp_manager.server_registry._servers) == 2 # Corrected attribute
    server1 = mcp_manager.server_registry.get_server("test_server_1")
    assert server1.name == "test_server_1"
    assert server1.config.transport == "stdio" # This assertion should now pass
    assert server1.config.command == "echo"
    assert server1.config.cwd == "/tmp"
    assert server1.config.groups == ["admin"]

    server2 = mcp_manager.server_registry.get_server("test_server_2")
    assert server2.name == "test_server_2"
    assert server2.config.transport == "http"
    assert server2.config.url == "http://localhost:8000"
    assert server2.config.groups == ["user"]

@pytest.mark.asyncio
async def test_mcp_manager_initialize_clients(mcp_manager, mock_config_manager, mock_fastmcp_client):
    """Test initializing clients."""
    mock_config_stdio, mock_config_http = create_mock_mcp_server_config_objects()
    
    # Mock MCPServerConfig.from_pydantic to return the correct mock object
    def mock_from_pydantic(pydantic_obj):
        if hasattr(pydantic_obj, 'transport') and pydantic_obj.transport == "stdio":
            return mock_config_stdio
        elif hasattr(pydantic_obj, 'config') and pydantic_obj.config.transport == "stdio":
            return mock_config_stdio
        else:
            return mock_config_http
    
    mock_mcp_server_config_from_pydantic = MagicMock(side_effect=mock_from_pydantic)

    # Patch the methods that _initialize_clients calls
    with patch('common.models.mcp_models.MCPServerConfig.from_pydantic', mock_mcp_server_config_from_pydantic), \
         patch.object(mcp_manager, '_create_stdio_client', return_value=mock_fastmcp_client) as mock_create_stdio, \
         patch.object(mcp_manager, '_create_http_client', return_value=mock_fastmcp_client) as mock_create_http:
        
        # Ensure server registry is populated first
        await mcp_manager._load_server_configs() # This should now work correctly

        await mcp_manager._initialize_clients()
        
        assert len(mcp_manager.clients) == 2
        assert "test_server_1" in mcp_manager.clients
        assert "test_server_2" in mcp_manager.clients
        
        mock_create_stdio.assert_called_once()
        mock_create_http.assert_called_once()

@pytest.mark.asyncio
async def test_mcp_manager_discover_tools(mcp_manager, mock_config_manager, mock_fastmcp_client):
    """Test discovering tools."""
    mcp_manager.clients["test_server_1"] = mock_fastmcp_client
    mcp_manager.clients["test_server_2"] = mock_fastmcp_client
    
    await mcp_manager._discover_tools()
    
    assert len(mcp_manager.tool_registry._tools) == 4 # Corrected attribute: 2 tools from each server
    tool1 = mcp_manager.tool_registry.get_tool_by_name("test_server_1_tool1")
    assert tool1.name == "tool1"
    assert tool1.server_name == "test_server_1"
    
    tool3 = mcp_manager.tool_registry.get_tool_by_name("test_server_2_tool1")
    assert tool3.name == "tool1"
    assert tool3.server_name == "test_server_2"

@pytest.mark.asyncio
async def test_mcp_manager_call_tool(mcp_manager, mock_config_manager, mock_fastmcp_client):
    """Test calling a tool."""
    mcp_manager.clients["test_server_1"] = mock_fastmcp_client
    
    # Add a tool to the tool registry
    tool = MCPTool(name="tool1", server_name="test_server_1", description="", input_schema={}, tags=set())
    mcp_manager.tool_registry.add_tool(tool)
    
    result = await mcp_manager.call_tool("test_server_1_tool1", {"arg1": "value1"})
    
    assert result == {"result": "success"}
    mock_fastmcp_client.call_tool.assert_called_once_with("tool1", {"arg1": "value1"})

@pytest.mark.asyncio
async def test_mcp_manager_call_tool_not_found(mcp_manager):
    """Test calling a non-existent tool."""
    with pytest.raises(ValueError, match="Tool not found: non_existent_tool"):
        await mcp_manager.call_tool("non_existent_tool", {})

@pytest.mark.asyncio
async def test_mcp_manager_call_tool_no_client(mcp_manager):
    """Test calling a tool when no client is available for the server."""
    tool = MCPTool(name="tool1", server_name="unknown_server", description="", input_schema={}, tags=set())
    mcp_manager.tool_registry.add_tool(tool)
    
    # Tool exists but no client is available for the server
    with pytest.raises(ValueError, match="No client available for server: unknown_server"):
        await mcp_manager.call_tool("unknown_server_tool1", {})

@pytest.mark.asyncio
async def test_mcp_manager_get_available_servers(mcp_manager, mock_config_manager, mock_fastmcp_client):
    """Test getting available servers."""
    mcp_manager.clients["test_server_1"] = mock_fastmcp_client
    mcp_manager.clients["test_server_2"] = mock_fastmcp_client
    
    available_servers = mcp_manager.get_available_servers()
    assert sorted(available_servers) == ["test_server_1", "test_server_2"]

@pytest.mark.asyncio
async def test_mcp_manager_get_authorized_servers(mcp_manager, mock_config_manager):
    """Test getting authorized servers."""
    # Mock server registry to have servers with group restrictions
    server1 = MCPServer(name="admin_server", config=MCPServerConfig(groups=["admin"]))
    server2 = MCPServer(name="user_server", config=MCPServerConfig(groups=["user"]))
    server3 = MCPServer(name="public_server", config=MCPServerConfig(groups=[])) # No group restriction
    
    mcp_manager.server_registry.add_server(server1)
    mcp_manager.server_registry.add_server(server2)
    mcp_manager.server_registry.add_server(server3)
    
    # Mock clients for these servers
    mock_client = AsyncMock()
    mcp_manager.clients["admin_server"] = mock_client
    mcp_manager.clients["user_server"] = mock_client
    mcp_manager.clients["public_server"] = mock_client

    authorized_admin = mcp_manager.get_authorized_servers(["admin", "user"])
    # Corrected expected list
    assert sorted(authorized_admin) == ["admin_server", "public_server", "user_server"]

    authorized_user = mcp_manager.get_authorized_servers(["user"])
    assert sorted(authorized_user) == ["public_server", "user_server"]

    authorized_none = mcp_manager.get_authorized_servers(["guest"])
    assert authorized_none == ["public_server"]

@pytest.mark.asyncio
async def test_mcp_manager_get_server_info(mcp_manager, mock_config_manager):
    """Test getting server information."""
    server_config = MagicMock(
        description="Detailed server info",
        short_description="Short info",
        author="Author Name",
        help_email="help@example.com",
        groups=["group1", "group2"],
        enabled=True,
        transport="http",
        url="http://example.com"
    )
    mcp_server = MCPServer(name="my_server", config=server_config)
    mcp_manager.server_registry.add_server(mcp_server)
    mcp_manager.clients["my_server"] = AsyncMock() # Add client to make it available

    server_info = mcp_manager.get_server_info("my_server")
    assert server_info == {
        'name': 'my_server',
        'description': 'Detailed server info',
        'short_description': 'Short info',
        'author': 'Author Name',
        'help_email': 'help@example.com',
        'groups': ['group1', 'group2'],
        'enabled': True,
        'transport': 'http'
    }

    assert mcp_manager.get_server_info("non_existent_server") is None

@pytest.mark.asyncio
async def test_mcp_manager_get_available_tools(mcp_manager, mock_config_manager, mock_fastmcp_client):
    """Test getting all available tools."""
    mcp_manager.clients["test_server_1"] = mock_fastmcp_client
    mcp_manager.clients["test_server_2"] = mock_fastmcp_client
    
    await mcp_manager._discover_tools() # Populate tool registry
    
    all_tools = mcp_manager.get_available_tools()
    assert len(all_tools) == 4
    assert all(isinstance(tool, MCPTool) for tool in all_tools)

@pytest.mark.asyncio
async def test_mcp_manager_get_tools_for_servers(mcp_manager, mock_config_manager, mock_fastmcp_client):
    """Test getting tools for specific servers."""
    mcp_manager.clients["test_server_1"] = mock_fastmcp_client
    mcp_manager.clients["test_server_2"] = mock_fastmcp_client
    
    await mcp_manager._discover_tools() # Populate tool registry
    
    tools_for_server1 = mcp_manager.get_tools_for_servers(["test_server_1"])
    assert len(tools_for_server1) == 2
    assert all(tool.server_name == "test_server_1" for tool in tools_for_server1)
    
    tools_for_server2 = mcp_manager.get_tools_for_servers(["test_server_2"])
    assert len(tools_for_server2) == 2
    assert all(tool.server_name == "test_server_2" for tool in tools_for_server2)
    
    tools_for_both = mcp_manager.get_tools_for_servers(["test_server_1", "test_server_2"])
    assert len(tools_for_both) == 4

@pytest.mark.asyncio
async def test_mcp_manager_get_tool_by_name(mcp_manager, mock_config_manager, mock_fastmcp_client):
    """Test getting a tool by its full name."""
    mcp_manager.clients["test_server_1"] = mock_fastmcp_client
    await mcp_manager._discover_tools() # Populate tool registry
    
    tool = mcp_manager.get_tool_by_name("test_server_1_tool1")
    assert tool is not None
    assert tool.name == "tool1"
    assert tool.server_name == "test_server_1"
    
    assert mcp_manager.get_tool_by_name("non_existent_server_tool1") is None
    assert mcp_manager.get_tool_by_name("test_server_1_non_existent_tool") is None

@pytest.mark.asyncio
async def test_mcp_manager_cleanup(mcp_manager):
    """Test cleanup method."""
    mock_client = AsyncMock()
    mcp_manager.clients["test_server_1"] = mock_client
    mcp_manager.clients["test_server_2"] = mock_client
    mcp_manager._initialized = True
    
    await mcp_manager.cleanup()
    
    assert not mcp_manager.clients
    assert mcp_manager._initialized is False

# Helper to mock ConfigManager and Client for tests
# This setup assumes pytest is used for running tests.
# If not, these mocks would need to be adapted.

# Mocking ConfigManager and Client for the tests
# These are defined here to be available within the test file.
class ConfigManager:
    def get_mcp_config(self):
        pass

class Client:
    def __init__(self, transport):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    async def list_tools(self):
        pass
    async def call_tool(self, tool_name, arguments):
        pass
