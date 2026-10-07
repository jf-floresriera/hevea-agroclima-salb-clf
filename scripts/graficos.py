"""Figuras del análisis climático (matplotlib, PNG 150 dpi)."""
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap

import config as C

# Paleta categórica validada (3 primeras ranuras: seguras para daltonismo en todos los pares)
AZUL, NARANJA, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
COLOR = {"era5": AZUL, "nasa": NARANJA, "est": AQUA, "ref": AQUA, "agera5": "#4a3aa7", "imerg": "#4a3aa7"}
NOMBRE = {"era5": "ERA5-Land / CHIRPS", "nasa": "NASA POWER", "est": "Estación Las Margaritas",
          "agera5": "AgERA5", "imerg": "GPM IMERG"}
COLOR_SITIO = {"delicias": AZUL, "taluma": NARANJA}
COLOR_MA = {3: AZUL, 7: NARANJA}
GRIS = "#b9b8b2"
TINTA, TINTA2 = "#0b0b0b", "#52514e"
SOMBRA = "#f3ecd9"  # ventana epidemiológica nov-feb
SECUENCIAL = ["#f0efec", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
# Meses ordenados jul -> jun para que la ventana nov-feb quede continua en los ejes
ORDEN = [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6]
POS = {m: i for i, m in enumerate(ORDEN)}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
    "axes.labelcolor": TINTA2, "axes.edgecolor": "#c9c8c2", "xtick.color": TINTA2,
    "ytick.color": TINTA2, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e8e7e3", "grid.linewidth": 0.6, "legend.frameon": False,
    "figure.dpi": 150, "savefig.bbox": "tight", "lines.linewidth": 1.5, "mathtext.fontset": "dejavusans",
})
SALB_CORTO, CLF_CORTO = "SALB", "CLF"


def _guardar(fig, nombre, sub):
    carpeta = C.FIGS / sub
    carpeta.mkdir(parents=True, exist_ok=True)
    # Reintenta si el archivo está abierto/bloqueado por un visor de imágenes
    for _ in range(5):
        try:
            fig.savefig(carpeta / nombre)
            break
        except OSError:
            time.sleep(1.5)
    else:
        fig.savefig(carpeta / nombre.replace(".png", "_nuevo.png"))
    plt.close(fig)


def _titulo(fig, texto, y=None):
    kw = dict(x=0.01, ha="left", fontweight="bold", fontsize=12)
    if y:
        kw["y"] = y
    fig.suptitle(texto, **kw)


def _fuentes(df, var, cuales=("era5", "nasa", "agera5", "imerg", "est")):
    return [f for f in cuales if f"{var}_{f}" in df and df[f"{var}_{f}"].notna().any()]


def _ventana_fechas(axs, idx):
    """Sombrea la ventana continua 1 nov - 1 mar de cada temporada en un eje de fechas."""
    for a in range(idx[0].year - 1, idx[-1].year + 1):
        ini, fin = pd.Timestamp(a, 11, 1), pd.Timestamp(a + 1, 3, 1)
        if fin < idx[0] or ini > idx[-1]:
            continue
        for ax in axs:
            ax.axvspan(ini, fin, color=SOMBRA, zorder=0, lw=0)


def _ventana_meses(ax):
    """Sombrea nov-feb en un eje de meses ordenado jul -> jun."""
    ax.axvspan(POS[11] - 0.5, POS[2] + 0.5, color=SOMBRA, zorder=0, lw=0)


def _eje_meses(ax):
    ax.set_xticks(range(12), [C.NOMBRE_MES[m][0] for m in ORDEN])
    ax.set_xlim(-0.6, 11.6)


def _rango(temporada):
    a = int(temporada[:4])
    return pd.Timestamp(a, 11, 1), pd.Timestamp(a + 1, 3, 1) - pd.Timedelta(days=1)


