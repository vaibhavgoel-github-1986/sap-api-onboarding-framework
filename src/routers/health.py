"""
Health check router for application monitoring.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import datetime
import os
import sys

from ..config import get_settings
from ..utils.logger import logger

router = APIRouter()


@router.get(
    "/",
    summary="Application Health Check",
    description="Returns the current health status of the SAP Tools API"
)
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring and load balancing.
    
    Returns:
        Dict containing health status and system information
    """
    try:
        settings = get_settings()
        
        # Basic health checks
        health_status = {
            "status": "healthy",
            "timestamp": datetime.datetime.now().isoformat(),
            "version": settings.app_version,
            "service": settings.app_title,
            "environment": {
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "log_level": settings.log_level
            },
            "checks": {
                "configuration": "ok",
                "dependencies": "ok"
            }
        }
        
        # Check if required environment variables are set
        try:
            settings.validate_required_settings()
            health_status["checks"]["configuration"] = "ok"
        except ValueError as e:
            logger.warning(f"Configuration issue detected: {e}")
            health_status["checks"]["configuration"] = "warning"
            health_status["warnings"] = [str(e)]
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "timestamp": datetime.datetime.now().isoformat(),
                "error": "Health check failed"
            }
        )