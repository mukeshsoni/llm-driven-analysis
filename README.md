 ### Install dependencies
 Run `uv sync`

 Now you should be able to run the main python script using `uv run main.py`

## TODO
- [X] Connect to openai endpoint and generate a response to a query from the LLM
- [X] Implement a chat loop/assistant on the terminal where user can talk to the LLM
- [X] Implement a simple MCP server and test with MCP inspector
- [X] Implement a simple MCP client and test with our MCP server
- [X] Integrate our chat loop with the MCP client so that the LLM can use our MCP server. The key is to have the chat loop as a method of MCP client. The MCP client takes care of both communicating with the LLM endpoint as well as making the tools calls to the appropriate MCP servers.
- [X] Make the MCP client, MCP server and the openai endpoint work together. Update prompt so that the LLM calls our tool for some task. The tool description takes care of LLM calling a tool. We don't need to tell it again inside the prompt.
- [ ] Use structured output with pydantic classes. P. S. Looks like it's not possible to use structured output with funciton/tool calls.
- [X] Add an MCP server which runs SQL queries on some database. Will need to change the prompt too.
- [ ] Expose the MCP client through an http api endpoint. For us, mainly figure out how to integrate FastMCP with FastAPI. Integrating with existing FastAPI server is a different beast than simply exposing our FastMCP servers as FastAPI endpoints.
- [ ] Multiple MCP servers. According to anthropic blog, there should  be one MCP client per MCP server! After going through reddit and the rest of the internet, it seems like this one client per server is not a strict thing. In fact, most implementations use a single client to connect to multiple MCP servers.
- [ ] Web UI
- [ ] Moving MCP server configurations to a json file. Or should it simply be a python dict? Why complicate things.
- [ ] Figure out how to handle concurrent sessions from multiple users
- [ ] Add copilot like functionality which allows users to update database through the LLM. E.g. add a new sales record for an artist in the database.
- [ ] Authorisation
