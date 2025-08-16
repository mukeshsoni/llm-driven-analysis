# Logging Configuration

This project includes a comprehensive logging system that provides structured logging across all application components.

## Features

- **Colored Console Output**: Different log levels are displayed in different colors for better readability
- **File Logging with Rotation**: Automatic log file rotation when files exceed 10MB
- **Multiple Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Centralized Configuration**: Single module (`logger_config.py`) for all logging setup
- **Per-Module Loggers**: Each module gets its own logger with automatic naming
- **Exception Logging**: Detailed exception tracebacks with context
- **Async Support**: Full support for async/await patterns

## Quick Start

### Basic Usage

```python
from logger_config import get_logger

# Get a logger for your module
logger = get_logger(__name__)

# Use it to log messages
logger.info("Application started")
logger.warning("This is a warning")
logger.error("An error occurred")
```

### Exception Logging

```python
from logger_config import get_logger, log_exception

logger = get_logger(__name__)

try:
    # Your code here
    risky_operation()
except Exception as e:
    log_exception(logger, e, "Failed to perform risky operation")
```

### Custom Logger Configuration

```python
from logger_config import setup_logger

# Create a custom logger with specific settings
custom_logger = setup_logger(
    name="my_custom_logger",
    level="DEBUG",  # More verbose logging
    log_dir="logs/custom",  # Custom log directory
    max_bytes=5242880,  # 5MB file size limit
    backup_count=10  # Keep 10 backup files
)
```

## Configuration Options

The `setup_logger()` function accepts the following parameters:

- `name`: Logger name (typically `__name__`)
- `level`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `log_dir`: Directory for log files (default: "logs")
- `console_output`: Enable/disable console output (default: True)
- `file_output`: Enable/disable file output (default: True)
- `max_bytes`: Maximum log file size before rotation (default: 10MB)
- `backup_count`: Number of backup files to keep (default: 5)
- `format_string`: Custom format for log messages

## Log File Structure

Log files are automatically created in the `logs/` directory with the following naming convention:

```
logs/
├── module_name_20240815.log      # Current log file
├── module_name_20240815.log.1    # First backup
├── module_name_20240815.log.2    # Second backup
└── ...
```

## Log Message Format

### Console Format (with colors)
```
2024-08-15 10:30:45 - module_name - INFO - Your message here
```

### File Format
```
2024-08-15 10:30:45 - module_name - INFO - Your message here
```

## Color Coding

Console output uses the following color scheme:

- 🔵 **DEBUG**: Cyan - Detailed diagnostic information
- 🟢 **INFO**: Green - General informational messages
- 🟡 **WARNING**: Yellow - Warning messages
- 🔴 **ERROR**: Red - Error messages
- 🟣 **CRITICAL**: Magenta - Critical issues

## Testing the Logging Configuration

Run the test script to verify the logging configuration:

```bash
# Run tests and keep log files
python test_logging.py

# Run tests and automatically clean up log files
python test_logging.py --cleanup
```

## Environment Variables

You can control logging behavior through environment variables:

```bash
# Set default log level (optional)
export LOG_LEVEL=DEBUG

# Set log directory (optional)
export LOG_DIR=/path/to/logs
```

## Integration with Existing Modules

The logging configuration has been integrated into the following modules:

- `api_server.py` - FastAPI server logging
- `llm_processor.py` - LLM query processing logging
- `mcp_manager.py` - MCP server connection logging
- `terminal_app.py` - Terminal application logging
- `main.py` - Main application entry point

## Best Practices

1. **Use appropriate log levels**:
   - DEBUG: Detailed information for debugging
   - INFO: General application flow
   - WARNING: Unexpected but handled situations
   - ERROR: Errors that don't stop the application
   - CRITICAL: Errors that might stop the application

2. **Include context in log messages**:
   ```python
   logger.info(f"Processing request for user {user_id}")
   logger.error(f"Failed to connect to database at {db_url}")
   ```

3. **Use structured logging for complex data**:
   ```python
   logger.info(f"API response: status={status}, time={elapsed}ms")
   ```

4. **Log at appropriate points**:
   - Application startup/shutdown
   - Major operations start/end
   - Error conditions
   - Important state changes

5. **Avoid logging sensitive information**:
   - Never log passwords, API keys, or tokens
   - Be careful with personal data

## Troubleshooting

### No log files are created
- Check that the `logs/` directory has write permissions
- Verify that `file_output=True` in logger configuration

### Console output is not colored
- Colors are only supported in terminals that support ANSI escape codes
- Windows Command Prompt may require additional configuration

### Log files are growing too large
- Adjust `max_bytes` parameter to a smaller value
- Reduce `backup_count` if disk space is limited

### Too many/few log messages
- Adjust the log level: `logger.setLevel(logging.WARNING)`
- Configure third-party library logging levels

## Third-Party Library Logging

The configuration automatically reduces noise from common third-party libraries:

- urllib3, asyncio, httpx, httpcore: WARNING level
- OpenAI SDK: WARNING level
- FastAPI/Starlette: WARNING level
- Uvicorn access logs: WARNING level

To adjust these settings, modify the `configure_third_party_loggers()` function in `logger_config.py`.