# 1. Series históricas mensuales -------------------------------------------------------------
def series_mensuales(mensual, sub, nombre):
    vars_ = [("prec", "Precipitación mensual (mm)"), ("tmax", "T máxima media (°C)"),
             ("tmin", "T mínima media (°C)"), ("hr", "Humedad relativa media (%)")]
    fig, axs = plt.subplots(4, 1, figsize=(12, 11), sharex=True)
    for ax, (v, tit) in zip(axs, vars_):
        if v == "hr":
            for c, col, et in [("hr_era5c", AZUL, "ERA5-Land corregida"), ("hr_nasa", NARANJA, "NASA POWER"),
                               ("hr_ref", AQUA, "Estación ref. HR")]:
                if c in mensual and mensual[c].notna().any():
                    ax.plot(mensual.index, mensual[c], color=col, label=et, lw=1.3)
        else:
            for f in _fuentes(mensual, v):
                ax.plot(mensual.index, mensual[f"{v}_{f}"], color=COLOR[f], label=NOMBRE[f], lw=1.3)
        ax.set_title(tit, loc="left")
        ax.legend(ncol=4, loc="upper left", fontsize=8)
    _ventana_fechas(axs, mensual.index)
    _titulo(fig, f"{nombre} — series mensuales 2011-2025 por fuente. Sombreado = ventana 1 nov - 28/29 feb", y=1.0)
    fig.tight_layout()
    _guardar(fig, "01_series_historicas_mensuales.png", sub)


# 2. Climatología mensual ----------------------------------------------------------------------
def climatologia(clim, sub, nombre):
    vars_ = [("prec", "Precipitación (mm/mes)"), ("tmax", "T máxima (°C)"), ("tmin", "T mínima (°C)"),
             ("tmed", "T media (°C)"), ("hr", "Humedad relativa (%)"), ("hr90_horas", "Horas HR≥90 % por mes")]
    x = np.array([POS[m] for m in clim.index])
    fig, axs = plt.subplots(2, 3, figsize=(13, 7))
    for ax, (v, tit) in zip(axs.flat, vars_):
        _ventana_meses(ax)
        if v in ("hr", "hr90_horas"):
            series = [(f"{v}_era5c" if v == "hr" else "hr90_horas", AZUL, "ERA5-Land corregida"),
                      (f"{v}_nasa", NARANJA, "NASA POWER"), (f"{v}_ref", AQUA, "Estación ref. HR")]
        else:
            series = [(f"{v}_{f}", COLOR[f], NOMBRE[f]) for f in ("era5", "nasa", "agera5", "imerg", "est")]
        series = [s for s in series if f"{s[0]}_mean" in clim and clim[f"{s[0]}_mean"].notna().any()]
        ancho = 0.8 / max(len(series), 1)
        for i, (c, col, et) in enumerate(series):
            y = clim[f"{c}_mean"].values
            if v in ("prec", "hr90_horas"):
                ax.bar(x + (i - (len(series) - 1) / 2) * ancho, y, ancho * 0.9, color=col, label=et)
            else:
                o = np.argsort(x)
                ax.plot(x[o], y[o], "-o", ms=4, color=col, label=et)
        _eje_meses(ax)
        ax.set_title(tit, loc="left")
        ax.legend(loc="lower left", fontsize=7)
    _titulo(fig, f"{nombre} — climatología mensual 2011-2025 (eje jul→jun). Sombreado = ventana nov-feb")
    fig.tight_layout()
    _guardar(fig, "02_climatologia_mensual.png", sub)


