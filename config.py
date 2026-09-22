"""Configuracion centralizada, leida desde variables de entorno."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

RAIZ = Path(__file__).resolve().parent.parent


class ErrorDeConfiguracion(RuntimeError):
    """Falta una variable de entorno obligatoria."""


def _requerido(clave: str) -> str:
    valor = os.getenv(clave, "").strip()
    if not valor:
        raise ErrorDeConfiguracion(
            f"Falta la variable de entorno {clave}. "
            f"Copia .env.example a .env y complétala."
        )
    return valor


@dataclass(frozen=True)
class Config:
    gemini_api_key: str
    gemini_model: str
    spreadsheet_id: str
    sheet_name: str
    credentials_file: Path

    @classmethod
    def desde_entorno(cls) -> "Config":
        return cls(
            gemini_api_key=_requerido("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            spreadsheet_id=_requerido("SPREADSHEET_ID"),
            sheet_name=os.getenv("SHEET_NAME", "Campanas"),
            credentials_file=RAIZ / os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
        )
