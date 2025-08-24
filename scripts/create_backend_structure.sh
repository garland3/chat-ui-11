#!/bin/bash

echo "Creating new backend structure based on refactor plan..."
echo "======================================================"

# Create main backend directory
mkdir -p backend

# Create main.py (FastAPI app entry point - keep existing)
echo "Creating main.py (FastAPI app entry point)..."
touch backend/main.py

# Create managers directory structure
echo "Creating managers directory structure..."
mkdir -p backend/managers

# Single file managers
touch backend/managers/__init__.py
touch backend/managers/service_coordinator.py
touch backend/managers/ui_callback_handler.py
touch backend/managers/logger_coordinator.py

# Auth management module
echo "Creating auth management module..."
mkdir -p backend/managers/auth
touch backend/managers/auth/__init__.py
touch backend/managers/auth/auth_manager.py
touch backend/managers/auth/permission_checker.py
touch backend/managers/auth/token_handler.py
touch backend/managers/auth/capability_tokens.py
touch backend/managers/auth/auth_models.py

# Session management module (pure state management)
echo "Creating session management module..."
mkdir -p backend/managers/session
touch backend/managers/session/__init__.py
touch backend/managers/session/session_manager.py
touch backend/managers/session/conversation_history.py
touch backend/managers/session/context_handler.py
touch backend/managers/session/session_models.py

# MCP server management module
echo "Creating MCP management module..."
mkdir -p backend/managers/mcp
touch backend/managers/mcp/__init__.py
touch backend/managers/mcp/mcp_manager.py
touch backend/managers/mcp/server_registry.py
touch backend/managers/mcp/tool_registry.py
touch backend/managers/mcp/prompt_registry.py
touch backend/managers/mcp/mcp_models.py

# Storage management module
echo "Creating storage management module..."
mkdir -p backend/managers/storage
touch backend/managers/storage/__init__.py
touch backend/managers/storage/storage_manager.py
touch backend/managers/storage/s3_storage.py
touch backend/managers/storage/filesystem_storage.py
touch backend/managers/storage/storage_interfaces.py
touch backend/managers/storage/storage_models.py

# Agent execution module
echo "Creating agent management module..."
mkdir -p backend/managers/agent
touch backend/managers/agent/__init__.py
touch backend/managers/agent/agent_manager.py
touch backend/managers/agent/strategy_handler.py
touch backend/managers/agent/event_emitter.py
touch backend/managers/agent/agent_models.py

# Tool execution module
echo "Creating tool management module..."
mkdir -p backend/managers/tools
touch backend/managers/tools/__init__.py
touch backend/managers/tools/tool_caller.py
touch backend/managers/tools/context_injector.py
touch backend/managers/tools/artifact_processor.py
touch backend/managers/tools/tool_execution.py
touch backend/managers/tools/tool_models.py

# RAG operations module
echo "Creating RAG management module..."
mkdir -p backend/managers/rag
touch backend/managers/rag/__init__.py
touch backend/managers/rag/rag_manager.py
touch backend/managers/rag/mcp_rag_client.py
touch backend/managers/rag/http_rag_client.py
touch backend/managers/rag/rag_models.py

# Admin operations module
echo "Creating admin management module..."
mkdir -p backend/managers/admin
touch backend/managers/admin/__init__.py
touch backend/managers/admin/admin_manager.py
touch backend/managers/admin/config_handler.py
touch backend/managers/admin/monitoring.py
touch backend/managers/admin/log_manager.py
touch backend/managers/admin/feedback_handler.py
touch backend/managers/admin/admin_models.py

# Middleware directory
echo "Creating middleware directory..."
mkdir -p backend/middleware
touch backend/middleware/__init__.py
touch backend/middleware/auth_middleware.py
touch backend/middleware/rate_limit_middleware.py
touch backend/middleware/logging_middleware.py
touch backend/middleware/security_headers.py

