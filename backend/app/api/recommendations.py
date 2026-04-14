from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ParseIntentRequest(BaseModel):
    query: str


class SearchRequest(BaseModel):
    province: str
    score: int
    subject_combo: list[str]
    risk_level: str


@router.post("/parse-intent")
def parse_intent(payload: ParseIntentRequest) -> dict:
    return {
        "message": "parse intent placeholder",
        "query": payload.query,
        "structured_conditions": {},
    }


@router.post("/search")
def search_recommendations(payload: SearchRequest) -> dict:
    return {
        "message": "recommendation search placeholder",
        "conditions": payload.model_dump(),
        "results": [],
    }