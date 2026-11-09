"""驗證語言實證、配對控制與原攻擊保留；不把模型分數當測試條件。"""
import copy
import json
import tempfile
import unittest
from collections import Counter, defaultdict
from pathlib import Path

from data_io import read_rows
from preflight import inspect_dataset
from train import groups

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'sentinel/dataset/small-api-v8'
OLD = ROOT / 'sentinel/dataset/small-api-v7'
SPLITS = ('train', 'test', 'validation', 'challenge')


class LiveLanguageTests(unittest.TestCase):
    def test_only_background_language_changed_and_payloads_preserved(self):
        changed = 0
        for split in SPLITS:
            before = read_rows(OLD / (split + '.csv'))
            after = read_rows(DATA / (split + '.csv'))
            self.assertEqual(len(before), len(after))
            for old, new in zip(before, after):
                expected = copy.deepcopy(old['input'])
                if expected != new['input']:
                    changed += 1
                    expected['headers']['sw-language-id'] = new['input']['headers']['sw-language-id']
                self.assertEqual(expected, new['input'])
                for field in ('split', 'platform', 'payload', 'skeleton_group_id'):
                    self.assertEqual(old['metadata'].get(field), new['metadata'].get(field))
                self.assertEqual(old['annotation'], new['annotation'])
                self.assertFalse(new['metadata']['http_executed'])
        self.assertEqual(changed, 145)

    def test_balanced_normals_and_symmetric_pair_languages(self):
        total = Counter()
        for split in SPLITS:
            pairs = defaultdict(list); counts = Counter()
            for row in read_rows(DATA / (split + '.csv')):
                pairs[row['metadata']['pair_group']].append(row)
                if row['annotation']['proposed_label'] == 'normal':
                    value = row['input']['headers'].get('sw-language-id')
                    if value:
                        counts[value] += 1; total[value] += 1
            if counts:
                self.assertEqual(len(counts), 2)
                self.assertLessEqual(max(counts.values()) - min(counts.values()), 1)
            for triple in pairs.values():
                normal = next(r for r in triple if r['annotation']['proposed_label'] == 'normal')
                value = normal['input']['headers'].get('sw-language-id')
                if not value:
                    continue
                for row in triple:
                    meta = row['metadata']
                    if meta.get('target_location') == 'header' and meta.get('target_parameter') == 'sw-language-id':
                        if row['annotation']['proposed_label'] != 'normal':
                            self.assertEqual(row['input']['headers']['sw-language-id'], meta['payload']['value'])
                        continue
                    self.assertEqual(row['input']['headers']['sw-language-id'], value)
        self.assertEqual(sorted(total.values()), [54, 57])

    def test_preflight_passes_and_modified_inventory_is_rejected(self):
        *_, report = inspect_dataset(DATA, groups, offline=True, evidence_root=ROOT)
        self.assertTrue(report['ready'], report['errors'])
        with tempfile.TemporaryDirectory() as directory:
            import shutil
            target = Path(directory)
            for path in DATA.iterdir():
                if path.is_file():
                    shutil.copy2(path, target / path.name)
            path = target / 'shopware-language-inventory.json'
            evidence = json.loads(path.read_text(encoding='utf-8'))
            evidence['languages'][0]['accepted'] = False
            path.write_text(json.dumps(evidence), encoding='utf-8')
            *_, bad = inspect_dataset(target, groups, offline=True, evidence_root=ROOT)
            self.assertFalse(bad['ready'])
            self.assertTrue(any('語言' in x for x in bad['errors']))


if __name__ == '__main__':
    unittest.main()
