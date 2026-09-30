from fastapi import APIRouter

from app.services import legal_service

router = APIRouter()


@router.get("/info")
def legal_info():
    """Dados públicos do vendedor usados no rodapé e nos documentos legais."""
    return legal_service.public_info()
