from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ReportGenerateRequest(BaseModel):
    student_id: int


class ReportUpdateRequest(BaseModel):
    sections: list[dict]


@router.post("/generate")
def generate_report(payload: ReportGenerateRequest) -> dict:
    return {
        "message": "report generate placeholder",
        "report_id": "TODO-report-id",
        "student_id": payload.student_id,
    }


@router.patch("/{report_id}")
def update_report(report_id: str, payload: ReportUpdateRequest) -> dict:
    return {
        "message": "report update placeholder",
        "report_id": report_id,
        "section_count": len(payload.sections),
    }


@router.post("/{report_id}/export-pdf")
def export_report_pdf(report_id: str) -> dict:
    return {
        "message": "report export placeholder",
        "report_id": report_id,
        "status": "queued",
    }