# 3. Medias móviles 3 y 7 días, centrada vs retrasada (una figura por temporada) -------------
def medias_moviles_temporada(diario, ma, temporada, sub, nombre):
    ini, fin = _rango(temporada)
    d, m = diario.loc[ini:fin], ma.loc[ini:fin]
    filas = [("tmed_era5", "T media ERA5-Land (°C)"), ("hr_era5c", "HR media ERA5-Land corregida (%)"),
             ("hr90_horas", "Horas con HR ≥ 90 %"), ("prec_era5", "Lluvia CHIRPS (mm)")]
    fig, axs = plt.subplots(4, 2, figsize=(14, 11), sharex=True)
    for i, (c, tit) in enumerate(filas):
        for j, (tipo, etq) in enumerate([("c", "centrada"), ("r", "retrasada")]):
            ax = axs[i, j]
            if c.startswith("prec"):
                ax.bar(d.index, d[c], color=GRIS, width=0.9, label="diario")
                for n in C.MA_DIAS:
                    ax.plot(m.index, m[f"{c}_acum{n}{tipo}"], color=COLOR_MA[n], lw=1.6,
                            label=f"acumulado {n} días")
            else:
                ax.plot(d.index, d[c], color=GRIS, lw=0.9, label="diario")
                for n in C.MA_DIAS:
                    ax.plot(m.index, m[f"{c}_ma{n}{tipo}"], color=COLOR_MA[n], lw=1.8, label=f"media móvil {n} días")
            if c == "hr90_horas":
                ax.axhline(C.SALB["horas_min"], color=TINTA2, ls="--", lw=1)
            ax.set_title(f"{tit} — {etq}", loc="left", fontsize=9)
            if i == 0:
                ax.legend(fontsize=7, ncol=3, loc="lower left")
            elif c.startswith("prec") and j == 0:
                ax.legend(fontsize=7, ncol=3, loc="upper left")
    axs[-1, 0].xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    axs[-1, 1].xaxis.set_major_formatter(mdates.DateFormatter("%d-%b"))
    _titulo(fig, f"{nombre} — medias móviles de 3 y 7 días, temporada {temporada} (1 nov - 28/29 feb).\n"
                 "Izquierda: centrada (días antes y después). Derecha: retrasada (solo días anteriores).")
    fig.tight_layout()
    _guardar(fig, f"medias_moviles_{temporada}.png", f"{sub}/04_temporadas")


# 4. Panel por temporada ------------------------------------------------------------------------
def panel_temporada(diario, ma, semanal, temporada, sub, nombre, ref_nombre):
    ini, fin = _rango(temporada)
    d, m = diario.loc[ini:fin], ma.loc[ini:fin]
    s = semanal[(semanal.index >= ini) & (semanal.index <= fin)]
    fig, axs = plt.subplots(4, 1, figsize=(12, 11), sharex=True, gridspec_kw={"height_ratios": [1, 1, 1.1, 0.55]})
    ax = axs[0]
    ax.axhspan(C.SALB["t_min"], C.SALB["t_max"], color="#e6f0fc", zorder=0, lw=0)
    ax.plot(d.index, d["tmed_era5"], color=GRIS, lw=0.9, label="T media diaria")
    for n in C.MA_DIAS:
        ax.plot(m.index, m[f"tmed_era5_ma{n}r"], color=COLOR_MA[n], lw=1.8, label=f"T media MA{n} retrasada")
    if "tmed_est" in d and d["tmed_est"].notna().any():
        ax.plot(m.index, m["tmed_est_ma3r"], color=AQUA, lw=1.4, label="T media estación MA3")
    ax.set_title("Temperatura (°C), ERA5-Land — franja azul = rango favorable SALB 20-28 °C", loc="left")
    ax.legend(fontsize=7, ncol=4, loc="lower left")
    ax = axs[1]
    ax.bar(d.index, d["hr90_horas"], color=GRIS, width=0.9, label="diario (ERA5-Land corregida)")
    for n in C.MA_DIAS:
        ax.plot(m.index, m[f"hr90_horas_ma{n}r"], color=COLOR_MA[n], lw=1.8, label=f"MA{n} retrasada")
    if d["hr90_horas_ref"].notna().any():
        ax.plot(d.index, d["hr90_horas_ref"], "o", ms=3, color=AQUA, label=f"observado {ref_nombre}")
    ax.axhline(C.SALB["horas_min"], color=TINTA2, ls="--", lw=1)
    ax.axhline(C.CLF["horas_min"], color=TINTA2, ls=":", lw=1)
    ax.set_ylim(0, 24.5)
    ax.set_title(f"Horas/día con HR ≥ 90 % (proxy de hoja mojada) — umbral SALB {C.SALB['horas_min']} h (--), "
                 f"CLF {C.CLF['horas_min']} h (··)", loc="left")
    ax.legend(fontsize=7, ncol=4, loc="upper right")
    ax = axs[2]
    ax.bar(s.index + pd.Timedelta(days=3), s["prec_era5"], width=6, color="#cde2fb",
           label="acumulado semana calendario", zorder=1)
    ax.bar(d.index, d["prec_era5"], width=0.9, color=AZUL, label="diario", zorder=2)
    ax.plot(m.index, m["prec_era5_acum7r"], color=NARANJA, lw=1.4, label="acumulado 7 días (retrasado)", zorder=3)
    if "prec_est" in s and s["prec_est"].notna().any():
        ax.plot(s.index + pd.Timedelta(days=3), s["prec_est"], "o", ms=4, color=AQUA, label="semana, estación")
    ax.set_title("Precipitación CHIRPS (mm)", loc="left")
    ax.legend(fontsize=7, ncol=4, loc="upper left")
    ax = axs[3]
    sa, co = d.index[d["salb_favorable"] == 1], d.index[d["clf_favorable"] == 1]
    ax.scatter(sa, np.ones(len(sa)), marker="|", s=120, color=AZUL)
    ax.scatter(co, np.zeros(len(co)), marker="|", s=120, color=NARANJA)
    ax.set_yticks([])
    for yy, txt in [(1.3, f"{C.SALB_NOMBRE}: {len(sa)} días"), (0.3, f"{C.CLF_FIG}: {len(co)} días")]:
        ax.text(ini, yy, txt, fontsize=8, color=TINTA2, va="bottom")
    ax.set_ylim(-0.4, 1.8)
    ax.grid(axis="y", visible=False)
    ax.set_title("Días con condiciones favorables de infección", loc="left")
    ax.set_xlim(ini - pd.Timedelta(days=1), fin + pd.Timedelta(days=1))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b-%Y"))
    _titulo(fig, f"{nombre} — temporada {temporada} (ventana 1 nov - 28/29 feb)")
    fig.tight_layout()
    _guardar(fig, f"temporada_{temporada}.png", f"{sub}/04_temporadas")


