import os
from datetime import datetime
from pathlib import Path
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from database import Base, engine, get_db
from models import DeviceModel


Base.metadata.create_all(bind=engine)

MONITORING_SERVICE_URL = os.getenv(
    "MONITORING_SERVICE_URL",
    "http://127.0.0.1:8001",
)


app = FastAPI(
    title="EdgeFleet Device Service",
    description="Device management service for the EdgeFleet platform",
    version="1.0.0",
)


STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(STATIC_DIR / "index.html")


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: str = Field(min_length=1, max_length=50)
    location: str = Field(min_length=1, max_length=100)
    software_version: str = Field(min_length=1, max_length=50)
    ip_address: str = Field(min_length=1, max_length=45)


class Device(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: str
    location: str
    software_version: str
    ip_address: str
    created_at: datetime


@app.get("/health")
def health_check():
    return {
        "service": "device-service",
        "status": "healthy",
    }


@app.post(
    "/devices",
    response_model=Device,
    status_code=status.HTTP_201_CREATED,
)
def create_device(
    device_data: DeviceCreate,
    db: Session = Depends(get_db),
):
    device = DeviceModel(
        name=device_data.name,
        type=device_data.type,
        location=device_data.location,
        software_version=device_data.software_version,
        ip_address=device_data.ip_address,
    )

    db.add(device)
    db.commit()
    db.refresh(device)

    return device


@app.get("/devices", response_model=list[Device])
def get_devices(db: Session = Depends(get_db)):
    return db.query(DeviceModel).all()


@app.get("/devices/{device_id}", response_model=Device)
def get_device(
    device_id: UUID,
    db: Session = Depends(get_db),
):
    device = db.get(DeviceModel, device_id)

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    return device


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: str | None = Field(default=None, min_length=1, max_length=50)
    location: str | None = Field(default=None, min_length=1, max_length=100)
    software_version: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )
    ip_address: str | None = Field(default=None, min_length=1, max_length=45)


@app.put("/devices/{device_id}", response_model=Device)
def update_device(
    device_id: UUID,
    device_data: DeviceUpdate,
    db: Session = Depends(get_db),
):
    device = db.get(DeviceModel, device_id)

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    update_data = device_data.model_dump(exclude_unset=True)

    if any(value is None for value in update_data.values()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Device fields cannot be null",
        )

    for field, value in update_data.items():
        setattr(device, field, value)

    db.commit()
    db.refresh(device)

    return device


@app.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device_id: UUID,
    db: Session = Depends(get_db),
):
    device = db.get(DeviceModel, device_id)

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    db.delete(device)
    db.commit()


@app.get("/devices/{device_id}/details")
def get_device_details(
    device_id: UUID,
    db: Session = Depends(get_db),
):
    device = db.get(DeviceModel, device_id)

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    monitoring_url = (
        f"{MONITORING_SERVICE_URL}/health-reports/{device_id}/latest"
    )

    try:
        response = httpx.get(monitoring_url, timeout=5.0)
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Monitoring service unavailable",
        )

    if response.status_code == status.HTTP_404_NOT_FOUND:
        health = None
    elif response.is_success:
        try:
            health = response.json()
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Monitoring service returned invalid JSON",
            ) from exc
    else:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Monitoring service returned an unexpected response",
        )

    return {
        "device": Device.model_validate(device),
        "health": health,
    }
