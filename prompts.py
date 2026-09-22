"""Construccion del prompt.

El modelo recibe metricas YA CALCULADAS y solo redacta. Eso reduce
alucinaciones numericas a casi cero y hace el resultado reproducible.
"""
from __future__ import annotations

from .metricas import Resumen

MESES = {
    1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
    7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre",
    12: "diciembre",
}

INSTRUCCION_SISTEMA = """\
Eres un consultor senior de marketing de performance que redacta reportes \
ejecutivos.

Reglas inquebrantables:
1. Devuelves UNICAMENTE HTML valido, desde <html> hasta </html>. Nunca markdown, \
nunca bloques de codigo, nunca texto fuera del HTML.
2. Usas EXCLUSIVAMENTE los numeros que se te entregan. No calculas, no estimas, \
no inventas. Los ROAS y CPA ya vienen calculados: copialos.
3. Todos los estilos van inline (style="..."), porque el HTML se importa a \
Google Docs y no soporta hojas de estilo externas.
4. Todo el texto en espanol, sin tildes en los atributos HTML.
5. Los importes se escriben como $1,234 USD.
"""


def _tabla_de_campanas(resumen: Resumen) -> str:
    lineas = []
    for c in resumen.campanas:
        lineas.append(
            f"- {c.campana} | {c.plataforma} | gasto ${c.gasto:,.0f} | "
            f"ingresos ${c.ingresos:,.0f} | ROAS {c.roas:.2f} | "
            f"CPA ${c.cpa:,.2f} | conversiones {c.conversiones:.0f} | "
            f"CTR {c.ctr:.2%} | semaforo {c.semaforo}"
        )
    return "\n".join(lineas)


def construir_prompt(resumen: Resumen, mes: int, anio: int) -> str:
    periodo = f"{MESES[mes]} {anio}"
    ganadoras = ", ".join(c.campana for c in resumen.ganadoras) or "ninguna"
    perdedoras = ", ".join(c.campana for c in resumen.perdedoras) or "ninguna"

    return f"""\
Genera el reporte mensual de {resumen.cliente} para el periodo {periodo}.

DATOS YA CALCULADOS (no recalcules nada):
- Inversion total: ${resumen.gasto_total:,.0f} USD
- Ingresos totales: ${resumen.ingresos_total:,.0f} USD
- ROAS combinado: {resumen.roas_combinado:.2f}
- Conversiones totales: {resumen.conversiones_total:.0f}
- CPA combinado: ${resumen.cpa_combinado:,.2f}
- Presupuesto en campanas con ROAS bajo 2: ${resumen.fuga_estimada:,.0f} USD
- Campanas ganadoras (ROAS >= 4): {ganadoras}
- Campanas ineficientes (ROAS < 2): {perdedoras}

DETALLE POR CAMPANA:
{_tabla_de_campanas(resumen)}

ESTRUCTURA EXACTA DEL HTML:

1) BANNER: tabla ancho 100%, celda con fondo #1F3A5F y padding 20px. Dentro:
   "Reporte Estrategico de Performance" en blanco, 24px, negrita. Debajo, en
   #AFC4E6 12px: nombre del cliente, periodo ({periodo}) y "Preparado por
   AI Automation Architect", separados por el caracter ·.

2) TARJETAS KPI: tabla ancho 100%, una fila con 3 celdas centradas, fondo
   #EEF3FB, padding 16px, separadas por borde blanco. Cada celda: etiqueta en
   11px gris #5A6472 y valor en 22px negrita. Celdas: INVERSION (#1F3A5F),
   INGRESOS (#1F3A5F), ROAS COMBINADO (#1B8A5A).

3) CALLOUT: tabla ancho 100%, celda fondo #FFF6E5 con borde izquierdo 4px
   solido #E0A800 y padding 14px. Texto: "Hallazgo principal:" en negrita mas
   el insight mas relevante, con la cifra clave en negrita #1B8A5A.

4) Titulo "Resumen de campanas" (15px negrita #1F3A5F) y tabla ancho 100% con
   cabecera fondo #1F3A5F y texto blanco. Columnas: Campana, Plataforma, Gasto,
   Ingresos, ROAS, Estado. Filas alternas con fondo #F7FAFF. La celda ROAS en
   negrita y coloreada segun el semaforo indicado arriba: verde #1B8A5A,
   ambar #B8860B, rojo #C0392B. En Estado usa el caracter ● con ese mismo color,
   sin emojis.

5) "1. Resumen ejecutivo" (15px negrita #1F3A5F): un parrafo con inversion,
   ingresos, ROAS combinado y un veredicto claro.

6) "2. Lo que esta funcionando" (15px negrita #1B8A5A): lista de las ganadoras
   con su ROAS y CPA, y por que funcionan.

7) "3. Donde se esta fugando el presupuesto" (15px negrita #C0392B): lista de
   las ineficientes con su gasto y el costo de oportunidad en dolares.

8) "4. Plan de accion" (15px negrita #1F3A5F): tres bloques en celdas de tabla
   ancho 100%. Alta prioridad: fondo #FBEAEA, borde izq #C0392B. Media: fondo
   #FFF6E5, borde izq #E0A800. Baja: fondo #E7F5EE, borde izq #1B8A5A. Cada uno
   con la accion en negrita, una linea de justificacion, e "Impacto estimado:"
   con el monto en negrita #1B8A5A.

9) Linea horizontal y pie en gris #9AA3AF 10px: "Reporte generado
   automaticamente con IA a partir de los datos de campanas."
"""
