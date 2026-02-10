"""
NFL Chatbot API - FastAPI Backend

This is the main entry point for the FastAPI application.
Provides RAG-based chatbot API with LLM fallback system.

Usage:
    Local: uvicorn main:app --reload --port 8000
    Vercel: Automatically deployed via vercel.json
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import APIConfig, debug_info, debug_error

# Import routes
from routes.chat_routes import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Lifespan event handler for startup and shutdown.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None
    """
    # Startup
    debug_info("🚀 NFL Chatbot API started successfully!")
    debug_info(f"📚 Knowledge base path: {APIConfig.KNOWLEDGE_BASE_PATH}")
    yield
    # Shutdown (nothing to clean up)


# Initialize FastAPI app
app = FastAPI(
    title="NFL Chatbot API",
    description="RAG-based chatbot API representing Naufal (fal bot)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=APIConfig.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    """
    Root endpoint.
    
    Returns:
        dict: Welcome message
    """
    return {
        "message": "Welcome to NFL Chatbot API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for unhandled errors.
    
    Args:
        request: The incoming request
        exc: The exception that was raised
        
    Returns:
        JSONResponse with error details
    """
    debug_error(f"Unhandled error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error",
            "detail": str(exc) if APIConfig.API_KEY == "nfl-dev-key-2026" else None
        }
    )


# For Vercel serverless
handler = app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

