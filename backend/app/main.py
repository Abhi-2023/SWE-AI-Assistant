from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.database import get_db, init_db
from app.api.routes.auth import router as auth_router
from app.api.routes.repo import router as repo_router
from app.api.routes.chat import router as chat_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    
app = FastAPI(
    title="SWE AI Assistant",
    lifespan= lifespan
)

app.include_router(auth_router)
app.include_router(repo_router)
app.include_router(chat_router)

@app.get('health')
async def health():
    return {'status': 'healthy'}