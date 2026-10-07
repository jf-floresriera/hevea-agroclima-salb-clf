"""Humedad relativa horaria: estaciones automáticas IDEAM y corrección de ERA5-Land por mapeo de cuantiles.

ERA5-Land subestima la HR nocturna en los Llanos (noches demasiado secas y cálidas), así que casi no
alcanza el 90 % en la época seca. Se corrige con un mapeo empírico de cuantiles (quantile mapping)
por mes y bloque de 3 horas, entrenado con la HR horaria de una estación automática IDEAM.
"""
import numpy as np
import pandas as pd

import config as C
from cargar_datos import leer_era5_horario, leer_nasa_horario

CUANTILES = np.linspace(0, 1, 101)


def leer_estacion_horaria(ref):
    """HR y T horarias de una estación automática IDEAM, con control de calidad básico."""
    o = pd.read_csv(C.CRUDOS / ref / "ideam_aut_horario.csv", index_col=0, parse_dates=True)
    o["hr"] = o["hr"].where(o["hr"].between(10, 100))
    o["t"] = o["t"].where(o["t"].between(10, 45))
    # Sensor pegado: el mismo valor 12 horas seguidas se descarta
    pegado = o["hr"].diff().eq(0).rolling(12).sum().ge(11) & o["hr"].lt(99)
    o.loc[pegado, "hr"] = np.nan
    return o.loc[C.PERIODO[0]:C.PERIODO[1]]


def horas_hr_alta(hr, minimo_horas=22):
    """Horas/día con HR >= 90 %. Días con menos de 'minimo_horas' datos válidos = NaN."""
    dia = hr.index.normalize()
    n = hr.groupby(dia).count()
    return (hr >= C.SALB["hr_umbral"]).groupby(dia).sum().where(n >= minimo_horas)


def _clave(idx):
    return idx.month * 10 + idx.hour // 3


def entrenar_qm(obs, mod):
    """Cuantiles por (mes, bloque de 3 h) de la estación y del modelo en las horas comunes."""
    m = pd.concat({"o": obs, "m": mod}, axis=1).dropna()
    tabla = {}
    for k, g in m.groupby(_clave(m.index)):
        tabla[k] = (np.quantile(g["m"], CUANTILES), np.quantile(g["o"], CUANTILES))
    return tabla


def aplicar_qm(mod, tabla):
    out = mod.astype(float).copy()
    claves = _clave(mod.index)
    for k, (qm, qo) in tabla.items():
        sel = claves == k
        out[sel] = np.interp(mod[sel], qm, qo)
    return out.clip(0, 100)


def validar_horas_hr(refs):
    """Valida las horas/día con HR >= 90 % contra las estaciones de referencia.

    Esquemas: (1) entrenar en años impares y probar en pares (y viceversa) en la misma estación;
    (2) entrenar en una estación y probar en la otra (transferibilidad espacial).
    """
    filas, mensual = [], []
    datos = {r: (leer_estacion_horaria(r)["hr"], leer_era5_horario(r)["hr"], leer_nasa_horario(r)["hr"])
             for r in refs}
    for r, (obs, era, nasa) in datos.items():
        obs_h = horas_hr_alta(obs)
        impar = obs.index.year % 2 == 1
        corr = pd.concat([aplicar_qm(era[era.index.year % 2 == p], entrenar_qm(obs[impar == (p == 0)], era))
                          for p in (0, 1)]).sort_index()
        otra = [x for x in refs if x != r][0]
        corr_otra = aplicar_qm(era, entrenar_qm(datos[otra][0], datos[otra][1]))
        for etiqueta, serie in [("ERA5-Land sin corregir", era),
                                ("ERA5-Land QM (validación cruzada por años)", corr),
                                (f"ERA5-Land QM entrenado en {C.REF_HR[otra]['nombre']}", corr_otra),
                                ("NASA POWER", nasa)]:
            p = horas_hr_alta(serie)
            m = pd.concat([obs_h, p], axis=1).dropna()
            o, s = m.iloc[:, 0], m.iloc[:, 1]
            v = m[m.index.month.isin(C.VENTANA_MESES)]
            filas.append({"estacion": C.REF_HR[r]["nombre"], "producto": etiqueta, "n_dias": len(m),
                          "horas_obs": o.mean(), "horas_prod": s.mean(), "sesgo_h": (s - o).mean(),
                          "MAE_h": (s - o).abs().mean(), "r": o.corr(s),
                          "sesgo_h_ventana": (v.iloc[:, 1] - v.iloc[:, 0]).mean(),
                          "r_ventana": v.iloc[:, 0].corr(v.iloc[:, 1]),
                          "acierto_dia_10h_%": 100 * ((o >= C.SALB["horas_min"]) == (s >= C.SALB["horas_min"])).mean()})
            mm = m.groupby(m.index.month).mean()
            mensual.append(pd.DataFrame({"estacion": C.REF_HR[r]["nombre"], "producto": etiqueta,
                                         "mes": mm.index, "horas_obs": mm.iloc[:, 0].values,
                                         "horas_prod": mm.iloc[:, 1].values}))
    return pd.DataFrame(filas).round(3), pd.concat(mensual).round(2)


def corregir_sitio(sitio, h_era5):
    """Aplica al sitio el QM entrenado con su estación de referencia de HR (todo el periodo)."""
    ref = C.SITIOS[sitio]["ref_hr"]
    est = leer_estacion_horaria(ref)
    tabla = entrenar_qm(est["hr"], leer_era5_horario(ref)["hr"])
    return h_era5.assign(hr=aplicar_qm(h_era5["hr"], tabla)), est
