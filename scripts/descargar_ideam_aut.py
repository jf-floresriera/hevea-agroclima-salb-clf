"""Descarga HR y temperatura subhorarias de estaciones automáticas IDEAM (datos.gov.co, API Socrata)
y las agrega a valores horarios.

Uso:  python scripts/descargar_ideam_aut.py
"""
import io

import pandas as pd
import requests

from config import CRUDOS

DATASETS = {"hr": "uext-mhny", "t": "sbwg-7ju4"}  # Humedad del aire 2 m / Temp Aire 2 m
ESTACIONES = {"palomera": "0035185010", "libertad": "0035025110"}
URL = "https://www.datos.gov.co/resource/{ds}.csv"
LOTE = 50000


def descargar(ds, codigo):
    partes, offset = [], 0
    while True:
        params = {"$select": "fechaobservacion,valorobservado", "$where": f"codigoestacion='{codigo}'",
                  "$order": "fechaobservacion", "$limit": LOTE, "$offset": offset}
        r = requests.get(URL.format(ds=ds), params=params, timeout=600)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        partes.append(df)
        if len(df) < LOTE:
            break
        offset += LOTE
    d = pd.concat(partes)
    d["fecha"] = pd.to_datetime(d["fechaobservacion"])
    return d.set_index("fecha")["valorobservado"].astype(float)


def main():
    for sitio, codigo in ESTACIONES.items():
        horas = {}
        for var, ds in DATASETS.items():
            s = descargar(ds, codigo)
            # Promedio horario: las observaciones de HH:00 a HH:59 se asignan a la hora HH
            horas[var] = s.groupby(s.index.floor("h")).mean()
            print(f"{sitio} {var}: {len(s)} registros -> {horas[var].count()} horas "
                  f"({s.index.min().date()} a {s.index.max().date()})")
        carpeta = CRUDOS / sitio
        carpeta.mkdir(exist_ok=True)
        pd.DataFrame(horas).rename_axis("fecha_hora").to_csv(carpeta / "ideam_aut_horario.csv")


if __name__ == "__main__":
    main()
