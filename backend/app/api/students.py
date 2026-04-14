import json
from datetime import datetime
from typing import Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Student, StudentAssessment, User

router = APIRouter()

RiskPreference = Literal["conservative", "balanced", "aggressive"]


class StudentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    province: str = Field(min_length=1, max_length=64)
    score: int = Field(ge=0, le=750)
    rank: int | None = Field(default=None, ge=1)
    subject_combo: list[str] = Field(default_factory=list)
    risk_preference: RiskPreference | None = None
    notes: str | None = Field(default=None, max_length=2000)


class StudentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    province: str | None = Field(default=None, min_length=1, max_length=64)
    score: int | None = Field(default=None, ge=0, le=750)
    rank: int | None = Field(default=None, ge=1)
    subject_combo: list[str] | None = None
    risk_preference: RiskPreference | None = None
    notes: str | None = Field(default=None, max_length=2000)


class StudentResponse(BaseModel):
    id: int
    name: str
    province: str
    score: int
    rank: int | None
    subject_combo: list[str]
    risk_preference: str | None
    notes: str | None
    counselor_id: int
    created_at: datetime
    updated_at: datetime


class StudentListResponse(BaseModel):
    total: int
    items: list[StudentResponse]


class StudentAssessmentRequest(BaseModel):
    answers: list[dict] = Field(default_factory=list)
    summary: str | None = Field(default=None, max_length=4000)


class StudentAssessmentResponse(BaseModel):
    id: int
    student_id: int
    counselor_id: int
    answer_count: int
    answers: list[dict]
    summary: str | None
    created_at: datetime


def _pack_subject_combo(subjects: list[str]) -> str:
    cleaned = [item.strip() for item in subjects if item.strip()]
    return ",".join(cleaned)


def _unpack_subject_combo(raw_value: str) -> list[str]:
    if not raw_value:
        return []
    return [item for item in (part.strip() for part in raw_value.split(",")) if item]


def _to_student_response(student: Student) -> StudentResponse:
    return StudentResponse(
        id=student.id,
        name=student.name,
        province=student.province,
        score=student.score,
        rank=student.rank,
        subject_combo=_unpack_subject_combo(student.subject_combo),
        risk_preference=_normalize_risk_preference(student.risk_preference),
        notes=student.notes,
        counselor_id=student.counselor_id,
        created_at=student.created_at,
        updated_at=student.updated_at,
    )


def _to_assessment_response(item: StudentAssessment) -> StudentAssessmentResponse:
    try:
        answers = json.loads(item.answers_json)
        if not isinstance(answers, list):
            answers = []
    except json.JSONDecodeError:
        answers = []

    return StudentAssessmentResponse(
        id=item.id,
        student_id=item.student_id,
        counselor_id=item.counselor_id,
        answer_count=item.answer_count,
        answers=answers,
        summary=item.summary,
        created_at=item.created_at,
    )


def _apply_visibility_filter(stmt, current_user: User):
    if current_user.role == "admin":
        return stmt
    return stmt.where(Student.counselor_id == current_user.id)


def _normalize_risk_preference(value: str | None) -> RiskPreference | None:
    if value is None:
        return None
    if value in {"conservative", "balanced", "aggressive"}:
        return cast(RiskPreference, value)
    return None


def _get_student_or_404(student_id: int, db: Session, current_user: User) -> Student:
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    if current_user.role != "admin" and student.counselor_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this student")

    return student


@router.get("", response_model=StudentListResponse)
def list_students(
    q: str | None = Query(default=None, max_length=128),
    province: str | None = Query(default=None, max_length=64),
    min_score: int | None = Query(default=None, ge=0, le=750),
    max_score: int | None = Query(default=None, ge=0, le=750),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentListResponse:
    if min_score is not None and max_score is not None and min_score > max_score:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="min_score cannot exceed max_score")

    base_stmt = _apply_visibility_filter(select(Student), current_user)
    count_stmt = _apply_visibility_filter(select(func.count()).select_from(Student), current_user)

    if q:
        like_pattern = f"%{q}%"
        base_stmt = base_stmt.where(Student.name.like(like_pattern))
        count_stmt = count_stmt.where(Student.name.like(like_pattern))

    if province:
        base_stmt = base_stmt.where(Student.province == province)
        count_stmt = count_stmt.where(Student.province == province)

    if min_score is not None:
        base_stmt = base_stmt.where(Student.score >= min_score)
        count_stmt = count_stmt.where(Student.score >= min_score)

    if max_score is not None:
        base_stmt = base_stmt.where(Student.score <= max_score)
        count_stmt = count_stmt.where(Student.score <= max_score)

    total = db.scalar(count_stmt) or 0
    students = db.scalars(base_stmt.order_by(Student.id.desc()).offset(offset).limit(limit)).all()

    return StudentListResponse(total=total, items=[_to_student_response(item) for item in students])


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentResponse:
    student = _get_student_or_404(student_id, db, current_user)
    return _to_student_response(student)


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentResponse:
    student = Student(
        name=payload.name,
        province=payload.province,
        score=payload.score,
        rank=payload.rank,
        subject_combo=_pack_subject_combo(payload.subject_combo),
        risk_preference=payload.risk_preference,
        notes=payload.notes,
        counselor_id=current_user.id,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return _to_student_response(student)


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    payload: StudentUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentResponse:
    student = _get_student_or_404(student_id, db, current_user)

    patch = payload.model_dump(exclude_none=True)
    if "subject_combo" in patch:
        student.subject_combo = _pack_subject_combo(patch.pop("subject_combo"))

    for field_name, value in patch.items():
        setattr(student, field_name, value)

    db.commit()
    db.refresh(student)
    return _to_student_response(student)


@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    student = _get_student_or_404(student_id, db, current_user)
    db.delete(student)
    db.commit()
    return {"message": "student deleted", "student_id": student_id}


@router.get("/{student_id}/assessments", response_model=list[StudentAssessmentResponse])
def list_assessments(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[StudentAssessmentResponse]:
    _get_student_or_404(student_id, db, current_user)

    items = db.scalars(
        select(StudentAssessment)
        .where(StudentAssessment.student_id == student_id)
        .order_by(StudentAssessment.id.desc())
    ).all()
    return [_to_assessment_response(item) for item in items]


@router.post("/{student_id}/assessments", response_model=StudentAssessmentResponse)
def submit_assessment(
    student_id: int,
    payload: StudentAssessmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StudentAssessmentResponse:
    _get_student_or_404(student_id, db, current_user)

    record = StudentAssessment(
        student_id=student_id,
        counselor_id=current_user.id,
        answers_json=json.dumps(payload.answers, separators=(",", ":"), ensure_ascii=False),
        answer_count=len(payload.answers),
        summary=payload.summary,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return _to_assessment_response(record)
