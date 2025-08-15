from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import uuid
import asyncio
from typing import Dict, List
from openai.types.chat import ChatCompletionMessageParam
from llm_processor import LLMQueryProcessor, LLMQueryRequest, LLMQueryResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    # Startup
    app.state.llm_processor = LLMQueryProcessor()
    await app.state.llm_processor.initialize()
    app.state.chat_sessions: Dict[str, List[ChatCompletionMessageParam]] = {}
    yield
    # Shutdown
    await app.state.llm_processor.cleanup()


app = FastAPI(lifespan=lifespan)


@app.post("/chat", response_model=LLMQueryResponse)
async def process_llm_query(request: LLMQueryRequest):
    """Process a query using the LLM with conversation memory."""
    if not hasattr(app.state, 'llm_processor') or not app.state.llm_processor:
        raise HTTPException(status_code=500, detail="LLM processor not initialized")

    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())

    # Retrieve conversation history
    conversation_history = app.state.chat_sessions.get(session_id, [])

    try:
        # Process query with history
        response, updated_messages = await app.state.llm_processor.process_query(
            request.query,
            conversation_history
        )

        # Store updated conversation (excluding system prompt)
        app.state.chat_sessions[session_id] = [
            msg for msg in updated_messages
            if msg.get("role") != "system"
        ]

        return LLMQueryResponse(response=response, session_id=session_id)
    except Exception as e:
        return LLMQueryResponse(
            response="",
            session_id=session_id,
            error=f"Error processing query: {str(e)}"
        )


@app.delete("/chat/{session_id}")
async def clear_session(session_id: str):
    """Clear a specific conversation session."""
    if session_id in app.state.chat_sessions:
        del app.state.chat_sessions[session_id]
        return {"message": "Session cleared"}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/chat/{session_id}/history")
async def get_session_history(session_id: str):
    """Get conversation history for a session."""
    if session_id in app.state.chat_sessions:
        return {"session_id": session_id, "history": app.state.chat_sessions[session_id]}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "processor_initialized": hasattr(app.state, 'llm_processor')}


async def main():
    """Run the FastAPI app with uvicorn."""
    import uvicorn
    await uvicorn.Server(
        uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8003,
            log_level="info"
        )
    ).serve()


if __name__ == "__main__":
    asyncio.run(main())
