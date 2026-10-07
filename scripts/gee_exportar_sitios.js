// Google Earth Engine: exporta ERA5-Land + CHIRPS diarios para ambos sitios con el mismo
// formato del archivo "Climate SCG (ERA 5 Land & CHIRPS).csv". Alternativa a descargar_chirps.py.
// Pegar en https://code.earthengine.google.com y ejecutar; los CSV quedan en Tasks -> Drive.

var sitios = ee.FeatureCollection([
  ee.Feature(ee.Geometry.Point([-73.34229, 3.81687]), {sitio: 'delicias'}),
  ee.Feature(ee.Geometry.Point([-72.23030, 4.37769]), {sitio: 'taluma'})
]);
var inicio = '2011-01-01', fin = '2026-01-01';

var era5 = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR').filterDate(inicio, fin)
  .select(['temperature_2m_min', 'temperature_2m_max', 'surface_solar_radiation_downwards_sum']);
var chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').filterDate(inicio, fin).select('precipitation');

var dias = ee.List.sequence(0, ee.Date(fin).difference(ee.Date(inicio), 'day').subtract(1));
var tabla = ee.FeatureCollection(dias.map(function (n) {
  var d = ee.Date(inicio).advance(n, 'day');
  var img = era5.filterDate(d, d.advance(1, 'day')).first()
    .addBands(chirps.filterDate(d, d.advance(1, 'day')).first());
  return img.reduceRegions({collection: sitios, reducer: ee.Reducer.first(), scale: 5000})
    .map(function (f) {
      return f.set({
        Fecha: d.format('YYYY-MM-dd'),
        'Tmin (C)': ee.Number(f.get('temperature_2m_min')).subtract(273.15),
        'Tmax (C)': ee.Number(f.get('temperature_2m_max')).subtract(273.15),
        'Rad (W/m2)': ee.Number(f.get('surface_solar_radiation_downwards_sum')).divide(86400),
        'Prec (mm)': f.get('precipitation')
      });
    });
})).flatten();

['delicias', 'taluma'].forEach(function (s) {
  Export.table.toDrive({
    collection: tabla.filter(ee.Filter.eq('sitio', s)),
    description: 'clima_' + s + '_ERA5Land_CHIRPS',
    fileFormat: 'CSV',
    selectors: ['Fecha', 'Rad (W/m2)', 'Tmin (C)', 'Tmax (C)', 'Prec (mm)']
  });
});
