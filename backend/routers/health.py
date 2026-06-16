"""
Router para verificación de salud del servicio.
"""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """
    Verifica que el servicio esté funcionando.
    Returns:
        dict: Estado del servicio.
    """
    return {"status": "OK"}