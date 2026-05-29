from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.database import get_db, init_db
from app.api.routes.auth import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    
app = FastAPI(
    title="SWE AI Assistant",
    lifespan= lifespan
)

app.include_router(auth_router)

@app.get('health')
async def health():
    return {'status': 'healthy'}