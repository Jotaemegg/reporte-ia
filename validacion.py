"""Validacion de la respuesta del modelo.

Esto es lo que Make te oculta: una API puede devolverte cualquier cosa.
Antes de meter el resultado en un documento del cliente, se verifica.
"""
from __future__ import annotations

import re


class RespuestaInvalida(ValueError):
    """El modelo devolvio algo que no sirve como reporte."""


# Secciones que el reporte DEBE contener. Si falta una, el modelo se desvio.
SECCIONES_OBLIGATORIAS = (
    "Resumen ejecutivo",
    "Lo que esta funcionando",
    "fugando el presupuesto",
    "Plan de accion",
)

_VALLA_MARKDOWN = re.compile(r"^\s*```(?:html)?\s*|\s*```\s*$", re.IGNORECASE)


def limpiar_html(texto: str) -> str:
    """Quita las vallas de markdown que el modelo a veces añade igual."""
    limpio = _VALLA_MARKDOWN.sub("", texto.strip())
    inicio = limpio.lower().find("<html")
    if inicio > 0:
        limpio = limpio[inicio:]
    fin = limpio.lower().rfind("</html>")
    if fin != -1:
        limpio = limpio[: fin + len("</html>")]
    return limpio.strip()


def validar_reporte(html: str, longitud_minima: int = 800) -> str:
    """Devuelve el HTML limpio o lanza RespuestaInvalida con el motivo."""
    if not html or not html.strip():
        raise RespuestaInvalida("El modelo devolvio una respuesta vacia.")

    limpio = limpiar_html(html)

    if not limpio.lower().startswith("<html"):
        raise RespuestaInvalida(
            f"La respuesta no empieza con <html>. Empieza con: {limpio[:80]!r}"
        )
    if "</html>" not in limpio.lower():
        raise RespuestaInvalida("La respuesta esta truncada: falta </html>.")
    if len(limpio) < longitud_minima:
        raise RespuestaInvalida(
            f"El reporte tiene {len(limpio)} caracteres, menos del minimo "
            f"razonable ({longitud_minima}). Probablemente esta incompleto."
        )

    faltantes = [s for s in SECCIONES_OBLIGATORIAS if s.lower() not in limpio.lower()]
    if faltantes:
        raise RespuestaInvalida(
            f"Al reporte le faltan secciones obligatorias: {', '.join(faltantes)}."
        )

    return limpio
