from fastapi import APIRouter

router = APIRouter()


@router.get("/template")
def get_assessment_template() -> dict:
    return {
        "message": "assessment template placeholder",
        "sections": [],
    }