# 5. Semanas de la ventana: variabilidad entre años -----------------------------------------------
def semanas_temporada(diario, sub, nombre):
    d = diario[diario.index.month.isin(C.VENTANA_MESES)].copy()
    ini = np.where(d.index.month >= 11, d.index.year, d.index.year - 1)
    d["temporada"] = ini
    d["semana"] = ((d.index - pd.to_datetime([f"{a}-11-01" for a in ini])).days // 7) + 1
    d = d[d["semana"] <= 17]
    g = d.groupby(["temporada", "semana"])
    s = pd.DataFrame({"prec_era5": g["prec_era5"].sum(), "hr90_horas": g["hr90_horas"].sum(),
                      "salb_favorable": g["salb_favorable"].sum(), "clf_favorable": g["clf_favorable"].sum(),
                      "n": g.size()}).reset_index()
    s = s[s["n"] >= 6]
    paneles = [("prec_era5", "Lluvia CHIRPS por semana (mm)"), ("hr90_horas", "Horas HR≥90 % por semana"),
               ("salb_favorable", f"Días favorables {C.SALB_NOMBRE} por semana"),
               ("clf_favorable", f"Días favorables {C.CLF_FIG} por semana")]
    fig, axs = plt.subplots(4, 1, figsize=(12, 12), sharex=True)
    semanas = sorted(s["semana"].unique())
    for ax, (c, tit) in zip(axs, paneles):
        datos = [s.loc[s["semana"] == w, c].dropna().values for w in semanas]
        bp = ax.boxplot(datos, positions=semanas, widths=0.6, patch_artist=True,
                        flierprops=dict(ms=2, mec=GRIS), medianprops=dict(color=TINTA, lw=1.5))
        for b in bp["boxes"]:
            b.set(facecolor="#cde2fb", edgecolor=AZUL, lw=0.8)
        ax.set_title(tit, loc="left")
    for mes, wk in [("Nov", 1), ("Dic", 5.3), ("Ene", 9.7), ("Feb", 14.1)]:
        for ax in axs:
            ax.axvline(wk - 0.5, color="#d6d5cf", lw=0.8, zorder=0)
        axs[0].text(wk - 0.3, 0.97, mes, fontsize=8, color=TINTA2, va="top", transform=axs[0].get_xaxis_transform())
    axs[-1].set_xlabel("Semana de la ventana (semana 1 = 1-7 nov; semana 17 = fin de feb)")
    _titulo(fig, f"{nombre} — variabilidad entre años por semana de la ventana nov-feb (2011-2025)", y=1.01)
    fig.tight_layout()
    _guardar(fig, "05_semanas_ventana_boxplot.png", sub)


# 6. Mapas de calor temporada x mes de la ventana -------------------------------------------
def heatmaps(diario, sub, nombre):
    d = diario[diario.index.month.isin(C.VENTANA_MESES)].copy()
    ini = np.where(d.index.month >= 11, d.index.year, d.index.year - 1)
    d["temporada"] = [f"{a}-{a + 1}" for a in ini]
    d["mes"] = d.index.month
    cmap = ListedColormap(SECUENCIAL)
    meses = C.VENTANA_MESES
    fig, axs = plt.subplots(1, 4, figsize=(17, 6.5))
    for ax, (c, tit, agg) in zip(axs, [("salb_favorable", f"Días favorables\n{C.SALB_NOMBRE}", "sum"),
                                        ("clf_favorable", f"Días favorables\n{C.CLF_FIG}", "sum"),
                                        ("hr90_horas", "Horas HR≥90 %\n(media diaria)", "mean"),
                                        ("prec_era5", "Lluvia CHIRPS\n(mm/mes)", "sum")]):
        t = d.pivot_table(index="temporada", columns="mes", values=c, aggfunc=agg)[meses]
        im = ax.imshow(t.values, aspect="auto", cmap=cmap)
        ax.set_xticks(range(len(meses)), [C.NOMBRE_MES[m] for m in meses])
        ax.set_yticks(range(len(t)), t.index)
        corte = np.nanpercentile(t.values, 60)
        for (i, j), v in np.ndenumerate(t.values):
            if np.isfinite(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=7, color="white" if v > corte else TINTA)
        ax.grid(False)
        ax.set_title(tit, loc="left")
        fig.colorbar(im, ax=ax, shrink=0.7)
    _titulo(fig, f"{nombre} — temporada × mes de la ventana nov-feb")
    fig.tight_layout()
    _guardar(fig, "06_mapas_calor_temporada_mes.png", sub)


# 7. Ciclo anual diario ---------------------------------------------------------------------
def ciclo_anual(diario, ma, sub, nombre):
    d = pd.concat([ma[["prec_era5_acum7c", "hr90_horas_ma7c", "tmed_era5_ma7c"]]], axis=1)
    # Día del año agrícola: 1 jul = día 1, para que la ventana nov-feb quede continua
    d["dia"] = (d.index - pd.to_datetime([f"{y if m >= 7 else y - 1}-07-01" for y, m in
                                          zip(d.index.year, d.index.month)])).days + 1
    d = d[d["dia"] <= 365]
    paneles = [("prec_era5_acum7c", "Lluvia acumulada 7 días CHIRPS (mm)"),
               ("hr90_horas_ma7c", "Horas HR≥90 % (MA7 centrada)"), ("tmed_era5_ma7c", "T media ERA5-Land (MA7 centrada, °C)")]
    fig, axs = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    for ax, (c, tit) in zip(axs, paneles):
        q = d.groupby("dia")[c].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).unstack()
        ax.fill_between(q.index, q[0.1], q[0.9], color=AZUL, alpha=0.12, lw=0, label="percentil 10-90")
        ax.fill_between(q.index, q[0.25], q[0.75], color=AZUL, alpha=0.25, lw=0, label="percentil 25-75")
        ax.plot(q.index, q[0.5], color=AZUL, lw=1.8, label="mediana 2011-2025")
        ax.axvspan(124, 244, color=SOMBRA, zorder=0, lw=0)  # 1 nov (día 124) - 28 feb (día 243)
        ax.set_title(tit, loc="left")
        ax.legend(fontsize=7, ncol=3, loc="upper left")
    inicios = np.cumsum([0, 31, 31, 30, 31, 30, 31, 31, 28, 31, 30, 31]) + 1
    axs[-1].set_xticks(inicios, [C.NOMBRE_MES[m] for m in ORDEN])
    _titulo(fig, f"{nombre} — ciclo anual día a día (año agrícola jul→jun). Sombreado = ventana nov-feb")
    fig.tight_layout()
    _guardar(fig, "07_ciclo_anual_diario.png", sub)


