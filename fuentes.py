"""Fuentes de datos: Google Sheets en produccion, CSV para desarrollo."""
from __future__ import annotations

import csv
from abc import ABC, abstractmethod
from pathlib import Path

from .metricas import Campana, ErrorDeDatos


class FuenteDeCampanas(ABC):
    """Interfaz comun. Permite desarrollar y testear sin tocar la red."""

    @abstractmethod
    def leer(self, cliente: str) -> list[Campana]:
        ...


def _normalizar(cabecera: str) -> str:
    """'Gasto (USD)' -> 'gasto'. Tolera acentos y mayusculas."""
    tabla = str.maketrans("áéíóúÁÉÍÓÚñÑ", "aeiouAEIOUnN")
    limpio = cabecera.translate(tabla).strip().lower()
    return limpio.split("(")[0].strip().replace(" ", "_")


def _filtrar(filas: list[dict], cliente: str, origen: str) -> list[Campana]:
    campanas = [
        Campana.desde_fila(fila, i)
        for i, fila in enumerate(filas, start=2)
        if str(fila.get("cliente", "")).strip().casefold() == cliente.casefold()
    ]
    if not campanas:
        disponibles = sorted({str(f.get("cliente", "")).strip() for f in filas} - {""})
        raise ErrorDeDatos(
            f"No hay filas para el cliente '{cliente}' en {origen}. "
            f"Clientes disponibles: {', '.join(disponibles) or 'ninguno'}."
        )
    return campanas


class FuenteCSV(FuenteDeCampanas):
    """Lee de un CSV local. Util para desarrollar sin credenciales."""

    def __init__(self, ruta: Path):
        self.ruta = Path(ruta)

    def leer(self, cliente: str) -> list[Campana]:
        if not self.ruta.exists():
            raise FileNotFoundError(f"No existe el archivo {self.ruta}")
        with self.ruta.open(encoding="utf-8") as f:
            lector = csv.DictReader(f)
            lector.fieldnames = [_normalizar(c) for c in (lector.fieldnames or [])]
            filas = list(lector)
        return _filtrar(filas, cliente, str(self.ruta))


class FuenteGoogleSheets(FuenteDeCampanas):
    """Lee de un Google Sheet mediante una cuenta de servicio.

    El import de gspread es perezoso: asi el proyecto corre en modo CSV
    sin necesidad de instalar las dependencias de Google.
    """

    ALCANCES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    def __init__(self, spreadsheet_id: str, sheet_name: str, credentials_file: Path):
        self.spreadsheet_id = spreadsheet_id
        self.sheet_name = sheet_name
        self.credentials_file = Path(credentials_file)

    def leer(self, cliente: str) -> list[Campana]:
        import gspread
        from google.oauth2.service_account import Credentials

        if not self.credentials_file.exists():
            raise FileNotFoundError(
                f"No se encontro {self.credentials_file}. Descarga el JSON de la "
                f"cuenta de servicio desde Google Cloud y comparte la hoja con su email."
            )

        credenciales = Credentials.from_service_account_file(
            str(self.credentials_file), scopes=self.ALCANCES
        )
        cliente_gs = gspread.authorize(credenciales)
        hoja = cliente_gs.open_by_key(self.spreadsheet_id).worksheet(self.sheet_name)

        filas_crudas = hoja.get_all_values()
        if len(filas_crudas) < 2:
            raise ErrorDeDatos("La hoja esta vacia o solo tiene cabecera.")

        cabeceras = [_normalizar(c) for c in filas_crudas[0]]
        filas = [dict(zip(cabeceras, fila)) for fila in filas_crudas[1:]]
        return _filtrar(filas, cliente, f"la hoja '{self.sheet_name}'")