# Routes directory (keep existing structure)
echo "Creating routes directory..."
mkdir -p backend/routes
touch backend/routes/__init__.py
touch backend/routes/config_routes.py
touch backend/routes/admin_routes.py
touch backend/routes/files_routes.py
touch backend/routes/feedback_routes.py
touch backend/routes/health_routes.py

# Core directory (keep essential infrastructure)
echo "Creating core directory..."
mkdir -p backend/core
touch backend/core/__init__.py
touch backend/core/otel_config.py
touch backend/core/middleware.py
touch backend/core/auth.py
touch backend/core/auth_utils.py
touch backend/core/rate_limit.py
touch backend/core/rate_limit_middleware.py
touch backend/core/security_headers_middleware.py
touch backend/core/utils.py

# Domain directory (keep existing models)
echo "Creating domain directory..."
mkdir -p backend/domain
touch backend/domain/__init__.py
touch backend/domain/errors.py
touch backend/domain/rag_mcp_service.py

mkdir -p backend/domain/messages
touch backend/domain/messages/__init__.py
touch backend/domain/messages/models.py

mkdir -p backend/domain/sessions
touch backend/domain/sessions/__init__.py
touch backend/domain/sessions/models.py

# Infrastructure directory (keep app factory and transport)
echo "Creating infrastructure directory..."
mkdir -p backend/infrastructure
touch backend/infrastructure/__init__.py
touch backend/infrastructure/app_factory.py

mkdir -p backend/infrastructure/transport
touch backend/infrastructure/transport/__init__.py
touch backend/infrastructure/transport/websocket_connection_adapter.py

# Interfaces directory (keep existing interfaces)
echo "Creating interfaces directory..."
mkdir -p backend/interfaces
touch backend/interfaces/__init__.py
touch backend/interfaces/llm.py
touch backend/interfaces/tools.py
touch backend/interfaces/transport.py

# Modules directory (keep existing modules for gradual migration)
echo "Creating modules directory..."
mkdir -p backend/modules
touch backend/modules/__init__.py

mkdir -p backend/modules/config
touch backend/modules/config/__init__.py
touch backend/modules/config/manager.py
touch backend/modules/config/cli.py

mkdir -p backend/modules/llm
touch backend/modules/llm/__init__.py
touch backend/modules/llm/caller.py
touch backend/modules/llm/litellm_caller.py
touch backend/modules/llm/models.py
touch backend/modules/llm/cli.py

mkdir -p backend/modules/file_storage
touch backend/modules/file_storage/__init__.py
touch backend/modules/file_storage/manager.py
touch backend/modules/file_storage/s3_client.py

mkdir -p backend/modules/mcp_tools
touch backend/modules/mcp_tools/__init__.py
touch backend/modules/mcp_tools/client.py

mkdir -p backend/modules/prompts
touch backend/modules/prompts/prompt_provider.py

mkdir -p backend/modules/rag
touch backend/modules/rag/__init__.py
touch backend/modules/rag/client.py

# Tests directory (placeholder for new tests)
echo "Creating tests directory..."
mkdir -p backend/tests
touch backend/tests/__init__.py
touch backend/tests/conftest.py

echo ""
echo "Backend structure created successfully!"
echo "======================================"
echo ""
echo "Key files created:"
echo "- backend/main.py (FastAPI entry point)"
echo "- backend/managers/ (new manager-based architecture)"
echo "- backend/infrastructure/app_factory.py (dependency injection hub)"
echo "- backend/core/otel_config.py (OpenTelemetry logging foundation)"
echo "- backend/domain/ (existing domain models)"
echo ""
echo "Next steps:"
echo "1. Copy and adapt main.py from old.backend/"
echo "2. Copy and adapt app_factory.py from old.backend/infrastructure/"  
echo "3. Copy essential files from old.backend/core/"
echo "4. Copy domain models from old.backend/domain/"
echo "5. Begin implementing managers according to refactor plan"
echo ""
echo "Remember: Follow the development philosophy from refactor_plan.md:"
echo "- Focus on happy path and readability"
echo "- Security-first approach for user input"
echo "- Pure state management for sessions"
echo "- Descriptive file names always"
