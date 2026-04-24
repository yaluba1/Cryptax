from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.database import get_db
from api.rq_service import rq_service
from loguru import logger

router = APIRouter()

@router.get("/health", tags=["system"])
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint that verifies DB and Redis connectivity."""
    health_status = {
        "status": "ok",
        "database": "down",
        "redis": "down"
    }
    
    # Check Database
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "ok"
    except Exception as e:
        logger.error(f"Health check failed: Database unreachable. {str(e)}")
    
    # Check Redis
    if rq_service.ping():
        health_status["redis"] = "ok"
    else:
        logger.error("Health check failed: Redis unreachable.")

    if health_status["database"] != "ok" or health_status["redis"] != "ok":
        health_status["status"] = "unhealthy"
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status
