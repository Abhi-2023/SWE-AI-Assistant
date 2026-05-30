from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.routes.auth import router as auth_router
from app.api.routes.repo import router as repos_router
from app.api.routes.chat import router as chat_router
from app.api.routes.webhook import router as webhook_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title   = "Synthr — SWE AI Assistant",
    version = "0.1.0",
    lifespan = lifespan,
)

# ✅ CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

app.include_router(auth_router)
app.include_router(repos_router)
app.include_router(chat_router)
app.include_router(webhook_router)


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {
        "app":     "Synthr — SWE AI Assistant",
        "version": "0.1.0",
        "docs":    "/docs",
        "health":  "/health",
    }