# 8. Efecto de las medias móviles ------------------------------------------------------------
def efecto_ma(suav, sub, nombre):
    clave = ["tmed_era5", "tmax_era5", "tmin_era5", "hr_era5c", "hr90_horas", "hr90_horas_ref",
             "dpv_era5c", "tmed_nasa", "hr_nasa", "tmed_est"]
    s = suav[suav["serie"].isin(clave)].set_index("serie").reindex([c for c in clave if c in set(suav["serie"])])
    y = np.arange(len(s))
    fig, ax = plt.subplots(figsize=(9, 0.45 * len(s) + 1.2))
    for k, n in enumerate(C.MA_DIAS):
        v = s[f"reduccion_ruido_ma{n}_%"]
        ax.barh(y + (k - 0.5) * 0.38, v, 0.36, color=COLOR_MA[n], label=f"media móvil {n} días")
        for yy, vv in zip(y, v):
            ax.text(vv + 0.5, yy + (k - 0.5) * 0.38, f"{vv:.0f} %", va="center", fontsize=7, color=TINTA2)
    ax.set_yticks(y, s.index)
    ax.invert_yaxis()
    ax.set_xlabel("Reducción de la variación día a día (%)")
    ax.grid(axis="y", visible=False)
    ax.legend(fontsize=8, loc="lower right")
    ax.set_title(f"{nombre} — cuánto 'calman' las medias móviles de 3 y 7 días cada serie", loc="left")
    _guardar(fig, "08_efecto_medias_moviles.png", sub)


