# Guía del análisis climático: Las Delicias y C.I. Taluma (caucho)
Epidemiología del **Mal Suramericano de las Hojas (SALB)**, *Pseudocercospora ulei*, y de ***Colletotrichum* Leaf Fall (CLF)**, *Colletotrichum* spp.

**Ventana epidemiológica:** continua del **1 de noviembre al 28/29 de febrero**. En las figuras va sombreada. Los ejes mensuales van de julio a junio para que la ventana quede continua.

## 1. Sitios, estaciones y distancias

| Sitio | Coordenadas | T y lluvia observadas | HR observada (horaria) |
|---|---|---|---|
| Finca Las Delicias | 3°49'0.73"N, 73°20'32.23"O | No hay estación climatológica. Hay **pluviómetros** IDEAM: Santa Helena [35010110] a **2.1 km**, El Toro [35010060] a 7.3 km y Yaguarito [35010150] a 7.4 km | **La Libertad AUT [35025110]**, a 30 km |
| C.I. Taluma (campo clonal) | 4°22'39.69"N, 72°13'49.08"O | **Las Margaritas [35125010], a 0.9 km** | **La Palomera AUT [35185010]**, a 39 km |

- Las Margaritas no midió HR antes de 2026. El archivo "Dhime HR" es de La Palomera.
- La HR horaria de La Palomera (2005-2023) y de La Libertad (2009-2023) se descargó de datos.gov.co con `scripts/descargar_ideam_aut.py`.

## 2. Fuentes de datos

| Sufijo | Fuente | Variables | Estado |
|---|---|---|---|
| `_era5` | CHIRPS v2.0 (5 km) | Lluvia | Listo (`descargar_chirps.py`; idéntico a su archivo SCG) |
| `_era5` | ERA5-Land (9 km) | T diaria y horaria | Listo |
| `_era5c` | ERA5-Land con HR corregida | HR horaria → horas HR ≥ 90 % | Listo. **Fuente principal de HR** |
| `_nasa` | NASA POWER (~50 km) | Todas | Listo |
| `_ref` | Estación automática IDEAM de referencia | HR horaria observada | Listo (2011-2023 con huecos) |
| `_est` | Las Margaritas (solo Taluma) | T, lluvia, brillo solar | Listo |
| `_agera5` | **AgERA5** (10 km) | T, HR a las 06-18 h, lluvia, radiación | **Pendiente: exportar con `scripts/gee_agera5_imerg.js`** |
| `_imerg` | **GPM IMERG** (10 km, cada 30 min) | Lluvia diaria, **horas con lluvia**, intensidad máxima | **Pendiente: mismo script de Earth Engine** |

**Para agregar AgERA5 e IMERG:**
1. Abra https://code.earthengine.google.com.
2. Pegue `scripts/gee_agera5_imerg.js` y presione Run.
3. En la pestaña Tasks, presione RUN en las 8 exportaciones.
4. Copie los CSV de Drive a `datos_crudos/gee/` y vuelva a ejecutar el análisis. Las nuevas fuentes entran solas y se validan contra las estaciones.

