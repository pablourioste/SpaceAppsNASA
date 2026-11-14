import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('adapter', ROOT/'scripts'/'build_comparator_data.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.cfg, self.targets, self.earth = [json.loads((ROOT/'app'/'data'/f).read_text(encoding='utf-8-sig')) for f in ('config.json','objetivos.json','tierra.json')]

    def test_counts_and_values_preserved(self):
        data = module.adapt(self.cfg, self.targets, self.earth)
        self.assertTrue(data['mock'])
        self.assertEqual(len(data['earth']), self.earth['n_cells'])
        moon = [t for t in self.targets['objetivos'] if t['body']=='moon']
        self.assertEqual(len(data['targets']), len(moon))
        for a, b in zip(data['targets'], moon):
            for k in module.KEYS:
                self.assertEqual(a['features'][k]['value'], b['features'].get(k))
        for i, a in enumerate(data['earth']):
            for k in module.KEYS:
                self.assertEqual(a['features'][k]['value'], self.earth['columns'][k][i])

    def test_real_requires_metadata(self):
        for x in (self.cfg,self.targets,self.earth): x.pop('_aviso',None)
        with self.assertRaisesRegex(ValueError,'metadata'): module.adapt(self.cfg,self.targets,self.earth)

    def test_mixed_provenance_rejected(self):
        self.targets.pop('_aviso')
        with self.assertRaisesRegex(ValueError,'Mezcla'): module.adapt(self.cfg,self.targets,self.earth)

    def test_column_lengths(self):
        self.earth['columns']['lat'].pop()
        with self.assertRaisesRegex(ValueError,'columnas'): module.adapt(self.cfg,self.targets,self.earth)

    def test_missing_value_stays_missing(self):
        self.earth['columns']['ice_depth_m'][0]=None
        data=module.adapt(self.cfg,self.targets,self.earth)
        self.assertEqual(data['earth'][0]['features']['ice_depth_m']['status'],'missing')

    def test_sentinels_rejected(self):
        self.earth['columns']['ice_depth_m'][0]=-999
        with self.assertRaisesRegex(ValueError,'sentinelas'): module.adapt(self.cfg,self.targets,self.earth)

if __name__=='__main__': unittest.main()
