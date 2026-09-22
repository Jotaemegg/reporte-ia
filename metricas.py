"""Modelo de datos y calculo de metricas.

Regla de diseño: TODA la aritmetica sobre dinero se hace aqui, en Python.
El modelo de lenguaje nunca calcula: solo redacta a partir de numeros ya
calculados. Un LLM que suma columnas es un bug esperando a ocurrir.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


class ErrorDeDatos(ValueError):
    """Una fila de la hoja no tiene el formato esperado."""


COLUMNAS_REQUERIDAS = (
    "cliente", "campana", "plataforma",
    "gasto", "impresiones", "clics", "conversiones", "ingresos",
)


def _a_numero(valor: object, campo: str, fila: int) -> float:
    """Convierte un valor de hoja de calculo a float.

    Tolera '$1,200.00', ' 1200 ', '1.200,00' no (ambiguo: se rechaza),
    y celdas vacias -> 0.
    """
    if valor is None:
        return 0.0
    texto = str(valor).strip()
    if not texto:
        return 0.0
    texto = texto.replace("$", "").replace(" ", "").replace(",", "")
    try:
        numero = float(texto)
    except ValueError as exc:
        raise ErrorDeDatos(
            f"Fila {fila}: el campo '{campo}' vale {valor!r} y no es un numero."
        ) from exc
    if numero < 0:
        raise ErrorDeDatos(f"Fila {fila}: el campo '{campo}' es negativo ({numero}).")
    return numero


@dataclass(frozen=True)
class Campana:
    cliente: str
    campana: str
    plataforma: str
    gasto: float
    impresiones: float
    clics: float
    conversiones: float
    ingresos: float

    @property
    def roas(self) -> float:
        """Retorno sobre inversion publicitaria. Gasto 0 -> 0, no infinito."""
        return self.ingresos / self.gasto if self.gasto else 0.0

    @property
    def cpa(self) -> float:
        """Costo por adquisicion. Sin conversiones el CPA no existe -> 0."""
        return self.gasto / self.conversiones if self.conversiones else 0.0

    @property
    def ctr(self) -> float:
        return self.clics / self.impresiones if self.impresiones else 0.0

    @property
    def semaforo(self) -> str:
        if self.roas >= 4:
            return "verde"
        if self.roas >= 2:
            return "ambar"
        return "rojo"

    @classmethod
    def desde_fila(cls, fila: dict, numero_fila: int) -> "Campana":
        faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in fila]
        if faltantes:
            raise ErrorDeDatos(
                f"Fila {numero_fila}: faltan las columnas {', '.join(faltantes)}."
            )
        return cls(
            cliente=str(fila["cliente"]).strip(),
            campana=str(fila["campana"]).strip(),
            plataforma=str(fila["plataforma"]).strip(),
            gasto=_a_numero(fila["gasto"], "gasto", numero_fila),
            impresiones=_a_numero(fila["impresiones"], "impresiones", numero_fila),
            clics=_a_numero(fila["clics"], "clics", numero_fila),
            conversiones=_a_numero(fila["conversiones"], "conversiones", numero_fila),
            ingresos=_a_numero(fila["ingresos"], "ingresos", numero_fila),
        )


@dataclass(frozen=True)
class Resumen:
    cliente: str
    campanas: Sequence[Campana]
    gasto_total: float
    ingresos_total: float
    conversiones_total: float
    roas_combinado: float

    @property
    def cpa_combinado(self) -> float:
        return self.gasto_total / self.conversiones_total if self.conversiones_total else 0.0

    @property
    def ganadoras(self) -> list[Campana]:
        return sorted([c for c in self.campanas if c.roas >= 4], key=lambda c: -c.roas)

    @property
    def perdedoras(self) -> list[Campana]:
        return sorted([c for c in self.campanas if c.roas < 2], key=lambda c: c.roas)

    @property
    def fuga_estimada(self) -> float:
        """Gasto de las campanas bajo ROAS 2: presupuesto reasignable."""
        return sum(c.gasto for c in self.perdedoras)


def construir_resumen(cliente: str, campanas: Iterable[Campana]) -> Resumen:
    lista = list(campanas)
    if not lista:
        raise ErrorDeDatos(f"No hay campanas para el cliente '{cliente}'.")

    gasto = sum(c.gasto for c in lista)
    ingresos = sum(c.ingresos for c in lista)
    conversiones = sum(c.conversiones for c in lista)

    # Usa el nombre tal como esta escrito en los datos, no como lo tipeo
    # el usuario en la CLI ("andina foods" -> "Andina Foods").
    return Resumen(
        cliente=lista[0].cliente or cliente,
        campanas=lista,
        gasto_total=gasto,
        ingresos_total=ingresos,
        conversiones_total=conversiones,
        roas_combinado=ingresos / gasto if gasto else 0.0,
    )
