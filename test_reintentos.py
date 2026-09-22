import pytest

from src.gemini import ErrorDelModelo, con_reintentos
from src.validacion import RespuestaInvalida


def test_exito_al_primer_intento_no_reintenta():
    llamadas = []

    def op():
        llamadas.append(1)
        return "ok"

    assert con_reintentos(op, espera_base=0) == "ok"
    assert len(llamadas) == 1


def test_reintenta_tras_respuesta_invalida_y_acierta():
    llamadas = []

    def op():
        llamadas.append(1)
        if len(llamadas) < 3:
            raise RespuestaInvalida("truncado")
        return "ok"

    assert con_reintentos(op, espera_base=0) == "ok"
    assert len(llamadas) == 3


def test_error_429_se_reintenta():
    llamadas = []

    def op():
        llamadas.append(1)
        if len(llamadas) == 1:
            raise RuntimeError("429 RESOURCE_EXHAUSTED")
        return "ok"

    assert con_reintentos(op, espera_base=0) == "ok"


def test_error_de_autenticacion_no_se_reintenta():
    # Un 401 fallaria igual las 3 veces: reintentar solo quema tiempo
    llamadas = []

    def op():
        llamadas.append(1)
        raise RuntimeError("401 API key invalida")

    with pytest.raises(ErrorDelModelo, match="no recuperable"):
        con_reintentos(op, espera_base=0)
    assert len(llamadas) == 1


def test_agota_intentos_y_reporta_el_ultimo_error():
    def op():
        raise RespuestaInvalida("sigue truncado")

    with pytest.raises(ErrorDelModelo, match="sigue truncado"):
        con_reintentos(op, intentos=3, espera_base=0)
