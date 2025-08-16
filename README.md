# LLM-Driven Database Analysis System

A system that uses LLMs with MCP (Model Context Protocol) to query and analyze multiple SQLite databases dynamically.

## Features

- **Multi-Database Support**: Query multiple SQLite databases through a single interface
- **Dynamic Schema Loading**: Automatically discovers and loads database schemas at runtime
- **MCP Integration**: Uses MCP servers for database operations and file system access
- **Session Management**: Maintains conversation history across API calls
- **REST API**: FastAPI-based HTTP interface for easy integration
- **Terminal Chat**: Interactive command-line interface for direct database queries
- **Dual Mode Operation**: Run as either an API server or terminal application
- **Chart Generation**: Automatically generates chart configurations for visualizable data

## Setup

### Install dependencies
Run `uv sync` to install all dependencies including Plotly and Pandas for chart visualization.

### Create sample databases (optional)
```bash
# Create employees database for testing multi-database support
python create_sample_db.py
```

## Running the Application

The application can run in two modes: **API Server** or **Terminal Chat**.

### Terminal Mode (Interactive Chat)
For an interactive command-line chat interface:

```bash
# Option 1: Run terminal app directly
uv run python terminal_app.py

# Option 2: Use main.py with terminal mode
uv run python main.py --mode terminal
```

In terminal mode:
- Type your queries directly in the console
- The LLM will respond with database analysis results
- Type 'exit', 'quit', or 'bye' to end the session
- Session history is maintained during the conversation

### API Server Mode
To run as a REST API server:

```bash
# Option 1: Default mode (API server)
uv run python main.py

# Option 2: Explicitly specify API mode
uv run python main.py --mode api

# Option 3: Run API server directly
uv run python api_server.py

# Option 4: Specify custom port
uv run python main.py --mode api --port 8080
```

The API will be available at `http://localhost:8003` (or your specified port)

## Usage Examples

### Testing Chart Generation
Run the example script to see chart generation in action:
```bash
# Run the example chart queries
uv run python example_chart_queries.py
```

### Terminal Mode Examples
When running in terminal mode, you can have conversations like:

```
User: How many artists are in the database?
[LLM responds with the count of artists from the chinook database]

User: Show me the top 5 customers by total purchase amount
[LLM generates and runs SQL query, then provides formatted results]

User: How many employees are in the Engineering department? Use the employees database.
[LLM switches to employees database and provides the information]

User: exit
Goodbye!
```

### API Mode Examples

#### Query a database
```bash
curl -X POST http://localhost:8003/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How many artists are in the database?"}'
```

#### Query with chart generation
```bash
# Request data with visualization
curl -X POST http://localhost:8003/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me the top 5 genres by number of tracks in a bar chart"}'

# Response format:
# {
#   "response": "Here are the top 5 genres by number of tracks...",
#   "session_id": "...",
#   "chart": {
#     "type": "bar",
#     "title": "Top 5 Genres by Track Count",
#     "data": {
#       "labels": ["Rock", "Latin", "Metal", "Alternative", "Jazz"],
#       "datasets": [{
#         "label": "Number of Tracks",
#         "data": [1297, 579, 374, 332, 130]
#       }]
#     }
#   }
# }
# Note: The LLM returns responses as JSON with "response" and "chart" fields.
# The "chart" field is null when visualization is not applicable.
```

#### Query with session management
```bash
# First query - returns a session_id
curl -X POST http://localhost:8003/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me all albums by Led Zeppelin"}'

# Follow-up query using session_id to maintain context
curl -X POST http://localhost:8003/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How many tracks are in their first album?", "session_id": "YOUR_SESSION_ID"}'
```

#### Query a specific database
```bash
curl -X POST http://localhost:8003/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How many employees are in the Engineering department? Use the employees database."}'
```

#### Get session history
```bash
curl -X GET http://localhost:8003/chat/YOUR_SESSION_ID/history
```

#### Clear a session
```bash
curl -X DELETE http://localhost:8003/chat/YOUR_SESSION_ID
```

#### Health check
```bash
curl -X GET http://localhost:8003/health
```

## Available Databases

- **chinook**: Music store database with artists, albums, tracks, and sales data
- **employees**: Employee management database with departments, employees, and projects

## Chart Generation

The system automatically generates chart configurations when data is suitable for visualization. The LLM returns all responses as structured JSON objects containing:

- `response`: The natural language answer to the query
- `chart`: Either `null` (when no visualization is needed) or a chart configuration object

The API response preserves this structure and adds a `session_id` field:

- `type`: Chart type (bar, line, pie, scatter, area)
- `title`: Chart title
- `data`: Chart data including labels and datasets
- `options`: Chart display options (axes, scales, etc.)

### Supported Chart Types

- **Bar Chart**: For comparing categories (e.g., "top 5 genres by track count")
- **Line Chart**: For trends over time (e.g., "sales by month over the last year")
- **Pie Chart**: For showing proportions (e.g., "percentage of tracks by media type")
- **Scatter Plot**: For relationships between variables
- **Area Chart**: For cumulative trends

### Example Queries for Charts

```bash
# Bar chart - categorical comparisons
"Show me the top 10 artists by total sales revenue with a chart"

# Line chart - time series
"What are the total sales by month over the last year? Display as a line chart"

# Pie chart - proportions
"What percentage of tracks are in each media type? Show as a pie chart"

# Distribution chart
"Show me the distribution of track lengths across all albums"
```

## Project Structure

- `llm_processor.py` - Core LLM query processing logic and MCP integration with chart generation
- `api_server.py` - FastAPI server implementation with session management and chart support
- `terminal_app.py` - Interactive terminal chat interface
- `streamlit_app.py` - Web UI with chart visualization using Plotly
- `main.py` - Unified entry point with mode selection
- `mcp_manager.py` - MCP client manager for tool orchestration
- `mcp_server_sql.py` - MCP server for SQL database operations
- `mcp_server_file_system.py` - MCP server for file system operations
- `example_chart_queries.py` - Example script demonstrating chart generation
- `test_chart_generation.py` - Test suite for chart generation functionality
- `test_json_response.py` - Test suite for JSON response format validation

## TODO
- [X] Connect to openai endpoint and generate a response to a query from the LLM
- [X] Implement a chat loop/assistant on the terminal where user can talk to the LLM
- [X] Implement a simple MCP server and test with MCP inspector
- [X] Implement a simple MCP client and test with our MCP server
- [X] Integrate our chat loop with the MCP client so that the LLM can use our MCP server. The key is to have the chat loop as a method of MCP client. The MCP client takes care of both communicating with the LLM endpoint as well as making the tools calls to the appropriate MCP servers.
- [X] Make the MCP client, MCP server and the openai endpoint work together. Update prompt so that the LLM calls our tool for some task. The tool description takes care of LLM calling a tool. We don't need to tell it again inside the prompt.
- [ ] Use structured output with pydantic classes. P. S. Looks like it's not possible to use structured output with funciton/tool calls.
- [X] Add an MCP server which runs SQL queries on some database. Will need to change the prompt too.
- [X] Use MCP resources or tools to expose db and table schema from the sql execution MCP server. Instead of hard coding in the prompt. That should allow us to scale to any number of databases.
- [X] Refactor MCPClient. Rename it to MCPManager. And break it into 2 parts. MCPManager should only handle MCP stuff.
- [X] Multiple MCP servers. According to anthropic blog, there should  be one MCP client per MCP server! After going through reddit and the rest of the internet, it seems like this one client per server is not a strict thing. In fact, most implementations use a single client to connect to multiple MCP servers.
- [X] Expose the MCP client through an http api endpoint. For us, mainly figure out how to integrate FastMCP with FastAPI. Integrating with existing FastAPI server is a different beast than simply exposing our FastMCP servers as FastAPI endpoints.
- [X] Get database table schemas dynamically when application starts. Use MCP server resource to get table schemas. Add support for multiple databases in our sql MCP server.
- [X] Web UI
- [X] Add logging. Mainly log the query response times. These might vary wildly for trying to solve problems with llm calls. Also log the breakup of the call between llm call and tool calls.
- [ ] Get LLM to return markdown
- [X] Ability to render charts from the data in our database
- [ ] Figure out how to handle concurrent sessions from multiple users
- [ ] Add copilot like functionality which allows users to update database through the LLM. E.g. add a new sales record for an artist in the database.
- [ ] Streaming response. If we stream response, does it mean we can respond with structured output? We HAVE to use markdown or text only?
- [ ] User conversation history
- [ ] Authorisation
- [ ] Write tests for MCP servers
- [ ] Handle case when session_id sent in a request is not in our session list. We should not entertain that request. Right now we would simply start a session with that session id for that user.