def por_sitio(sitio, r):
    nombre = C.SITIOS[sitio]["nombre"]
    ref = C.REF_HR[C.SITIOS[sitio]["ref_hr"]]["nombre"].split(" AUT")[0]
    series_mensuales(r["mensual"], sitio, nombre)
    climatologia(r["clim"], sitio, nombre)
    for t in r["temp"].index:
        panel_temporada(r["diario"], r["ma"], r["semanal"], t, sitio, nombre, ref)
        medias_moviles_temporada(r["diario"], r["ma"], t, sitio, nombre)
    semanas_temporada(r["diario"], sitio, nombre)
    heatmaps(r["diario"], sitio, nombre)
    ciclo_anual(r["diario"], r["ma"], sitio, nombre)
    efecto_ma(r["suav"], sitio, nombre)


# ================================================================ comparación
def validacion(taluma):
    d, m, v = taluma["diario"], taluma["mensual"], taluma["valid"]
    casos = [("tmax", d, "T máxima diaria (°C)"), ("tmin", d, "T mínima diaria (°C)"),
             ("tmed", d, "T media diaria (°C)"), ("prec", m, "Lluvia mensual (mm)")]
    fig, axs = plt.subplots(1, 4, figsize=(16, 4.3))
    for ax, (var, df, tit) in zip(axs, casos):
        x = df[f"{var}_est"]
        esc = "mensual" if var == "prec" else "diaria"
        lims = [np.nanmin(x), np.nanmax(x)]
        for f in _fuentes(df, var, ("era5", "nasa", "agera5", "imerg")):
            y = df[f"{var}_{f}"]
            fila = v[(v.variable == var) & (v.escala == esc) & (v.producto == NOMBRE[f])]
            et = ("CHIRPS" if var == "prec" else "ERA5-Land") if f == "era5" else NOMBRE[f]
            if len(fila):
                et += f"  r={fila.r.iloc[0]:.2f}  sesgo={fila.sesgo.iloc[0]:+.1f}"
            ax.scatter(x, y, s=5 if esc == "diaria" else 14, alpha=0.3 if esc == "diaria" else 0.7,
                       color=COLOR[f], label=et, lw=0)
            lims = [min(lims[0], np.nanmin(y)), max(lims[1], np.nanmax(y))]
        ax.plot(lims, lims, color=TINTA2, lw=1, ls="--")
        ax.set_xlabel("Estación Las Margaritas")
        ax.set_ylabel("Producto en Taluma")
        ax.set_title(tit, loc="left")
        ax.legend(loc="upper left", fontsize=7, markerscale=2)
    _titulo(fig, "Validación en C.I. Taluma: productos vs estación Las Margaritas (0.9 km). Línea 1:1")
    fig.tight_layout()
    _guardar(fig, "C1_validacion_T_lluvia_Taluma.png", "comparacion")


