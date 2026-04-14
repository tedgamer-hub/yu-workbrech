from fastapi import FastAPI
from sqlalchemy import select

from app.api.assessments import router as assessments_router
from app.api.auth import router as auth_router
from app.api.imports import router as imports_router
from app.api.recommendations import router as recommendations_router
from app.api.reports import router as reports_router
from app.api.students import router as students_router
from app.database import Base, SessionLocal, engine
from app.models import User
from app.security import hash_password

app = FastAPI(title="Gaokao Workbench API", version="0.2.0")


def _bootstrap_admin_user() -> None:
    with SessionLocal() as db:
        existing_admin = db.scalar(select(User).where(User.username == "admin"))
        if existing_admin is not None:
            return

        db.add(
            User(
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin",
                is_active=True,
            )
        )
        db.commit()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    _bootstrap_admin_user()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(students_router, prefix="/api/students", tags=["students"])
app.include_router(assessments_router, prefix="/api/assessments", tags=["assessments"])
app.include_router(imports_router, prefix="/api/imports", tags=["imports"])
app.include_router(recommendations_router, prefix="/api/recommendations", tags=["recommendations"])
app.include_router(reports_router, prefix="/api/reports", tags=["reports"])
