import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('prepare_remotion', ROOT / 'scripts/prepare_remotion.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestRemotion(unittest.TestCase):
    def test_two_compositions_have_real_sources(self):
        for name, path in mod.SPEC.items():
            data = mod.check_storyboard(name, json.loads(path.read_text(encoding='utf-8')))
            self.assertEqual(len(data['scenes']), 8)
            self.assertTrue(data['disclosure'])
            self.assertEqual(len({s['id'] for s in data['scenes']}), 8)
            self.assertTrue(all(s['action_ref'] and s['evidence_ref'] for s in data['scenes']))

    def test_hachimo_only_uses_abstract_schematics(self):
        name='HachimoPrepurchase'
        data=mod.check_storyboard(name, json.loads(mod.SPEC[name].read_text(encoding='utf-8')))
        self.assertEqual(data['kind'],'technical-schematic')
        self.assertTrue(all('diagram' in s and 'image_src' not in s for s in data['scenes']))
        self.assertIn('未',data['disclosure'])

    def test_tent_only_uses_real_own_images(self):
        data=mod.check_storyboard('ChristmasTentG0',json.loads(mod.SPEC['ChristmasTentG0'].read_text(encoding='utf-8')))
        self.assertEqual(data['kind'],'digital-simulation')
        self.assertTrue(all('image_src' in s and 'diagram' not in s for s in data['scenes']))

    def test_missing_evidence_rejected(self):
        data=json.loads(mod.SPEC['HachimoPrepurchase'].read_text(encoding='utf-8'))
        data['scenes'][0]['evidence_ref']='source-data/nope/does-not-exist.csv'
        with self.assertRaises(AssertionError):
            mod.check_storyboard('HachimoPrepurchase',data)

    def test_traversal_rejected(self):
        data=json.loads(mod.SPEC['ChristmasTentG0'].read_text(encoding='utf-8'))
        data['scenes'][0]['visual']='../../etc/passwd'
        with self.assertRaises(AssertionError):
            mod.check_storyboard('ChristmasTentG0',data)

    def test_provenance_can_be_prepared(self):
        r=mod.prepare(write=False)
        self.assertIn('ChristmasTentG0',r)
        self.assertIn('HachimoPrepurchase',r)


if __name__=='__main__':
    unittest.main()