def validacion_hr(valid_hr, valid_hr_mes):
    estaciones = valid_hr_mes["estacion"].unique()
    fig, axs = plt.subplots(1, len(estaciones), figsize=(14, 4.8), sharey=True)
    estilos = {"ERA5-Land sin corregir": (GRIS, "-"), "NASA POWER": (NARANJA, "-")}
    for ax, e in zip(np.atleast_1d(axs), estaciones):
        _ventana_meses(ax)
        g = valid_hr_mes[valid_hr_mes["estacion"] == e]
        obs = g.drop_duplicates("mes").set_index("mes")["horas_obs"]
        ax.plot([POS[mm] for mm in obs.index], obs.values, "o", ms=7, color=AQUA, label="observado", zorder=5)
        for p, gp in g.groupby("producto"):
            if "validación cruzada" in p:
                col, ls, et = AZUL, "-", "ERA5-Land corregida (validación cruzada)"
            elif "entrenado en" in p:
                col, ls, et = AZUL, ":", "ERA5-Land corregida con la otra estación"
            else:
                (col, ls), et = estilos[p], p
            gp = gp.set_index("mes").reindex(ORDEN)
            ax.plot(range(12), gp["horas_prod"], ls, color=col, lw=1.6, label=et)
        ax.axhline(C.SALB["horas_min"], color=TINTA2, ls="--", lw=0.8)
        _eje_meses(ax)
        fila = valid_hr[(valid_hr.estacion == e) & valid_hr.producto.str.contains("cruzada")].iloc[0]
        ax.set_title(f"{e}\nERA5-Land corregida: sesgo {fila.sesgo_h:+.1f} h, acierto umbral 10 h "
                     f"{fila['acierto_dia_10h_%']:.0f} %", loc="left", fontsize=9)
    np.atleast_1d(axs)[0].set_ylabel("Horas/día con HR ≥ 90 %")
    np.atleast_1d(axs)[0].legend(fontsize=7, loc="lower left")
    _titulo(fig, "Validación de las horas con HR ≥ 90 % contra estaciones automáticas IDEAM. Sombreado = ventana")
    fig.tight_layout()
    _guardar(fig, "C1b_validacion_horas_HR90.png", "comparacion")


def climatologia_sitios(sitios):
    paneles = [("prec_era5", "Lluvia CHIRPS (mm/mes)", "bar"), ("tmed_era5", "T media ERA5-Land (°C)", "line"),
               ("tmax_era5", "T máxima ERA5-Land (°C)", "line"), ("hr_era5c", "HR ERA5-Land corregida (%)", "line"),
               ("hr90_horas", "Horas HR≥90 % por mes", "bar"),
               ("salb_favorable", f"Días favorables {SALB_CORTO} / mes", "bar"),
               ("clf_favorable", f"Días favorables {CLF_CORTO} / mes", "bar"),
               ("dia_lluvia", "Días con lluvia ≥ 1 mm / mes", "bar")]
    fig, axs = plt.subplots(2, 4, figsize=(17, 7.5))
    for ax, (c, tit, tipo) in zip(axs.flat, paneles):
        _ventana_meses(ax)
        for i, (s, r) in enumerate(sitios.items()):
            y = r["clim"][f"{c}_mean"]
            x = np.array([POS[m] for m in y.index])
            et = C.SITIOS[s]["nombre"]
            if tipo == "bar":
                ax.bar(x + (i - 0.5) * 0.4, y.values, 0.37, color=COLOR_SITIO[s], label=et)
            else:
                o = np.argsort(x)
                ax.plot(x[o], y.values[o], "-o", ms=4, color=COLOR_SITIO[s], label=et)
        _eje_meses(ax)
        ax.set_title(tit, loc="left")
    axs[0, 0].legend(loc="upper left", fontsize=8)
    fig.text(0.01, -0.01, f"SALB = {C.SALB_NOMBRE}.   CLF = {C.CLF_FIG}.", fontsize=9, color=TINTA2)
    _titulo(fig, "Las Delicias vs C.I. Taluma — climatología mensual 2011-2025 (mismas fuentes; eje jul→jun). "
                 "Sombreado = ventana nov-feb")
    fig.tight_layout()
    _guardar(fig, "C2_climatologia_sitios.png", "comparacion")


