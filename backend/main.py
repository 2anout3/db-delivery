from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routers import admin, auth, clients, couriers, deliveries, history, reference


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Delivery Service API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(clients.router)
app.include_router(deliveries.router)
app.include_router(couriers.router)
app.include_router(history.router)
app.include_router(reference.router)

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/static/pages/login.html")


@app.get("/health", tags=["health"])
def healthcheck():
    return {"status": "ok"}
