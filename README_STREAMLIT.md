# Streamlit Chat Interface for Database Analysis

This is a web-based chat interface for the LLM-driven database analysis application.

## Prerequisites

1. Make sure the FastAPI server is running:
   ```bash
   python api_server.py
   ```
   The API server should be running on `http://localhost:8003`

2. Install dependencies (if not already installed):
   ```bash
   pip install streamlit
   # or if using uv:
   uv pip install streamlit
   ```

## Running the Streamlit App

1. Start the Streamlit app:
   ```bash
   streamlit run streamlit_app.py
   ```

2. The app will automatically open in your browser at `http://localhost:8501`

## Features

- **Chat Interface**: Natural language conversation with your databases
- **Session Management**: Maintains conversation history throughout the session
- **Connection Status**: Real-time API connection monitoring
- **Clear Chat**: Reset the conversation without losing session
- **New Session**: Start a fresh session with new context

## Usage Examples

Try these example queries in the chat:

- "Show me all tables in the database"
- "List the first 10 customers"
- "What are the top selling products?"
- "How many orders were placed last month?"
- "Show me the database schema"
- "Count the total number of employees"

## Configuration

The app connects to the FastAPI server at `http://localhost:8003` by default. You can change this in the sidebar settings if your API is running on a different port or host.

## Troubleshooting

### Cannot connect to API
- Ensure the FastAPI server is running (`python api_server.py`)
- Check that the API URL in the sidebar is correct
- Verify that CORS is enabled in the FastAPI server

### Queries timeout
- Complex queries may take longer to process
- The timeout is set to 60 seconds by default
- Check the API server logs for any errors

### Session issues
- Click "New Session" to start fresh if you encounter any session-related problems
- The session ID is displayed in the sidebar for reference

## Development

To modify the Streamlit app:
1. Edit `streamlit_app.py`
2. Streamlit will automatically reload when you save changes (if running in development mode)

## Notes

- The chat history is maintained in the Streamlit session state
- The backend API also maintains conversation history for context-aware responses
- CORS is enabled on the FastAPI server to allow browser-based requests