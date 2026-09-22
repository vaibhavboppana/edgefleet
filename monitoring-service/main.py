from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import HealthReportModel


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="EdgeFleet Monitoring Service",
    description="Health monitoring service for the EdgeFleet platform",
    version="1.0.0",
)


class HealthReportCreate(BaseModel):
    device_id: UUID
    status: Literal["ONLINE", "WARNING", "OFFLINE"]
    cpu_usage: float = Field(ge=0, le=100)
    memory_usage: float = Field(ge=0, le=100)


class HealthReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    device_id: UUID
    status: Literal["ONLINE", "WARNING", "OFFLINE"]
    cpu_usage: float
    memory_usage: float
    timestamp: datetime


@app.get("/health")
def health_check():
    return {
        "service": "monitoring-service",
        "status": "healthy",
    }


@app.post(
    "/health-reports",
    response_model=HealthReport,
    status_code=status.HTTP_201_CREATED,
)
def create_health_report(
    report_data: HealthReportCreate,
    db: Session = Depends(get_db),
):
    report = HealthReportModel(
        device_id=report_data.device_id,
        status=report_data.status,
        cpu_usage=report_data.cpu_usage,
        memory_usage=report_data.memory_usage,
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    return report


@app.get("/health-reports/{device_id}/latest", response_model=HealthReport)
def get_latest_health_report(
    device_id: UUID,
    db: Session = Depends(get_db),
):
    report = (
        db.query(HealthReportModel)
        .filter(HealthReportModel.device_id == device_id)
        .order_by(desc(HealthReportModel.timestamp))
        .first()
    )

    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No health reports found for device",
        )

    return report
