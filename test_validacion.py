import pytest

from src.validacion import RespuestaInvalida, limpiar_html, validar_reporte

RELLENO = "<p>" + ("contenido de relleno " * 60) + "</p>"

REPORTE_OK = (
    "<html><body>"
    "<h2>1. Resumen ejecutivo</h2>"
    "<h2>2. Lo que esta funcionando</h2>"
    "<h2>3. Donde se esta fugando el presupuesto</h2>"
    "<h2>4. Plan de accion</h2>"
    + RELLENO +
    "</body></html>"
)


class TestLimpieza:
    def test_quita_valla_de_markdown(self):
        sucio = "```html\n<html><body>hola</body></html>\n```"
        assert limpiar_html(sucio) == "<html><body>hola</body></html>"

    def test_quita_texto_previo_del_modelo(self):
        sucio = "Claro, aqui tienes el reporte:\n<html><body>x</body></html>"
        assert limpiar_html(sucio).startswith("<html")

    def test_quita_texto_posterior(self):
        sucio = "<html><body>x</body></html>\n\nEspero que te sirva!"
        assert limpiar_html(sucio).endswith("</html>")


class TestValidacion:
    def test_reporte_completo_pasa(self):
        assert validar_reporte(REPORTE_OK).startswith("<html")

    def test_vacio_falla(self):
        with pytest.raises(RespuestaInvalida, match="vacia"):
            validar_reporte("")

    def test_truncado_falla(self):
        with pytest.raises(RespuestaInvalida, match="truncada"):
            validar_reporte("<html><body>" + RELLENO)

    def test_demasiado_corto_falla(self):
        with pytest.raises(RespuestaInvalida, match="caracteres"):
            validar_reporte("<html><body>ok</body></html>")

    def test_seccion_faltante_se_reporta_por_nombre(self):
        sin_plan = REPORTE_OK.replace("4. Plan de accion", "4. Otra cosa")
        with pytest.raises(RespuestaInvalida, match="Plan de accion"):
            validar_reporte(sin_plan)

    def test_markdown_en_vez_de_html_falla(self):
        with pytest.raises(RespuestaInvalida, match="no empieza"):
            validar_reporte("# Reporte\n\nAqui van las metricas..." * 30)
