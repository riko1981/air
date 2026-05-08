import os
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from db import AirQualityDB

load_dotenv()

app = FastAPI(title="Air Monitoring API - Kazakhstan", description="API для приема данных с квадрокоптера в Казахстане")

# Модель данных
class Measurement(BaseModel):
    city: Optional[str] = Field(default="Неизвестно", max_length=100)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: Optional[float] = Field(default=0, ge=0)
    co2_ppm: float = Field(..., ge=0)
    co_ppm: float = Field(..., ge=0)
    pm25: float = Field(..., ge=0)
    pm10: float = Field(..., ge=0)
    temperature_celsius: float = Field(..., ge=-80, le=80)
    humidity_percent: float = Field(..., ge=0, le=100)
    battery_level: Optional[float] = Field(default=100, ge=0, le=100)
    drone_status: Optional[str] = "active"


def measurement_to_dict(measurement: Measurement):
    if hasattr(measurement, "model_dump"):
        return measurement.model_dump()
    return measurement.dict()

@app.get("/")
def root():
    return {"message": "Air Monitoring API - Kazakhstan работает!", "status": "online", "location": "Kazakhstan"}

@app.post("/api/measurements")
async def add_measurement(measurement: Measurement):
    """Прием данных с квадрокоптера"""
    try:
        with AirQualityDB() as db:
            db.insert_measurement(measurement_to_dict(measurement))
        return {
            "status": "success",
            "message": "Data saved to Kazakhstan database",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/measurements")
async def get_measurements(limit: int = Query(default=100, ge=1, le=1000)):
    """Получение последних измерений"""
    try:
        with AirQualityDB() as db:
            df = db.get_all_measurements(limit)
        return df.to_dict(orient="records")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/measurements/latest")
async def get_latest():
    """Получение последнего измерения"""
    try:
        with AirQualityDB() as db:
            latest = db.get_latest_measurement()
        if latest:
            return latest
        return {"message": "No data yet"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/statistics")
async def get_statistics():
    """Получение статистики"""
    try:
        with AirQualityDB() as db:
            stats = db.get_statistics()
        return stats.to_dict(orient="records")[0] if not stats.empty else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("AIR_API_HOST", "127.0.0.1")
    port = int(os.getenv("AIR_API_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
