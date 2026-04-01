"""API routes para historial de acciones/logs."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.database import get_db
from app.models.models import ActionLog, LogLevel
from app.schemas.schemas import LogResponse

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/", response_model=List[LogResponse])
async def get_logs(
    limit: int = Query(50, ge=1, le=500),
    level: LogLevel | None = None,
    product_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Lista los logs de acciones más recientes."""
    query = select(ActionLog).order_by(ActionLog.created_at.desc()).limit(limit)

    if level:
        query = query.where(ActionLog.level == level)
    if product_id:
        query = query.where(ActionLog.product_id == product_id)

    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/")
async def clear_logs(db: AsyncSession = Depends(get_db)):
    """Limpia todos los logs."""
    from sqlalchemy import delete
    await db.execute(delete(ActionLog))
    await db.commit()
    return {"detail": "Logs eliminados"}
