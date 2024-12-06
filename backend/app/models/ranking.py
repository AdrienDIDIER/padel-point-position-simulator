from pydantic import BaseModel

class RankingResponse(BaseModel):
    position: int
    additional_points_needed: int
