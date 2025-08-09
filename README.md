 ### Install dependencies
 Run `uv sync`

 Now you should be able to run the main python script using `uv run main.py`

## TODO
- [X] Connect to openai endpoint and generate a response to a query from the LLM
- [X] Implement a chat loop/assistant on the terminal where user can talk to the LLM
- [X] Implement a simple MCP server and test with MCP inspector
- [X] Implement a simple MCP client and test with our MCP server
- [X] Integrate our chat loop with the MCP client so that the LLM can use our MCP server. The key is to have the chat loop as a method of MCP client. The MCP client takes care of both communicating with the LLM endpoint as well as making the tools calls to the appropriate MCP servers.
- [ ] Use structured output with pydantic classes
- [ ] Add an MCP server which runs SQL queries on some database. Will need to change the prompt too.
- [ ] Expose the MCP client through an http api endpoint
- [ ] Figure out how to handle concurrent sessions from multiple users
