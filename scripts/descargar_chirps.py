"""Extrae la lluvia diaria CHIRPS v2.0 (0.05°) en los sitios de config.SITIOS.

Lee de cada COG diario (servidor UCSB-CHC) solo el encabezado y el bloque 512x512 que contiene
cada punto, mediante peticiones HTTP por rango. No usa GDAL (falla con rutas de usuario con tildes).

Uso:  python scripts/descargar_chirps.py            (2011-2025, todos los sitios)
      python scripts/descargar_chirps.py 2026 2026  (otro periodo)
"""
import io
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
import requests
import tifffile

from config import CRUDOS, PERIODO, SITIOS

URL = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_daily/cogs/p05/{a}/chirps-v2.0.{f}.cog"
# Puntos extra de validación (estación de HR)
PUNTOS = {k: (v["lat"], v["lon"]) for k, v in SITIOS.items()}


class RangoHTTP(io.RawIOBase):
    """Archivo de solo lectura sobre HTTP que descarga bloques de 64 KB bajo demanda."""

    def __init__(self, url, ses, bloque=65536):
        self.url, self.ses, self.pos, self.b, self.cache = url, ses, 0, bloque, {}
        r = ses.head(url, timeout=60)
        r.raise_for_status()
        self.size = int(r.headers["Content-Length"])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, o, w=0):
        self.pos = {0: o, 1: self.pos + o, 2: self.size + o}[w]
        return self.pos

    def rango(self, a, n):
        r = self.ses.get(self.url, headers={"Range": f"bytes={a}-{a + n - 1}"}, timeout=60)
        r.raise_for_status()
        return r.content

    def _blk(self, i):
        if i not in self.cache:
            a = i * self.b
            self.cache[i] = self.rango(a, min(self.b, self.size - a))
        return self.cache[i]

    def read(self, n=-1):
        n = self.size - self.pos if n < 0 else min(n, self.size - self.pos)
        out = b""
        while len(out) < n:
            i, off = divmod(self.pos + len(out), self.b)
            out += self._blk(i)[off:off + n - len(out)]
        self.pos += n
        return out

    def readinto(self, b):
        d = self.read(len(b))
        b[:len(d)] = d
        return len(d)


def leer_dia(fecha, ses):
    url = URL.format(a=fecha.year, f=fecha.strftime("%Y.%m.%d"))
    for _ in range(4):
        try:
            fh = RangoHTTP(url, ses)
            with tifffile.TiffFile(fh) as t:
                p = t.pages[0]
                dx, dy, _ = p.tags[33550].value
                x0, y0 = p.tags[33922].value[3:5]
                th, tw = p.tile
                por_fila = -(-p.shape[1] // tw)
                vals = {}
                for sitio, (lat, lon) in PUNTOS.items():
                    col, fila = int((lon - x0) / dx), int((y0 - lat) / dy)
                    i = (fila // th) * por_fila + col // tw
                    datos = fh.rango(p.dataoffsets[i], p.databytecounts[i])
                    bloque = p.decode(datos, i)[0].reshape(th, tw)
                    v = float(bloque[fila % th, col % tw])
                    vals[sitio] = np.nan if v < 0 else v
            return fecha, vals
        except Exception:
            continue
    return fecha, {s: np.nan for s in PUNTOS}


def main(a0=None, a1=None):
    fechas = pd.date_range(f"{a0}-01-01" if a0 else PERIODO[0], f"{a1}-12-31" if a1 else PERIODO[1])
    previos = {}
    for s in PUNTOS:
        f = CRUDOS / s / "chirps_diario.csv"
        previos[s] = pd.read_csv(f, index_col=0, parse_dates=True)["prec_chirps"] if f.exists() else pd.Series(dtype=float)
    faltan = [f for f in fechas if any(pd.isna(previos[s].get(f)) for s in PUNTOS)]
    print(f"CHIRPS: {len(faltan)} días por descargar para {list(PUNTOS)}")
    ses = requests.Session()
    ses.mount("https://", requests.adapters.HTTPAdapter(pool_maxsize=16))
    res = {}
    with ThreadPoolExecutor(12) as ex:
        for k, (f, v) in enumerate(ex.map(lambda f: leer_dia(f, ses), faltan)):
            res[f] = v
            if k % 500 == 0:
                print(f"   {k}/{len(faltan)}")
    nuevo = pd.DataFrame.from_dict(res, orient="index")
    for s in PUNTOS:
        serie = pd.concat([previos[s], nuevo[s] if s in nuevo else pd.Series(dtype=float)]).sort_index()
        serie = serie[~serie.index.duplicated(keep="last")]
        (CRUDOS / s).mkdir(parents=True, exist_ok=True)
        serie.rename("prec_chirps").rename_axis("fecha").to_csv(CRUDOS / s / "chirps_diario.csv")
        print(f"   {s}: {serie.count()} días con dato, {serie.isna().sum()} faltantes")


if __name__ == "__main__":
    main(*(int(x) for x in sys.argv[1:3]))
