import os
import logging
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from config import WEBAPP_CORS_ORIGINS
from .auth import validate_webapp_init_data
from .routers import announcements, dashboard

app = FastAPI(title="Tenir-Too Web Bridge")
logger = logging.getLogger("web")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return HTTPException(status_code=500, detail="Internal Server Error")

# Настройка CORS [PL-2.1]
app.add_middleware(
    CORSMiddleware,
    allow_origins=WEBAPP_CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

app.include_router(announcements.router, prefix="/api/announcements", tags=["Announcements"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

# Раздача статики [PL-2.1] - В самом конце, чтобы не перехватывать API роуты
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")
