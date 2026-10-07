"""Lectura y limpieza de fuentes por sitio.

Fuentes homogéneas en ambos sitios (mismo producto, mismo método):
  _era5  ERA5-Land 9 km (T, HR) + ERA5 0.25° (radiación, ETP) + CHIRPS 5 km (lluvia)
  _nasa  NASA POWER (MERRA-2 / CERES, ~50 km)
  _est   Estación IDEAM co-ubicada (solo Taluma: Hacienda Las Margaritas, a 0.9 km)
  _agera5 / _imerg  AgERA5 e IMERG exportados desde Google Earth Engine (opcionales, datos_crudos/gee/)
"""
import warnings

import numpy as np
import pandas as pd

from config import BASE, CRUDOS, PERIODO, SITIOS

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

# Rangos físicamente plausibles para la Orinoquía; fuera de ellos el dato se descarta
RANGOS = {"tmax": (20, 42), "tmin": (12, 30), "tmed": (18, 35), "prec": (0, 250),
          "hr": (30, 100), "bs": (0, 13)}

ARCHIVOS_DHIME = {"tmax": "Dhime TMax Las Margaritas.xlsx", "tmin": "Dhime TMin Las Margaritas.xlsx",
                  "tmed": "Dhime TM Las Margaritas.xlsx", "prec": "Dhime Prec Las Margaritas.xlsx",
                  "bs": "Dhime BS Las Margaritas.xlsx", "hr": "Dhime HR Las Margaritas.xlsx"}


def _filtrar(s, var):
    lo, hi = RANGOS[var]
    malos = (s < lo) | (s > hi)
    if malos.any():
        print(f"   {var}: {malos.sum()} valores fuera de rango [{lo}, {hi}] descartados")
    return s.mask(malos)


def _saltar_encabezado(ruta):
    with open(ruta, encoding="utf-8", errors="ignore") as fh:
        for i, linea in enumerate(fh):
            if linea.startswith("-END HEADER-"):
                return i + 1
    return 0


def _openmeteo(ruta, cols):
    d = pd.read_csv(ruta, skiprows=3, index_col=0, parse_dates=True)
    d.columns = cols
    return d


# ---------------------------------------------------------------- productos por sitio
def leer_era5(sitio):
    """ERA5-Land (T, HR diaria) + ERA5 (radiación, ETP) + CHIRPS (lluvia)."""
    c = CRUDOS / sitio
    d = _openmeteo(c / "era5land_diario.csv", ["tmax", "tmin", "tmed", "_p", "_r", "_e", "hr"])
    d = d[["tmax", "tmin", "tmed", "hr"]]
    d = d.join(_openmeteo(c / "era5_rad_etp.csv", ["rad", "etp"]))
    chirps = c / "chirps_diario.csv"
    if chirps.exists():
        d["prec"] = pd.read_csv(chirps, index_col=0, parse_dates=True)["prec_chirps"]
    else:
        print(f"   AVISO: falta CHIRPS para {sitio}; ejecute scripts/descargar_chirps.py")
        d["prec"] = np.nan
    return d.add_suffix("_era5")


def leer_nasa_diario(sitio):
    f = CRUDOS / sitio / "nasa_power_diario.csv"
    df = pd.read_csv(f, skiprows=_saltar_encabezado(f))
    df["fecha"] = pd.to_datetime(df["YEAR"].astype(str) + df["DOY"].astype(str).str.zfill(3), format="%Y%j")
    df = df.set_index("fecha").replace(-999, np.nan)
    df = df.rename(columns={"T2M": "tmed", "T2M_MAX": "tmax", "T2M_MIN": "tmin", "RH2M": "hr",
                            "T2MDEW": "tdew", "PRECTOTCORR": "prec", "ALLSKY_SFC_SW_DWN": "rad",
                            "WS2M": "viento", "GWETTOP": "hum_suelo"})
    return df.drop(columns=["YEAR", "DOY"]).add_suffix("_nasa")


def leer_nasa_horario(sitio):
    partes = []
    for f in sorted((CRUDOS / sitio).glob("nasa_power_horario_*.csv")):
        partes.append(pd.read_csv(f, skiprows=_saltar_encabezado(f)))
    h = pd.concat(partes).replace(-999, np.nan)
    h.index = pd.to_datetime(dict(year=h.YEAR, month=h.MO, day=h.DY, hour=h.HR))
    return h[["T2M", "RH2M"]].rename(columns={"T2M": "t", "RH2M": "hr"})


