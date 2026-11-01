from fastapi import FastAPI
from sqlalchemy import text
from app.api.routes.market_data import router as market_data_router

from app.database.connection import engine
from app.api.routes.historical import router as historical_router

app = FastAPI(
    title="D_O_D AI Options Trading Intelligence",
    version="1.0.0",
)

app.include_router(historical_router)
app.include_router(market_data_router)

@app.get("/")
def root():
    return {
        "message": "D_O_D backend is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


@app.get("/health/database")
def database_health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected"
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }



