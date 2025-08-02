# Better Logging System

This document describes the comprehensive logging system implemented for chat-ui-11.

## Features

### 1. Environment-Based Configuration
- Log level can be set in `.env` file using `LOG_LEVEL` (DEBUG, INFO, WARNING, ERROR)
- Default log level is INFO if not specified
- All components respect the configured log level

### 2. Multiple Log Destinations
- **Console Output**: Real-time logging to stdout with simple formatting
- **Application Logs**: Rotating file handler at `logs/app.log` (10MB files, 5 backups)
- **Error Logs**: Dedicated file for errors at `logs/errors.log`
- **Database Logs**: Persistent logging to SQLite database at `logs/app_logs.db`

### 3. Enhanced Error Handling
- All errors are automatically logged with full tracebacks
- Contextual information (user_email, session_id) is preserved
- Database handler ensures errors are persistent and queryable

### 4. LLM Call Tracking
- Complete logging of all LLM API calls to SQLite database at `logs/llm_calls.db`
- Tracks:
  - Full input messages and output responses
  - Processing time and token counts (estimated)
  - Selected tools and tool calls
  - Error messages for failed calls
  - User and session context
  - API endpoints used

### 5. Admin Access
- RESTful API endpoints for log management
- Database querying capabilities for admins
- Usage statistics and analytics
- Log file downloading

## Configuration

Add to your `.env` file:
```
LOG_LEVEL=INFO
```

Valid levels: DEBUG, INFO, WARNING, ERROR

## Database Schema

### Application Logs (`app_logs.db`)
```sql
CREATE TABLE app_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    level TEXT NOT NULL,
    logger_name TEXT NOT NULL,
    message TEXT NOT NULL,
    module TEXT,
    function TEXT,
    line_number INTEGER,
    traceback TEXT,
    user_email TEXT,
    session_id TEXT
);
```

### LLM Call Logs (`llm_calls.db`)
```sql
CREATE TABLE llm_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    user_email TEXT NOT NULL,
    session_id TEXT,
    model_name TEXT NOT NULL,
    input_messages TEXT NOT NULL,
    output_response TEXT NOT NULL,
    tool_calls TEXT,
    selected_tools TEXT,
    processing_time_ms INTEGER,
    token_count_input INTEGER,
    token_count_output INTEGER,
    error_message TEXT,
    api_endpoint TEXT
);
```

## Admin API Endpoints

### Log Management
- `GET /admin/logs` - Get application logs with filtering
  - Query params: `limit`, `level`, `search`
- `GET /admin/logs/file/{filename}` - Download log files
- `GET /admin/llm-calls` - Get LLM call logs with filtering
  - Query params: `limit`, `user_email`, `model_name`, `has_error`
- `GET /admin/llm-calls/{call_id}` - Get detailed LLM call information
- `GET /admin/llm-stats` - Get LLM usage statistics
  - Query params: `days` (default: 7)

### Example Usage
```bash
# Get recent application logs
curl "http://localhost:8000/admin/logs?limit=50&level=ERROR"

# Get LLM calls for a specific user
curl "http://localhost:8000/admin/llm-calls?user_email=user@example.com&limit=20"

# Get LLM usage statistics for last 30 days
curl "http://localhost:8000/admin/llm-stats?days=30"

# Download application log file
curl "http://localhost:8000/admin/logs/file/app.log" -o app.log
```

## Usage in Code

### Basic Logging
```python
import logging

logger = logging.getLogger(__name__)
logger.info("This is an info message")
logger.error("This is an error", exc_info=True)  # Includes traceback
```

### Contextual Logging
```python
from logging_config import log_with_context

log_with_context(
    logger, 
    logging.INFO, 
    "User action performed", 
    user_email="user@example.com",
    session_id="session-123"
)
```

### LLM Call Logging
LLM calls are automatically logged by the enhanced `call_llm` and `call_llm_with_tools` functions. No additional code required.

## File Structure
```
logs/
├── app.log          # Main application log (rotating)
├── app.log.1        # Previous log files (automatic rotation)
├── errors.log       # Error-only log file
├── app_logs.db      # Application logs database
└── llm_calls.db     # LLM call logs database
```

## Benefits

1. **Comprehensive Tracking**: Every LLM call and error is logged for debugging and analytics
2. **Admin Visibility**: Complete system observability through admin APIs
3. **Performance Monitoring**: Track LLM response times and token usage
4. **Error Analysis**: Full tracebacks with context for all errors
5. **User Activity**: Track user interactions and system usage patterns
6. **Compliance**: Detailed audit trail for all system operations

## Security Considerations

- Admin endpoints require admin group membership
- Log file access is restricted to logs directory only
- Sensitive information in LLM calls is logged (consider this for privacy)
- Database files should be included in backup procedures