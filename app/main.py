"""
Propabridge Listings Service - Main application
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware as GZIPMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import init_db
from app.routes.listings import router as listings_router

logger = logging.getLogger(__name__)

settings = get_settings()


# Startup and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Propabridge Listings Service...")
    try:
        init_db()
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Propabridge Listings Service...")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    docs_url=settings.api_docs_url,
    redoc_url=settings.api_redoc_url,
    openapi_url=f"/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)


# ============ MIDDLEWARE ============

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# GZIP Middleware
app.add_middleware(GZIPMiddleware, minimum_size=1000)


# ============ ROUTES ============

# Include routers
app.include_router(listings_router, prefix=f"/api/{settings.api_version}")


# ============ HEALTH CHECK ============

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.api_version,
        "service": "listings",
        "environment": settings.environment,
    }


# ============ ROOT ENDPOINT ============

@app.get("/", tags=["Info"])
async def root():
    """Service information"""
    return {
        "title": settings.api_title,
        "description": settings.api_description,
        "version": settings.api_version,
        "service": "listings",
        "docs": settings.api_docs_url,
    }


# ============ ERROR HANDLING ============

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle ValueError exceptions"""
    logger.error(f"ValueError: {str(exc)}")
    return {
        "code": "VALIDATION_ERROR",
        "message": str(exc),
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return {
        "code": "INTERNAL_SERVER_ERROR",
        "message": "An unexpected error occurred",
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,  # Different port from user service (8000)
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
