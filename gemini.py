"""Cliente de Gemini con reintentos, backoff y validacion de salida."""
from __future__ import annotations

import logging
import random
import time
from typing import Callable

from .validacion import RespuestaInvalida, validar_reporte

log = logging.getLogger(__name__)


class ErrorDelModelo(RuntimeError):
    """El modelo no produjo un reporte utilizable tras todos los intentos."""


# Errores que tiene sentido reintentar: la red falla, el servicio se satura.
# Un 400 por prompt malformado no se reintenta: fallaria igual las 3 veces.
_REINTENTABLES = ("429", "500", "502", "503", "504", "timeout", "deadline", "unavailable")


def _vale_la_pena_reintentar(exc: Exception) -> bool:
    mensaje = str(exc).lower()
    return any(marca in mensaje for marca in _REINTENTABLES)


def con_reintentos(
    operacion: Callable[[], str],
    intentos: int = 3,
    espera_base: float = 2.0,
) -> str:
    """Ejecuta `operacion` con backoff exponencial y jitter.

    El jitter (el random) evita que varios procesos reintenten a la vez
    y vuelvan a tumbar el servicio. Se llama thundering herd.
    """
    ultimo_error: Exception | None = None

    for intento in range(1, intentos + 1):
        try:
            return operacion()
        except RespuestaInvalida as exc:
            # El modelo respondio, pero mal. Reintentar tiene sentido:
            # la generacion es estocastica.
            ultimo_error = exc
            log.warning("Intento %d/%d: respuesta invalida (%s)", intento, intentos, exc)
        except Exception as exc:
            ultimo_error = exc
            if not _vale_la_pena_reintentar(exc):
                raise ErrorDelModelo(f"Error no recuperable: {exc}") from exc
            log.warning("Intento %d/%d: error transitorio (%s)", intento, intentos, exc)

        if intento < intentos:
            espera = espera_base * (2 ** (intento - 1)) + random.uniform(0, 1)
            log.info("Reintentando en %.1fs", espera)
            time.sleep(espera)

    raise ErrorDelModelo(
        f"Fallaron los {intentos} intentos. Ultimo error: {ultimo_error}"
    )


class ClienteGemini:
    def __init__(self, api_key: str, modelo: str = "gemini-2.5-flash"):
        from google import genai

        self._genai = genai
        self.cliente = genai.Client(api_key=api_key)
        self.modelo = modelo

    def generar_reporte(
        self,
        prompt: str,
        instruccion_sistema: str,
        temperatura: float = 0.3,
        max_tokens: int = 8192,
    ) -> str:
        """Genera el reporte y garantiza que el HTML devuelto es valido."""
        from google.genai import types

        def _una_llamada() -> str:
            respuesta = self.cliente.models.generate_content(
                model=self.modelo,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=instruccion_sistema,
                    temperature=temperatura,
                    max_output_tokens=max_tokens,
                ),
            )
            texto = getattr(respuesta, "text", None)
            if not texto:
                raise RespuestaInvalida(
                    "La API respondio sin texto (posible bloqueo por filtros de seguridad)."
                )
            return validar_reporte(texto)

        return con_reintentos(_una_llamada)
