"""Adapta app/data al comparador. No descarga ni modifica datos originales."""
import argparse
import hashlib
import json
import math
from pathlib import Path

KEYS = ('slope_deg', 'roughness_deg', 't_mean_K', 'ice_depth_m')
ROOT = Path(__file__).resolve().parents[1]


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def adapt(config, targets, earth, metadata=None):
    flags = [bool(x.get('_aviso')) for x in (config, targets, earth)]
    if len(set(flags)) != 1:
        raise ValueError('Mezcla de archivos simulados y no simulados; revisar el paquete.')
    mock = all(flags)
    if mock and not all('DATOS FALSOS' in x['_aviso'] for x in (config, targets, earth)):
        raise ValueError('Aviso desconocido; no se puede determinar la procedencia.')
    if not mock and not metadata:
        raise ValueError('Datos sin aviso de simulacion: requieren --metadata con definiciones, unidades, fuentes y escalas por cuerpo.')
    variables = {}
    for k in KEYS:
        v = config['variables'][k]
        if not number(v.get('tolerance')) or v['tolerance'] <= 0:
            raise ValueError('Tolerancia invalida: ' + k)
        variables[k] = {'label': v.get('label', k), 'tolerance': v['tolerance']}
    cols = earth['columns']
    n = earth['n_cells']
    if not isinstance(n, int) or n < 1 or any(not isinstance(v, list) or len(v) != n for v in cols.values()):
        raise ValueError('Las columnas de tierra deben tener n_cells elementos.')
    if not all(k in cols for k in ('cell_id', 'lat', 'lon')):
        raise ValueError('Faltan identificadores o coordenadas terrestres.')

    def measure(k, value, body):
        if mock:
            meta = {'unit': {'slope_deg':'deg','roughness_deg':'deg','t_mean_K':'K','ice_depth_m':'m'}[k],
                    'definition': 'simulacion:' + k, 'scale_m': 800 if k in KEYS[:2] else None,
                    'source': 'DATOS FALSOS: scripts/make_mock_data.py; escala de prueba, no medida'}
        else:
            meta = dict(metadata.get(body, {}).get(k, {}))
            for field in ('unit', 'definition', 'source'):
                if not isinstance(meta.get(field), str) or not meta[field].strip():
                    raise ValueError(f'Falta {body}.{k}.{field}')
            if k in KEYS[:2] and (not number(meta.get('scale_m')) or meta['scale_m'] <= 0):
                raise ValueError(f'Falta escala valida en {body}.{k}')
        if value is None:
            return {**meta, 'value': None, 'status': 'missing'}
        # Los sentinelas deben venir interpretados por el equipo, nunca inferidos aqui.
        if not number(value) or value < 0:
            raise ValueError(f'Valor no valido en {body}.{k}: {value}; interpretar sentinelas antes de exportar.')
        return {**meta, 'value': value, 'status': 'value'}

    def site(row, body):
        lat, lon = row.get('lat'), row.get('lon')
        if not number(lat) or not number(lon) or abs(lat) > 90 or abs(lon) > 180:
            raise ValueError('Coordenadas invalidas: ' + str(row.get('id')))
        return {'id': str(row['id']), 'name': str(row.get('name') or row['id']),
                'lat': lat, 'lon': lon,
                'features': {k: measure(k, row.get('features', {}).get(k), body) for k in KEYS}}
    moon = [site(t, 'moon') for t in targets['objetivos'] if t.get('body') == 'moon']
    if not moon:
        raise ValueError('No hay objetivos lunares.')
    cells = [site({'id':cols['cell_id'][i], 'name':cols.get('name',cols['cell_id'])[i],
                   'lat':cols['lat'][i], 'lon':cols['lon'][i],
                   'features':{k:cols[k][i] if k in cols else None for k in KEYS}}, 'earth') for i in range(n)]
    for group in (moon, cells):
        if len({s['id'] for s in group}) != len(group):
            raise ValueError('Identificadores duplicados.')
    return {'schema_version':1, 'mock':mock, 'variables':variables, 'targets':moon, 'earth':cells}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=ROOT/'app'/'data')
    parser.add_argument('--output-dir', type=Path, default=ROOT/'app')
    parser.add_argument('--metadata', type=Path)
    parser.add_argument('--revision', default='local')
    args = parser.parse_args()
    files = [args.input_dir/name for name in ('config.json','objetivos.json','tierra.json')]
    try:
        source = [json.loads(f.read_text(encoding='utf-8-sig')) for f in files]
        meta = json.loads(args.metadata.read_text(encoding='utf-8-sig')) if args.metadata else None
        data = adapt(*source, metadata=meta)
        data['provenance'] = {'repository':'marcantich/SpaceAppsNASA','revision':args.revision,
                              'files':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
        payload = json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(',',':'))
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir/'repository-data.json').write_text(payload, encoding='utf-8')
        (args.output_dir/'repository-data.js').write_text('window.REPOSITORY_DATA = '+payload.replace('<','\\u003c')+';\n', encoding='utf-8')
        print(f"Integrados {len(data['targets'])} objetivos lunares y {len(data['earth'])} celdas. Simulados: {data['mock']}")
    except (ValueError, KeyError, TypeError, OSError) as exc:
        parser.exit(1, f'No se ha generado el paquete: {exc}\n')


if __name__ == '__main__':
    main()
