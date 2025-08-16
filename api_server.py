from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uuid
import asyncio
import time
from typing import Dict, List
from openai.types.chat import ChatCompletionMessageParam
from llm_processor import LLMQueryProcessor, LLMQueryRequest, LLMQueryResponse
from logger_config import get_logger, log_exception

# Initialize logger for this module
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    # Startup
    logger.info("Starting up API server...")
    try:
        app.state.llm_processor = LLMQueryProcessor()
        await app.state.llm_processor.initialize()
        app.state.chat_sessions: Dict[str, List[ChatCompletionMessageParam]] = {}
        logger.info("API server startup complete")
    except Exception as e:
        log_exception(logger, e, "Failed to initialize LLM processor")
        raise

    yield

    # Shutdown
    logger.info("Shutting down API server...")
    await app.state.llm_processor.cleanup()
    logger.info("API server shutdown complete")


app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat", response_model=LLMQueryResponse)
async def process_llm_query(request: LLMQueryRequest):
    """Process a query using the LLM with conversation memory."""
    request_start_time = time.perf_counter()

    if not hasattr(app.state, 'llm_processor') or not app.state.llm_processor:
        logger.error("LLM processor not initialized when processing query")
        raise HTTPException(status_code=500, detail="LLM processor not initialized")

    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    logger.info(f"Processing query for session {session_id}: {request.query[:100]}...")

    # Retrieve conversation history
    conversation_history = app.state.chat_sessions.get(session_id, [])
    logger.debug(f"Session {session_id} has {len(conversation_history)} messages in history")

    try:
        # Process query with history
        processing_start = time.perf_counter()
        response, updated_messages, timing_info = await app.state.llm_processor.process_query(
            request.query,
            conversation_history
        )
        processing_time = time.perf_counter() - processing_start

        # Store updated conversation (excluding system prompt)
        app.state.chat_sessions[session_id] = [
            msg for msg in updated_messages
            if msg.get("role") != "system"
        ]

        total_time = time.perf_counter() - request_start_time

        # Log comprehensive timing information
        logger.info(f"✅ Successfully processed query for session {session_id}")
        logger.info(f"⏱️  Total API request time: {total_time:.3f}s")
        logger.info(f"   ├─ Processing time: {processing_time:.3f}s")
        if timing_info:
            logger.info(f"   │  ├─ LLM calls: {timing_info.get('llm_time', 0):.3f}s ({timing_info.get('llm_calls', 0)} calls)")
            logger.info(f"   │  ├─ Tool calls: {timing_info.get('tool_time', 0):.3f}s ({timing_info.get('tool_calls', 0)} calls)")
            logger.info(f"   │  └─ Other: {processing_time - timing_info.get('llm_time', 0) - timing_info.get('tool_time', 0):.3f}s")
        logger.info(f"   └─ API overhead: {total_time - processing_time:.3f}s")

        return LLMQueryResponse(response=response, session_id=session_id)
    except Exception as e:
        total_time = time.perf_counter() - request_start_time
        log_exception(logger, e, f"Error processing query for session {session_id} (took {total_time:.3f}s)")
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
        logger.info(f"Cleared session {session_id}")
        return {"message": "Session cleared"}
    logger.warning(f"Attempted to clear non-existent session {session_id}")
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/chat/{session_id}/history")
async def get_session_history(session_id: str):
    """Get conversation history for a session."""
    if session_id in app.state.chat_sessions:
        history_length = len(app.state.chat_sessions[session_id])
        logger.debug(f"Retrieved history for session {session_id} ({history_length} messages)")
        return {"session_id": session_id, "history": app.state.chat_sessions[session_id]}
    logger.warning(f"Attempted to get history for non-existent session {session_id}")
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    is_initialized = hasattr(app.state, 'llm_processor')
    logger.debug(f"Health check: processor_initialized={is_initialized}")
    return {"status": "healthy", "processor_initialized": is_initialized}


async def main():
    """Run the FastAPI app with uvicorn."""
    import uvicorn
    logger.info("Starting uvicorn server on http://0.0.0.0:8003")
    await uvicorn.Server(
        uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8003,
            log_level="info"
        )
    ).serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        log_exception(logger, e, "Unexpected error during server execution")
        raise
