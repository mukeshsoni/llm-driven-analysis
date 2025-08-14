# LLM-Driven Database Analysis System

A system that uses LLMs with MCP (Model Context Protocol) to query and analyze multiple SQLite databases dynamically.

## Features

- **Multi-Database Support**: Query multiple SQLite databases through a single interface
- **Dynamic Schema Loading**: Automatically discovers and loads database schemas at runtime
- **MCP Integration**: Uses MCP servers for database operations and file system access
- **Session Management**: Maintains conversation history across API calls
- **REST API**: FastAPI-based HTTP interface for easy integration

## Setup

### Install dependencies
Run `uv sync`

### Create sample databases (optional)
```bash
# Create employees database for testing multi-database support
python create_sample_db.py
```

### Run the system
```bash
# Start the FastAPI server with MCP integration
uv run main.py
```

The API will be available at `http://localhost:8003`

## API Usage

### Query a database
```bash
curl -X POST http://localhost:8003/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How many artists are in the database?"}'
```

### Query a specific database
```bash
curl -X POST http://localhost:8003/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "How many employees are in the Engineering department? Use the employees database."}'
```

## Available Databases

- **chinook**: Music store database with artists, albums, tracks, and sales data
- **employees**: Employee management database with departments, employees, and projects

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
- [ ] Handle case when session_id sent in a request is not in our session list. We should not entertain that request. Right now we would simply start a session with that session id for that user.
- [ ] Web UI
- [ ] Ability to render charts from the data in our database
- [ ] Figure out how to handle concurrent sessions from multiple users
- [ ] Add copilot like functionality which allows users to update database through the LLM. E.g. add a new sales record for an artist in the database.
- [ ] Add logging. Mainly log the query response times. These might vary wildly for trying to solve problems with llm calls. Also log the breakup of the call between llm call and tool calls.
- [ ] Streaming response. If we stream response, does it mean we can respond with structured output? We HAVE to use markdown or text only?
- [ ] User conversation history
- [ ] Authorisation
