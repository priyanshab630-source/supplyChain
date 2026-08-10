from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.routers.chat import router as chat_router
from backend.routers.admin import router as admin_router



app = FastAPI(title="Supply Chain Multi-Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)


@app.on_event("startup")
def on_startup():
    init_db()


app.include_router(chat_router)


@app.get("/health")
def health():
    return {"status": "ok"}
