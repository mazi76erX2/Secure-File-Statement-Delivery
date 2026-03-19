from fastapi import APIRouter
from .statements import router as statements_router


api_router = APIRouter()
api_router.include_router(statements_router)
