"""Parámetros del análisis. Modifique aquí sitios, ventana, medias móviles y umbrales epidemiológicos."""
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
CRUDOS = BASE / "datos_crudos"
SALIDA = BASE / "resultados"
FIGS = SALIDA / "figuras"

PERIODO = ("2011-01-01", "2025-12-31")

# Sitios de interés. 'estacion' = hay estación IDEAM de T y lluvia a < 5 km (Las Margaritas).
# 'ref_hr' = estación automática IDEAM con HR horaria usada como referencia de humedad.
SITIOS = {
    "delicias": dict(nombre="Finca Las Delicias", lat=3.81687, lon=-73.34229,  # 3°49'0.73"N 73°20'32.23"O
                     municipio="San Carlos de Guaroa", estacion=False, ref_hr="libertad"),
    "taluma": dict(nombre="C.I. Taluma (campo clonal)", lat=4.37769, lon=-72.23030,  # 4°22'39.69"N 72°13'49.08"O
                   municipio="Puerto López", estacion=True, ref_hr="palomera"),
}
# Estaciones automáticas IDEAM con HR horaria (datos.gov.co). Las Margaritas no midió HR antes de 2026.
REF_HR = {
    "palomera": dict(nombre="La Palomera AUT [35185010]", lat=4.260321, lon=-72.564525, km={"taluma": 39.3}),
    "libertad": dict(nombre="La Libertad AUT [35025110]", lat=4.057415, lon=-73.467865, km={"delicias": 30.2}),
}

# Ventana epidemiológica continua: 1 nov (año) -> 28/29 feb (año+1)
VENTANA_MESES = [11, 12, 1, 2]
NOMBRE_MES = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
              7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}

# Medias móviles (días). Se calculan centradas y retrasadas.
MA_DIAS = [3, 7]
# Ventanas de acumulación / rezago (días)
VENTANAS = [3, 7, 14, 21, 30]

# Umbral de lluvia para "día lluvioso"
LLUVIA_DIA_MM = 1.0

# Nombres de las enfermedades (texto plano y con cursiva para figuras, formato mathtext)
SALB_NOMBRE = "Mal Suramericano de las Hojas (SALB)"
CLF_NOMBRE = "Colletotrichum Leaf Fall (CLF)"
CLF_FIG = r"$\it{Colletotrichum}$ Leaf Fall (CLF)"

# --- Mal Suramericano de las Hojas (SALB, Pseudocercospora ulei) ---------
# Literatura: Holliday 1970; Gasparotto et al. 1997; Guyot et al. 2014.
# Infección: >= 10 h de hoja mojada (proxy HR >= 90 %), T 20-28 °C (óptimo ~24 °C).
SALB = dict(hr_umbral=90, horas_min=10, t_min=20.0, t_max=28.0)

# --- Colletotrichum Leaf Fall (CLF, Colletotrichum spp.) -----------------
# Literatura: Jayasinghe et al. 1997; Saha et al. 2002; Cao et al. 2019.
# Infección: T media 24-30 °C, >= 12 h de HR >= 90 % o lluvia (dispersión por salpique).
CLF = dict(hr_umbral=90, horas_min=12, t_min=24.0, t_max=30.0, lluvia_mm=1.0)
