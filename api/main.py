from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from api.routes import health, jobs
from api.logging_config import logger
from api.config import settings

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CrypTax API is starting up...")
    yield
    logger.info("CrypTax API is shutting down...")

app = FastAPI(
    title="CrypTax API",
    description="API for tax processing services for crypto brokers (Binance, Coinbase, Kraken).",
    version="1.0.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
    responses={
        503: {"description": "Service Unavailable - The server is currently unable to handle the request due to a temporary overloading or maintenance of the server."}
    }
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to return HTTP 503 for all unhandled exceptions."""
    logger.error(f"Unhandled exception occurred: {str(exc)}")
    logger.exception(exc)
    return JSONResponse(
        status_code=503,
        content={"message": "Service Unavailable. Please try again later."},
    )

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