**Pluviómetros cercanos a Las Delicias:** descargue de DHIME (http://dhime.ideam.gov.co) la precipitación diaria de Santa Helena, El Toro y Yaguarito, 2011-2025. Con eso se valida CHIRPS en la propia finca.

## 3. Humedad relativa: el punto más delicado

**ERA5-Land subestima mucho la HR nocturna en la época seca.** En enero, La Palomera registra 9 h/día con HR ≥ 90 %, mientras ERA5-Land da 1 h.

**Corrección aplicada:** un *mapeo de cuantiles* por mes y bloque de 3 horas, entrenado con la HR horaria de la estación de referencia de cada sitio. Validado entrenando con unos años y probando con otros (figura `comparacion/C1b`, hoja `validacion_horas_HR90`):

| Estación | Sesgo sin corregir | Sesgo corregido | Acierto del umbral de 10 h (sin → con corrección) |
|---|---|---|---|
| La Palomera | -4.9 h/día | +0.4 h/día | 67 % → 84 % |
| La Libertad | -5.6 h/día | +0.2 h/día | 55 % → 74 % |

**Advertencia importante:** las dos estaciones son muy distintas en la época seca. En enero, La Palomera tiene 9 h/día con HR ≥ 90 % y La Libertad solo 3 h. Una corrección entrenada en una estación no sirve para la otra. Por eso:
- La comparación de humedad **entre** Las Delicias y Taluma depende de qué estación se use como referencia (figura `C4`; columnas `_alt`).
- Con la referencia más cercana a cada sitio, **Taluma resulta más húmedo** en la ventana que Las Delicias. Con las referencias intercambiadas, ocurre lo contrario.
- **Solo un termohigrómetro o un sensor de hoja mojada en cada sitio puede resolverlo.** Es la recomendación más importante del estudio.

## 4. Medias móviles de 3 y 7 días

| Tipo | Días que promedia | Para qué sirve |
|---|---|---|
| **Centrada** (`_ma3c`, `_ma7c`) | 10 ene = promedio del 9-11 ene (MA3) o del 7-13 ene (MA7) | Describir la tendencia y graficar |
| **Retrasada** (`_ma3r`, `_ma7r`) | 10 ene = promedio del 8-10 ene (MA3) o del 4-10 ene (MA7) | Alertas y relación con la enfermedad: solo usa días **anteriores**, que son los que influyen en la infección |

- **La lluvia no se promedia, se acumula:** columnas `_acum3r` y `_acum7r`.
- **Cuánto suaviza cada una** (figura `08`, hoja `efecto_medias_moviles`): la MA3 reduce la variación día a día en ~55-60 % y la MA7 en ~75-80 %.
- **MA3** conserva los eventos cortos, como 2-3 noches húmedas seguidas que bastan para una infección.
- **MA7** muestra el régimen de fondo de la semana, como la entrada a la época seca.
- **Comparación visual:** por cada temporada hay una figura `04_temporadas/medias_moviles_<temporada>.png`, con la centrada a la izquierda y la retrasada a la derecha.
- **Recomendación:** use la **retrasada** para relacionar con la enfermedad. Pruebe las dos longitudes y quédese con la que mejor correlacione con la severidad observada.

## 5. Acumulados semanales y ventanas de rezago
- `semanal_calendario` y `semanal_ventana`: semana ISO (lunes-domingo), para cruzar con evaluaciones semanales.
- `ventanas_moviles`: para cada fecha, lo acumulado en los 3, 7, 14, 21 y 30 días anteriores. Úselas así:
  1. Tome la fecha de cada evaluación de severidad.
  2. Busque las ventanas de esa fecha y de 7, 14 y 21 días antes. La incubación del SALB dura ~7-14 días.
  3. Calcule la correlación de Spearman con cada ventana.

## 6. Validación de T y lluvia en Taluma
- **T media:** ERA5-Land r = 0.66, sesgo -0.1 °C.
- **T mínima de Las Margaritas:** casi no se correlaciona con ningún producto (r ≈ 0.2). Probablemente es un problema de calidad del dato.
- **Lluvia:** CHIRPS da r = 0.68 semanal y 0.86 mensual. NASA sobreestima la lluvia en ~30 %.

## 7. Archivos
| Ruta | Contenido |
|---|---|
| `scripts/config.py` | Sitios, ventana, medias móviles, umbrales y estaciones de referencia |
| `scripts/analisis_clima.py` | Todo el análisis |
| `scripts/humedad.py` | Corrección y validación de la HR horaria |
| `scripts/descargar_chirps.py`, `descargar_ideam_aut.py` | Descargas automáticas |
| `scripts/gee_agera5_imerg.js` | AgERA5 e IMERG (Google Earth Engine) |
| `resultados/<sitio>/Base_climatica_<sitio>.xlsx` | Datos diarios, medias móviles, semanales, temporadas (la hoja LEEME explica todo) |
| `resultados/Comparacion_sitios.xlsx` | Validaciones, sensibilidad y comparación entre sitios |
| `resultados/figuras/<sitio>/` | 01 series, 02 climatología, 04_temporadas (panel y medias móviles por temporada), 05 semanas, 06 mapas de calor, 07 ciclo anual, 08 efecto de las medias móviles |
| `resultados/figuras/comparacion/` | C1 validación T/lluvia, C1b validación horas HR ≥ 90 %, C2 climatología, C3 temporadas, C4 sensibilidad HR |
