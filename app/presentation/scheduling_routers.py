import logging
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status, Depends
from app.presentation.dto.message_request_payload import WebhookPayload
from app.application.services.scheduling_service import (
    get_scheduling_service,
    SchedulingService,
)
from app.infrastructure.config.config import settings
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

router = APIRouter()


class MessageRequest(BaseModel):
    message: str


@router.post("/", summary="Recebe mensagem do webhook", status_code=status.HTTP_200_OK)
async def receive_webhook(
    payload: WebhookPayload, service: SchedulingService = Depends(get_scheduling_service)
):
    logger.info(f"Nova mensagem de '{payload.phone_number}' recebida.")
    logger.info(f"Conteúdo: '{payload.message}'")

    result = await service.handle_incoming_message(
        payload.phone_number, payload.message, payload.message_id
    )

    return result

@router.post("/debug/truncate-tables")
async def truncate_langgraph_tables():
    """🗑️ Limpa todas as tabelas do LangGraph"""
    try:
        postgres_uri = (
            f"postgresql://"
            f"{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD.get_secret_value()}"
            f"@db:5432/{settings.POSTGRES_DB}"
        )
        
        connection_kwargs = {
            "autocommit": True,
            "prepare_threshold": 0,
            "row_factory": dict_row,
        }
        
        pool = AsyncConnectionPool(
            conninfo=postgres_uri,
            max_size=5,
            kwargs=connection_kwargs
        )
        await pool.open()
        
        try:
            async with pool.connection() as conn:
                # Tabelas do LangGraph
                tables = ['checkpoints', 'checkpoint_writes', 'store']
                
                for table in tables:
                    try:
                        async with conn.cursor() as cursor:
                            await cursor.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
                        logger.info(f"✅ {table} truncada")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao truncar {table}: {e}")
                
                return {"status": "success", "message": "Tabelas LangGraph limpas"}
        finally:
            await pool.close()
            
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))