def leer_era5_horario(sitio):
    return _openmeteo(CRUDOS / sitio / "era5land_horario.csv", ["t", "hr", "td"])[["t", "hr"]]


# ---------------------------------------------------------------- Google Earth Engine (opcional)
# Nombres de bandas de AgERA5 (Climate Engine) -> variable. Se busca por fragmento en minúsculas.
AGERA5_BANDAS = [("temperature_air_2m_max", "tmax"), ("temperature_air_2m_min", "tmin"),
                 ("temperature_air_2m_mean", "tmed"), ("precipitation", "prec"),
                 ("solar_radiation", "rad"), ("vapour_pressure", "pvap"), ("wind_speed", "viento"),
                 ("relative_humidity_2m_06", "hr06"), ("relative_humidity_2m_09", "hr09"),
                 ("relative_humidity_2m_12", "hr12"), ("relative_humidity_2m_15", "hr15"),
                 ("relative_humidity_2m_18", "hr18")]


def leer_agera5(punto):
    f = CRUDOS / "gee" / f"agera5_{punto}.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f)
    d.index = pd.to_datetime(d["fecha"])
    out = pd.DataFrame(index=d.index)
    for frag, var in AGERA5_BANDAS:
        col = next((c for c in d.columns if frag in c.lower()), None)
        if col is not None and var not in out:
            out[var] = pd.to_numeric(d[col], errors="coerce")
    for v in ("tmax", "tmin", "tmed"):
        if v in out and out[v].mean() > 200:  # Kelvin -> °C
            out[v] -= 273.15
    if "rad" in out and out["rad"].mean() > 1e4:  # J/m2/día -> MJ/m2/día
        out["rad"] /= 1e6
    hr = [c for c in out if c.startswith("hr")]
    if hr:
        out["hr"] = out[hr].mean(axis=1)  # promedio de las 5 horas disponibles (06-18 h)
    print(f"   AgERA5 {punto}: {list(out.columns)}")
    return out.add_suffix("_agera5")


def leer_imerg(punto):
    f = CRUDOS / "gee" / f"imerg_{punto}.csv"
    if not f.exists():
        return None
    d = pd.read_csv(f, index_col="fecha", parse_dates=True)
    print(f"   IMERG {punto}: {len(d)} días")
    return d.rename(columns={"imerg_mm": "prec_imerg", "imerg_horas_lluvia": "horas_lluvia_imerg",
                             "imerg_max_mmh": "intensidad_max_imerg"})


# ---------------------------------------------------------------- estaciones IDEAM
def leer_dhime(archivo, var):
    crudo = pd.read_excel(BASE / archivo, header=None)
    estacion = str(crudo.iloc[1, 1])
    d = crudo.iloc[8:, [0, 2]].dropna()
    d.columns = ["fecha", var]
    d["fecha"] = pd.to_datetime(d["fecha"], format="%Y-%m-%d %H:%M")
    s = pd.to_numeric(d.set_index("fecha")[var], errors="coerce")
    s = s[~s.index.duplicated()]
    print(f"   {archivo}: {estacion} | {s.index.min().date()} a {s.index.max().date()} | n={s.count()}")
    return _filtrar(s, var), estacion


def leer_estaciones():
    series, estaciones = {}, {}
    for var, arch in ARCHIVOS_DHIME.items():
        series[var], estaciones[var] = leer_dhime(arch, var)
    return pd.DataFrame(series), estaciones


# ---------------------------------------------------------------- ensamblado
def cargar_sitio(sitio, est=None):
    """Tabla diaria de un sitio y sus datos horarios (ERA5-Land y NASA)."""
    idx = pd.date_range(*PERIODO, freq="D")
    partes = [leer_era5(sitio), leer_nasa_diario(sitio)]
    partes += [x for x in (leer_agera5(sitio), leer_imerg(sitio)) if x is not None]
    if SITIOS[sitio]["estacion"] and est is not None:
        # La HR del archivo DHIME es de La Palomera: entra como estación de referencia de HR, no aquí
        partes.append(est.drop(columns="hr").add_suffix("_est"))
    diario = pd.concat(partes, axis=1).reindex(idx)
    diario.index.name = "fecha"
    return diario, leer_era5_horario(sitio), leer_nasa_horario(sitio)
