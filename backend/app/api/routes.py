
from fastapi import APIRouter

router = APIRouter()

@router.post("/generate")
def generate(payload: dict):
    return {"message": "stub - connect MapGenerator here"}
