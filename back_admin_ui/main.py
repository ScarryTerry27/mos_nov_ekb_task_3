from typing import Dict

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from handlers.auth import router as auth_router
from handlers.checks import router as checks_router
from handlers.documents import router as documents_router
from handlers.incidents import router as incidents_router
from handlers.materials import router as materials_router
from handlers.objects import router as objects_router
from handlers.subobjects import router as subobjects_router
from handlers.users import router as users_router
from services.db.db import create_tables

create_tables()

app = FastAPI(title="User Service API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth_router)
app.include_router(objects_router)
app.include_router(subobjects_router)
app.include_router(checks_router)
app.include_router(incidents_router)
app.include_router(documents_router)
app.include_router(materials_router)
app.include_router(users_router)


@app.get("/")
def read_root() -> Dict[str, str]:
    return {"status": "ok"}
