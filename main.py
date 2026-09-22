"""CLI: orquesta el flujo completo.

    python -m src.main --cliente NovaShop --fuente csv --destino archivo
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from .config import Config, ErrorDeConfiguracion
from .fuentes import FuenteCSV, FuenteGoogleSheets
from .gemini import ClienteGemini, ErrorDelModelo
from .metricas import ErrorDeDatos, construir_resumen
from .prompts import INSTRUCCION_SISTEMA, construir_prompt
from .salidas import DestinoArchivo, DestinoGoogleDocs

RAIZ = Path(__file__).resolve().parent.parent


def configurar_logs(verboso: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verboso else logging.INFO,
        format="%(levelname)-8s %(message)s",
    )


def parsear_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Genera un reporte estrategico de performance publicitaria con IA."
    )
    p.add_argument("--cliente", required=True, help="Nombre del cliente tal como aparece en los datos")
    p.add_argument("--fuente", choices=["csv", "sheets"], default="csv")
    p.add_argument("--destino", choices=["archivo", "docs"], default="archivo")
    p.add_argument("--csv", type=Path, default=RAIZ / "data" / "campanas_ejemplo.csv")
    p.add_argument("--mes", type=int, default=date.today().month, choices=range(1, 13))
    p.add_argument("--anio", type=int, default=date.today().year)
    p.add_argument("--solo-metricas", action="store_true",
                   help="Calcula e imprime las metricas sin llamar al modelo (no gasta API)")
    p.add_argument("-v", "--verboso", action="store_true")
    return p.parse_args(argv)


def imprimir_metricas(resumen) -> None:
    print(f"\n  Cliente: {resumen.cliente}")
    print(f"  Inversion total:   ${resumen.gasto_total:>12,.2f}")
    print(f"  Ingresos totales:  ${resumen.ingresos_total:>12,.2f}")
    print(f"  ROAS combinado:     {resumen.roas_combinado:>12.2f}")
    print(f"  CPA combinado:     ${resumen.cpa_combinado:>12.2f}")
    print(f"  Presupuesto en fuga:${resumen.fuga_estimada:>11,.2f}\n")
    print(f"  {'Campana':<32}{'Plataforma':<14}{'ROAS':>8}{'CPA':>10}  Estado")
    print("  " + "-" * 74)
    for c in sorted(resumen.campanas, key=lambda x: -x.roas):
        print(f"  {c.campana[:31]:<32}{c.plataforma[:13]:<14}"
              f"{c.roas:>8.2f}{c.cpa:>10.2f}  {c.semaforo}")
    print()


def main(argv: list[str] | None = None) -> int:
    args = parsear_argumentos(argv)
    configurar_logs(args.verboso)
    log = logging.getLogger("reporte")

    try:
        # 1. Leer los datos
        if args.fuente == "csv":
            fuente = FuenteCSV(args.csv)
        else:
            cfg = Config.desde_entorno()
            fuente = FuenteGoogleSheets(cfg.spreadsheet_id, cfg.sheet_name, cfg.credentials_file)

        log.info("Leyendo campanas de %s...", args.cliente)
        campanas = fuente.leer(args.cliente)
        log.info("%d campanas encontradas", len(campanas))

        # 2. Calcular metricas en Python, no en el modelo
        resumen = construir_resumen(args.cliente, campanas)
        imprimir_metricas(resumen)

        if args.solo_metricas:
            return 0

        # 3. Redaccion con el modelo
        cfg = Config.desde_entorno()
        log.info("Generando el reporte con %s...", cfg.gemini_model)
        modelo = ClienteGemini(cfg.gemini_api_key, cfg.gemini_model)
        html = modelo.generar_reporte(
            prompt=construir_prompt(resumen, args.mes, args.anio),
            instruccion_sistema=INSTRUCCION_SISTEMA,
        )

        # 4. Entrega
        if args.destino == "docs":
            destino = DestinoGoogleDocs(Config.desde_entorno().credentials_file)
        else:
            destino = DestinoArchivo(RAIZ / "salida")

        referencia = destino.guardar(html, f"Reporte Estrategico - {args.cliente}")
        print(f"\n  Listo: {referencia}\n")
        return 0

    except ErrorDeDatos as exc:
        log.error("Problema con los datos: %s", exc)
        return 2
    except ErrorDeConfiguracion as exc:
        log.error("Falta configuracion: %s", exc)
        return 3
    except ErrorDelModelo as exc:
        log.error("El modelo fallo: %s", exc)
        return 4
    except FileNotFoundError as exc:
        log.error("%s", exc)
        return 5
    except KeyboardInterrupt:
        log.warning("Cancelado por el usuario.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
