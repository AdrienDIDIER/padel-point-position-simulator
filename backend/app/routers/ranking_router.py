from fastapi import APIRouter, HTTPException
from ..models.ranking import RankingResponse
from ..services.ranking_service import simulate_position

router = APIRouter()

@router.get("/position", response_model=RankingResponse)
def get_position(points: int):
    result = simulate_position(points)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
