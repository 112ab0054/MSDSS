"""Offline scientific-boundary and structure checks for small-api-v2."""
import csv
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'sentinel/dataset/small-api-v2'


def read_csv(name):
    with (DATA / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


class CompletedDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sets = {s: [json.loads(r['完整紀錄JSON']) for r in read_csv(s + '.csv')]
                    for s in ('train', 'test', 'validation')}
        cls.summary = json.loads((DATA / 'provenance.json').read_text(encoding='utf-8'))

    def test_ratio_labels_and_platforms(self):
        for split, count in [('train', 252), ('test', 84), ('validation', 84)]:
            rows = self.sets[split]
            self.assertEqual(len(rows), count)
            for label in ('normal', 'sqli', 'xss'):
                self.assertEqual(sum(r['annotation']['proposed_label'] == label for r in rows), count // 3)
            self.assertEqual({r['metadata']['platform'] for r in rows},
                             {'sylius'} if split == 'validation' else {'bagisto', 'shopware'})

    def test_no_overlap_or_historical_session_reuse_between_splits(self):
        sources, operations, requests, families = {}, {}, {}, {}
        for split, rows in self.sets.items():
            sources[split] = {r['metadata']['historical_source_report'] for r in rows}
            operations[split] = {(r['metadata']['platform'], r['input']['method'], r['metadata']['operation_path']) for r in rows}
            requests[split] = {json.dumps(r['input'], sort_keys=True) for r in rows}
            self.assertEqual(len(requests[split]), len(rows))
            families[split] = {(r['metadata']['payload'] or {}).get('family') for r in rows} - {None}
        for a, b in [('train', 'test'), ('train', 'validation'), ('test', 'validation')]:
            self.assertFalse(sources[a] & sources[b])
            self.assertFalse(operations[a] & operations[b])
            self.assertFalse(requests[a] & requests[b])
            self.assertFalse(families[a] & families[b])
        self.assertEqual(len(set.union(*operations.values())), 62)

    def test_natural_identity_and_control_references(self):
        """姓名／信箱不再使用固定測試字樣，且原始本文與對照 ID 同步更新。"""
        import re
        def inspect(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    field = key.lower().replace('_', '')
                    if field == 'firstname': self.assertNotEqual(child, 'MSDSS')
                    if field == 'lastname': self.assertNotEqual(child, 'Test')
                    if field in {'email', 'username'} and isinstance(child, str):
                        self.assertFalse(re.fullmatch(r'(phase1-[0-9a-f]+|customer)@example\.test', child, re.I))
                    inspect(child)
            elif isinstance(value, list):
                for child in value: inspect(child)
        for rows in self.sets.values():
            by_id = {r['sample_id']: r for r in rows}
            for row in rows:
                inspect(row['input']['body'])
                inspect(row['input']['query'])
                if row['input']['raw_body']:
                    self.assertEqual(json.loads(row['input']['raw_body']), row['input']['body'])
                control = row['metadata'].get('control_sample_id')
                if control:
                    self.assertIn(control, by_id)
                    self.assertEqual(row['metadata']['pair_group'], by_id[control]['metadata']['pair_group'])

    def test_schemas_replace_empty_objects_and_pseudo_body_field(self):
        baselines = [r for rows in self.sets.values() for r in rows if r['metadata']['variant'] == 'document_baseline']
        for row in baselines:
            req, meta = row['input'], row['metadata']
            body = req['body'] or {}
            self.assertNotIn('（本文）', body)
            for container in (req['query'], body):
                if meta['platform'] == 'shopware':
                    for name in ('associations', 'includes', 'excludes'):
                        if name in container:
                            self.assertTrue(container[name])
                    for name in ('reduce-aggregations', 'no-aggregations', 'only-aggregations'):
                        if name in container:
                            self.assertEqual(container[name], '1')
            if meta['platform'] == 'bagisto' and meta['operation_path'] == '/add-product-in-cart':
                for name in ('superAttribute', 'qty', 'bundleOptions', 'bundleOptionQty', 'booking'):
                    self.assertTrue(body[name])

    def test_all_fields_remain_visible_and_unresolved_fixtures_are_disclosed(self):
        fields = read_csv('field-coverage.csv')
        self.assertEqual(len(fields), 620)
        self.assertTrue(all(int(r['存在筆數']) > 0 for r in fields))
        self.assertFalse(any('${LIVE:' in r['填入值JSON'] for r in fields))
        self.assertTrue(any('商品種子待建立' in r['狀態'] for r in fields))
        self.assertEqual(self.summary['live_binding_markers_remaining'], 0)

    def test_source_documents_and_historical_evidence_match_saved_hashes(self):
        for path, expected in self.summary['parameter_document_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / path).read_bytes().replace(b'\r\n', b'\n')).hexdigest(), expected)
        # Historical digest modes may differ: the builder verifies these through refresh/verify_evidence.
        self.assertEqual(len(self.summary['historical_evidence_sha256']), 5)
        self.assertTrue(all((ROOT / p).is_file() for p in self.summary['historical_evidence_sha256']))

    def test_external_payload_preserved_and_no_live_success_claims(self):
        external = {(r['類別'], r['payload']) for r in read_csv('external-payloads.csv')}
        for split, rows in self.sets.items():
            for row in rows:
                req, meta = row['input'], row['metadata']
                self.assertFalse(meta['http_executed'])
                self.assertFalse(meta['training_approved'])
                self.assertFalse(meta['raw_body_captured'])
                self.assertFalse('${LIVE:' in json.dumps(req))
                self.assertEqual(json.loads(req['raw_body']) if req['raw_body'] else None, req['body'])
                if meta['payload'] and split == 'validation':
                    self.assertEqual(meta['payload']['source'], 'httpParamsDataset')
                    self.assertIn((row['annotation']['proposed_label'], meta['payload']['value']), external)

    def test_matched_triples_do_not_encode_label_in_header_presence(self):
        for rows in self.sets.values():
            pairs = {}
            for row in rows:
                pairs.setdefault(row['metadata']['pair_group'], []).append(row)
            for triple in pairs.values():
                self.assertEqual(len(triple), 3)
                self.assertEqual({r['annotation']['proposed_label'] for r in triple}, {'normal', 'sqli', 'xss'})
                normal = next(r for r in triple if r['annotation']['proposed_label'] == 'normal')
                for row in triple:
                    self.assertEqual(set(row['input']['headers']), set(normal['input']['headers']))
                    if row is not normal:
                        self.assertEqual(row['metadata']['control_sample_id'], normal['sample_id'])


if __name__ == '__main__':
    unittest.main()
