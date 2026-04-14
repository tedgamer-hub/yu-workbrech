from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="counselor")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    students: Mapped[list[Student]] = relationship(back_populates="counselor")
    import_tasks: Mapped[list[ImportTask]] = relationship(back_populates="creator")
    student_assessments: Mapped[list[StudentAssessment]] = relationship(back_populates="counselor")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    subject_combo: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    risk_preference: Mapped[str | None] = mapped_column(String(32), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    counselor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    counselor: Mapped[User] = relationship(back_populates="students")
    assessments: Mapped[list[StudentAssessment]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )


class StudentAssessment(Base):
    __tablename__ = "student_assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False, index=True)
    counselor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    answers_json: Mapped[str] = mapped_column(Text, nullable=False)
    answer_count: Mapped[int] = mapped_column(Integer, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    student: Mapped[Student] = relationship(back_populates="assessments")
    counselor: Mapped[User] = relationship(back_populates="student_assessments")


class ImportTask(Base):
    __tablename__ = "import_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded", index=True)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    success_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    creator: Mapped[User] = relationship(back_populates="import_tasks")
    admission_scores: Mapped[list[AdmissionScore]] = relationship(
        back_populates="import_task", cascade="all, delete-orphan"
    )
    import_row_errors: Mapped[list[ImportRowError]] = relationship(
        back_populates="import_task", cascade="all, delete-orphan"
    )


class AdmissionScore(Base):
    __tablename__ = "admission_scores"
    __table_args__ = (
        UniqueConstraint(
            "college_name",
            "major_name",
            "province",
            "year",
            name="uq_admission_score_college_major_province_year",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    college_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    major_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    province: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    min_score: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    min_rank: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    import_task_id: Mapped[int] = mapped_column(ForeignKey("import_tasks.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    import_task: Mapped[ImportTask] = relationship(back_populates="admission_scores")


class ImportRowError(Base):
    __tablename__ = "import_row_errors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    import_task_id: Mapped[int] = mapped_column(ForeignKey("import_tasks.id"), nullable=False, index=True)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    error_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_row_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    import_task: Mapped[ImportTask] = relationship(back_populates="import_row_errors")
