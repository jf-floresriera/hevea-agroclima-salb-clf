// Google Earth Engine: AgERA5 (diario, 0.1°) y GPM IMERG V07 (30 min -> resumen diario) en ambos sitios.
// 1) Pegar en https://code.earthengine.google.com  2) Run  3) Pestaña Tasks -> RUN en cada exportación.
// 4) Descargar los 8 CSV de Google Drive (carpeta 'clima_caucho') y copiarlos, sin renombrar, a
//    datos_crudos/gee/   (agera5_<sitio>.csv e imerg_<sitio>.csv para delicias, taluma, palomera, libertad).
// Luego ejecutar:  python scripts/analisis_clima.py   (las nuevas fuentes se incorporan solas).

var sitios = ee.FeatureCollection([
  ee.Feature(ee.Geometry.Point([-73.34229, 3.81687]), {sitio: 'delicias'}),
  ee.Feature(ee.Geometry.Point([-72.23030, 4.37769]), {sitio: 'taluma'}),
  // Estaciones automáticas IDEAM con HR horaria (validación)
  ee.Feature(ee.Geometry.Point([-72.564525, 4.260321]), {sitio: 'palomera'}),
  ee.Feature(ee.Geometry.Point([-73.467865, 4.057415]), {sitio: 'libertad'})
]);
var INICIO = '2011-01-01', FIN = '2026-01-01';
var nDias = ee.Date(FIN).difference(ee.Date(INICIO), 'day');
var dias = ee.List.sequence(0, nDias.subtract(1));

// ---------------- AgERA5 (catálogo comunitario de Climate Engine) ----------------
// Incluye HR a las 06, 09, 12, 15 y 18 h, T máx/mín/media, presión de vapor, lluvia, radiación, viento.
var agera5 = ee.ImageCollection('projects/climate-engine-pro/assets/ce-ag-era5-v2/daily')
  .filterDate(INICIO, FIN);
print('Bandas AgERA5:', agera5.first().bandNames());

var tablaAg = agera5.map(function (img) {
  return img.reduceRegions({collection: sitios, reducer: ee.Reducer.first(), scale: 10000})
    .map(function (f) { return f.set('fecha', img.date().format('YYYY-MM-dd')); });
}).flatten();

// ---------------- GPM IMERG V07 (lluvia cada 30 min) ----------------
// Por día: lluvia total (mm), horas con lluvia (>= 0.1 mm/h) e intensidad máxima (mm/h).
// Día en hora local de Colombia (UTC-5).
var imerg = ee.ImageCollection('NASA/GPM_L3/IMERG_V07').select('precipitation');

var tablaIm = ee.FeatureCollection(dias.map(function (n) {
  var d0 = ee.Date(INICIO).advance(n, 'day').advance(5, 'hour');  // 00:00 local = 05:00 UTC
  var c = imerg.filterDate(d0, d0.advance(1, 'day'));
  var total = c.sum().multiply(0.5).rename('imerg_mm');               // mm/h * 0.5 h
  var horas = c.map(function (i) { return i.gte(0.1); }).sum().multiply(0.5).rename('imerg_horas_lluvia');
  var imax = c.max().rename('imerg_max_mmh');
  var img = total.addBands(horas).addBands(imax);
  return img.reduceRegions({collection: sitios, reducer: ee.Reducer.first(), scale: 10000})
    .map(function (f) {
      return f.set('fecha', ee.Date(INICIO).advance(n, 'day').format('YYYY-MM-dd'));
    });
})).flatten();

['delicias', 'taluma', 'palomera', 'libertad'].forEach(function (s) {
  Export.table.toDrive({
    collection: tablaAg.filter(ee.Filter.eq('sitio', s)),
    description: 'agera5_' + s, folder: 'clima_caucho', fileNamePrefix: 'agera5_' + s,
    fileFormat: 'CSV'
  });
  Export.table.toDrive({
    collection: tablaIm.filter(ee.Filter.eq('sitio', s)),
    description: 'imerg_' + s, folder: 'clima_caucho', fileNamePrefix: 'imerg_' + s,
    fileFormat: 'CSV', selectors: ['fecha', 'imerg_mm', 'imerg_horas_lluvia', 'imerg_max_mmh']
  });
});
