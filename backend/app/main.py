import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.main_router import router
from app.config import settings
from app.db.session import Base, SessionLocal, engine
from app.services import mqtt_service
from app.seed import demo_data

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="EIR Medichat API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def on_startup():
    import app.models.entities  # noqa: F401

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        demo_data.run_seed(db)
    finally:
        db.close()
    mqtt_service.start_mqtt_background()
