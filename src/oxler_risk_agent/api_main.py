from __future__ import annotations
from fastapi.middleware.cors import CORSMiddleware
from .api import build_app

app = build_app()

# Inyectamos el CORS a la aplicación ya construida
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permite conexiones desde Lovable
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
