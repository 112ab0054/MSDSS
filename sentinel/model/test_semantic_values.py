"""確保語義多樣性、來源對照與攻擊配對仍完整；不檢查模型分數。"""
import copy
import csv
import json
import sys
import unittest
from collections import defaultdict
from pathlib import Path

from data_io import read_rows
from preflight import inspect_dataset
from semantic_values import audit_semantic_values
from train import groups

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'sentinel/dataset'))
from build_xss_v3 import set_field
from build_small_dataset import finalize
DATA = ROOT / 'sentinel/dataset/small-api-v9'
OLD = ROOT / 'sentinel/dataset/small-api-v8'
SPLITS = ('train', 'test', 'validation', 'challenge')


class SemanticValueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sets = {s: read_rows(DATA / (s + '.csv')) for s in SPLITS}
        cls.provenance = json.loads((DATA / 'provenance.json').read_text(encoding='utf-8'))

    def test_labels_split_payload_skeleton_and_pair_background_preserved(self):
        count = 0
        for split in SPLITS:
            old = {r['sample_id']: r for r in read_rows(OLD / (split + '.csv'))}; pairs = defaultdict(list)
            for row in self.sets[split]:
                previous = old[row['metadata']['semantic_source_sample_id']]
                self.assertEqual(row['annotation'], previous['annotation'])
                for field in ('platform', 'split', 'payload', 'skeleton_group_id', 'benign_content_context'):
                    self.assertEqual(row['metadata'].get(field), previous['metadata'].get(field))
                self.assertFalse(row['metadata']['http_executed'])
                pairs[row['metadata']['pair_group']].append(row); count += 1
            for triple in pairs.values():
                normal = next(r for r in triple if r['annotation']['proposed_label'] == 'normal')
                for row in triple:
                    if row is normal: continue
                    expected = copy.deepcopy(normal['input']); meta = row['metadata']
                    set_field(expected, meta['target_location'], meta['target_parameter'], meta['payload']['value'])
                    finalize(expected, meta['operation_path'])
                    self.assertEqual(expected, row['input'])
                    self.assertEqual(meta['control_sample_id'], normal['sample_id'])
        self.assertEqual(count, 1098)

    def test_database_languages_and_free_text_diversity(self):
        headers = defaultdict(set)
        for rows in self.sets.values():
            for r in rows:
                if r['annotation']['proposed_label'] != 'normal': continue
                for name in ('X-Locale', 'Accept-Language'):
                    if name in r['input']['headers']: headers[name].add(r['input']['headers'][name])
        self.assertEqual(headers['X-Locale'], {'en'})
        self.assertEqual(headers['Accept-Language'], {'en_US', 'de_DE', 'es_ES', 'es_MX', 'fr_FR', 'pl_PL', 'pt_PT', 'zh_CN'})
        with (DATA / 'free-text-diversity.csv').open(encoding='utf-8-sig', newline='') as f:
            for r in csv.DictReader(f):
                self.assertNotEqual(r['strategy'], 'needs_semantic_review')
                if r['strategy'] == 'semantic_free_text' and int(r['normal_occurrences']) >= 3:
                    self.assertGreaterEqual(int(r['after_unique']), 3, r['parameter'])

    def test_preflight_and_inconsistent_address_or_unknown_language_rejected(self):
        *_, report = inspect_dataset(DATA, groups, offline=True, evidence_root=ROOT)
        self.assertTrue(report['ready'], report['errors'])
        sets = copy.deepcopy(self.sets)
        row = next(r for r in sets['train'] if r['annotation']['proposed_label'] == 'normal'
                   and r['metadata']['platform'] == 'bagisto' and 'country' in (r['input']['body'] or {}))
        row['input']['body']['country'] = 'ZZ'
        self.assertTrue(audit_semantic_values(DATA, sets, self.provenance))
        sets = copy.deepcopy(self.sets)
        row = next(r for r in sets['validation'] if r['annotation']['proposed_label'] == 'normal'
                   and 'Accept-Language' in r['input']['headers'])
        row['input']['headers']['Accept-Language'] = 'fr_GQ'  # 文件有列，但資料庫未建立。
        self.assertTrue(audit_semantic_values(DATA, sets, self.provenance))


if __name__ == '__main__': unittest.main()
