import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.health import router as health_router
from .routers.sap_tools import router as sap_tools
from .utils.logger import logger
from .config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("SAP Tools FastAPI server starting up...")

    yield

    # Shutdown
    logger.info("SAP Tools FastAPI server shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_title,
        description="AI-Powered SAP Technical Tools API",
        version=settings.app_version,
        docs_url="/docs",
        lifespan=lifespan,
    )

    # Add CORS middleware with secure defaults
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router, tags=["Health Check"])
    app.include_router(sap_tools, tags=["SAP Tools"])

    return app


def main() -> None:
    """Main entry point for the application."""
    settings = get_settings()
    uvicorn.run(
        create_app(), 
        host=settings.host, 
        port=settings.port, 
        reload=settings.debug, 
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
