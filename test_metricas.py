import pytest

from src.metricas import Campana, ErrorDeDatos, construir_resumen


def campana(**kwargs) -> Campana:
    base = dict(
        cliente="ACME", campana="Test", plataforma="Meta Ads",
        gasto=100.0, impresiones=10000.0, clics=500.0,
        conversiones=10.0, ingresos=500.0,
    )
    base.update(kwargs)
    return Campana(**base)


class TestCampana:
    def test_roas(self):
        assert campana(gasto=100, ingresos=500).roas == 5.0

    def test_roas_con_gasto_cero_no_explota(self):
        # Division por cero: el caso que rompe el 90% de los scripts caseros
        assert campana(gasto=0, ingresos=500).roas == 0.0

    def test_cpa_sin_conversiones_no_explota(self):
        assert campana(conversiones=0).cpa == 0.0

    @pytest.mark.parametrize("ingresos,esperado", [
        (500, "verde"),   # ROAS 5
        (400, "verde"),   # ROAS 4, justo en el limite
        (300, "ambar"),   # ROAS 3
        (200, "ambar"),   # ROAS 2, limite inferior
        (199, "rojo"),    # ROAS 1.99
    ])
    def test_semaforo_en_los_limites(self, ingresos, esperado):
        assert campana(gasto=100, ingresos=ingresos).semaforo == esperado


class TestParseoDeFilas:
    def test_acepta_formato_de_hoja_de_calculo(self):
        fila = {
            "cliente": " ACME ", "campana": "Black Friday", "plataforma": "Meta Ads",
            "gasto": "$1,200.00", "impresiones": "145,000", "clics": "3800",
            "conversiones": "190", "ingresos": "$7,800.00",
        }
        c = Campana.desde_fila(fila, 2)
        assert c.cliente == "ACME"
        assert c.gasto == 1200.0
        assert c.ingresos == 7800.0

    def test_celda_vacia_es_cero(self):
        fila = {
            "cliente": "ACME", "campana": "X", "plataforma": "Y",
            "gasto": "100", "impresiones": "", "clics": "", 
            "conversiones": "", "ingresos": "50",
        }
        assert Campana.desde_fila(fila, 2).conversiones == 0.0

    def test_texto_basura_da_error_con_numero_de_fila(self):
        fila = {
            "cliente": "ACME", "campana": "X", "plataforma": "Y",
            "gasto": "pendiente", "impresiones": "1", "clics": "1",
            "conversiones": "1", "ingresos": "1",
        }
        with pytest.raises(ErrorDeDatos, match="Fila 7"):
            Campana.desde_fila(fila, 7)

    def test_negativos_rechazados(self):
        fila = {
            "cliente": "ACME", "campana": "X", "plataforma": "Y",
            "gasto": "-100", "impresiones": "1", "clics": "1",
            "conversiones": "1", "ingresos": "1",
        }
        with pytest.raises(ErrorDeDatos, match="negativo"):
            Campana.desde_fila(fila, 3)

    def test_columna_faltante(self):
        with pytest.raises(ErrorDeDatos, match="ingresos"):
            Campana.desde_fila({"cliente": "ACME"}, 2)


class TestResumen:
    def test_agregados(self):
        r = construir_resumen("ACME", [
            campana(gasto=100, ingresos=500, conversiones=10),
            campana(gasto=300, ingresos=300, conversiones=5),
        ])
        assert r.gasto_total == 400
        assert r.ingresos_total == 800
        assert r.roas_combinado == 2.0
        assert r.cpa_combinado == pytest.approx(26.666, rel=1e-3)

    def test_clasificacion(self):
        buena = campana(campana="Buena", gasto=100, ingresos=600)
        mala = campana(campana="Mala", gasto=200, ingresos=100)
        r = construir_resumen("ACME", [buena, mala])
        assert [c.campana for c in r.ganadoras] == ["Buena"]
        assert [c.campana for c in r.perdedoras] == ["Mala"]
        assert r.fuga_estimada == 200

    def test_sin_campanas_es_error(self):
        with pytest.raises(ErrorDeDatos):
            construir_resumen("Fantasma", [])