def temporadas_sitios(sitios):
    fig, axs = plt.subplots(3, 1, figsize=(13, 10), sharex=True)
    temps = sitios["delicias"]["temp"].index
    x = np.arange(len(temps))
    for ax, (c, tit) in zip(axs, [("salb_favorable", f"Días favorables — {C.SALB_NOMBRE}"),
                                  ("clf_favorable", f"Días favorables — {C.CLF_FIG}"),
                                  ("prec_era5", "Lluvia CHIRPS en la ventana (mm)")]):
        for i, (s, r) in enumerate(sitios.items()):
            ax.bar(x + (i - 0.5) * 0.4, r["temp"][c].reindex(temps), 0.37, color=COLOR_SITIO[s],
                   label=C.SITIOS[s]["nombre"])
        ax.set_title(tit, loc="left")
    axs[0].legend(loc="upper right", fontsize=8, ncol=2)
    axs[-1].set_xticks(x, temps, rotation=45)
    _titulo(fig, "Comparación por temporada (ventana 1 nov - 28/29 feb) — Las Delicias vs C.I. Taluma")
    fig.tight_layout()
    _guardar(fig, "C3_temporadas_sitios.png", "comparacion")


def sensibilidad_hr(sitios):
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.8), sharey=True)
    for ax, (s, r) in zip(axs, sitios.items()):
        _ventana_meses(ax)
        d = r["diario"]
        ref = C.REF_HR[C.SITIOS[s]["ref_hr"]]
        for c, col, ls, et in [("hr90_horas_era5", GRIS, "-", "ERA5-Land sin corregir"),
                               ("hr90_horas", AZUL, "-", f"ERA5-Land corregida con {ref['nombre'].split(' AUT')[0]} (usada)"),
                               ("hr90_horas_alt", AZUL, ":", "ERA5-Land corregida con la otra estación"),
                               ("hr90_horas_nasa", NARANJA, "-", "NASA POWER"),
                               ("hr90_horas_ref", AQUA, "-", f"observado en {ref['nombre'].split(' AUT')[0]} ({ref['km'][s]} km)")]:
            y = d[c].groupby(d.index.month).mean().reindex(ORDEN)
            ax.plot(range(12), y.values, ls, marker="o", ms=3.5, color=col, label=et)
        ax.axhline(C.SALB["horas_min"], color=TINTA2, ls="--", lw=1)
        _eje_meses(ax)
        ax.set_title(C.SITIOS[s]["nombre"], loc="left")
        ax.legend(fontsize=7, loc="lower left")
    axs[0].set_ylabel("Horas/día con HR ≥ 90 %")
    _titulo(fig, "Sensibilidad del indicador de hoja mojada a la fuente de HR (línea -- = umbral SALB 10 h)")
    fig.tight_layout()
    _guardar(fig, "C4_sensibilidad_fuente_HR.png", "comparacion")


def comparacion(sitios, valid_hr, valid_hr_mes):
    validacion(sitios["taluma"])
    validacion_hr(valid_hr, valid_hr_mes)
    climatologia_sitios(sitios)
    temporadas_sitios(sitios)
    sensibilidad_hr(sitios)
