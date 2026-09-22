"""Destinos del reporte: archivo local o Google Docs."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)


class DestinoDelReporte(ABC):
    @abstractmethod
    def guardar(self, html: str, nombre: str) -> str:
        """Guarda el reporte y devuelve una referencia legible (ruta o URL)."""


class DestinoArchivo(DestinoDelReporte):
    """Escribe un .html local. Es el destino por defecto: sin credenciales,
    sin red, y lo abres en el navegador para ver el resultado."""

    def __init__(self, carpeta: Path):
        self.carpeta = Path(carpeta)
        self.carpeta.mkdir(parents=True, exist_ok=True)

    def guardar(self, html: str, nombre: str) -> str:
        marca = datetime.now().strftime("%Y%m%d-%H%M%S")
        seguro = "".join(c if c.isalnum() or c in "-_ " else "" for c in nombre).strip()
        ruta = self.carpeta / f"{seguro.replace(' ', '-')}-{marca}.html"
        ruta.write_text(html, encoding="utf-8")
        log.info("Reporte escrito en %s", ruta)
        return str(ruta)


class DestinoGoogleDocs(DestinoDelReporte):
    """Sube el HTML a Drive y deja que Google lo convierta a Documento.

    Truco: en vez de construir el documento con la API de Docs (que exige
    describir cada insercion de texto), se sube el HTML con mimeType
    text/html y se pide conversion a application/vnd.google-apps.document.
    Google respeta los estilos inline. Mucho menos codigo.
    """

    ALCANCES = ["https://www.googleapis.com/auth/drive.file"]

    def __init__(self, credentials_file: Path, carpeta_destino: str | None = None):
        self.credentials_file = Path(credentials_file)
        self.carpeta_destino = carpeta_destino

    def guardar(self, html: str, nombre: str) -> str:
        import io

        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload

        if not self.credentials_file.exists():
            raise FileNotFoundError(f"No se encontro {self.credentials_file}")

        credenciales = Credentials.from_service_account_file(
            str(self.credentials_file), scopes=self.ALCANCES
        )
        drive = build("drive", "v3", credentials=credenciales)

        metadatos = {
            "name": nombre,
            "mimeType": "application/vnd.google-apps.document",
        }
        if self.carpeta_destino:
            metadatos["parents"] = [self.carpeta_destino]

        medio = MediaIoBaseUpload(
            io.BytesIO(html.encode("utf-8")), mimetype="text/html", resumable=False
        )
        archivo = (
            drive.files()
            .create(body=metadatos, media_body=medio, fields="id,webViewLink")
            .execute()
        )
        enlace = archivo.get("webViewLink", archivo["id"])
        log.info("Documento creado: %s", enlace)
        return enlace
