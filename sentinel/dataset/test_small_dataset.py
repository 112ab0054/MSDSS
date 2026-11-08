"""Offline checks for the committed small candidate dataset, not platform success."""
import csv
import json
from pathlib import Path
import unittest
from urllib.parse import parse_qs, unquote

from build_small_dataset import read_documents

DATA = Path(__file__).resolve().parent / 'small-api-v1'


class SmallDatasetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sets = {}
        for split in ('train', 'test', 'validation'):
            with (DATA / f'{split}.csv').open(encoding='utf-8-sig', newline='') as f:
                cls.sets[split] = [json.loads(r['完整紀錄JSON']) for r in csv.DictReader(f)]

    def test_body_fields_named_query_are_not_url_parameters(self):
        operations, _ = read_documents()
        fields = operations['shopware', 'POST', '/search']['fields']
        self.assertIn(('body', 'query'), fields)
        self.assertNotIn(('query', '選填'), fields)
        self.assertNotIn(('query', 'query'), fields)

    def test_platform_operations_and_request_values_do_not_cross_splits(self):
        operations, values = {}, {}
        for split, rows in self.sets.items():
            self.assertEqual({r['annotation']['proposed_label'] for r in rows}, {'normal', 'sqli', 'xss'})
            self.assertEqual({r['metadata']['platform'] for r in rows},
                             {'sylius'} if split == 'validation' else {'bagisto', 'shopware'})
            operations[split] = {(r['metadata']['platform'], r['input']['method'], r['metadata']['operation_path']) for r in rows}
            values[split] = {json.dumps(r['input'], sort_keys=True) for r in rows}
        self.assertEqual(len(set.union(*operations.values())), 62)
        for a, b in [('train', 'test'), ('train', 'validation'), ('test', 'validation')]:
            self.assertFalse(operations[a] & operations[b])
            self.assertFalse(values[a] & values[b])
        families = [{r['metadata']['payload']['family'] for r in self.sets[s] if r['metadata']['payload']}
                    for s in ('train', 'test')]
        self.assertFalse(families[0] & families[1])

    def test_serialized_body_query_headers_and_payload_match(self):
        for rows in self.sets.values():
            for row in rows:
                req, meta = row['input'], row['metadata']
                self.assertTrue(all(isinstance(v, str) for v in req['headers'].values()))
                headers = {k.lower() for k in req['headers']}
                self.assertFalse({'sw-context-token', 'sw-context-source'} <= headers)
                if 'sw-context-source' in headers:
                    self.assertIn('cookie', headers)
                self.assertEqual(json.loads(req['raw_body']) if req['raw_body'] else None, req['body'])
                decoded = parse_qs(req['raw_query'], keep_blank_values=True)
                for name, value in req['query'].items():
                    if isinstance(value, dict) and value:
                        for child, item in value.items():
                            self.assertEqual(decoded[f'{name}[{child}]'], [str(item)])
                        continue
                    if isinstance(value, (dict, list)) and not value:
                        self.assertEqual(decoded[name], [json.dumps(value)])
                        continue
                    expected = [str(v) for v in value] if isinstance(value, list) else [str(value)]
                    self.assertEqual(decoded[name], expected)
                if meta['payload'] and meta['target_location'] == 'path':
                    self.assertIn(meta['payload']['value'], unquote(req['path']))
                self.assertFalse(meta['training_approved'])
                self.assertFalse(meta['http_executed'])
                self.assertFalse(meta['raw_target_captured'])

    def test_external_source_only_in_validation_and_original_values_retained(self):
        with (DATA / 'external-payloads.csv').open(encoding='utf-8-sig', newline='') as f:
            external = {(r['類別'], r['payload']) for r in csv.DictReader(f)}
        self.assertEqual(len(external), 24)
        for split, rows in self.sets.items():
            for row in rows:
                payload = row['metadata']['payload']
                if not payload:
                    continue
                if split == 'validation':
                    self.assertEqual(payload['source'], 'httpParamsDataset')
                    self.assertIn((row['annotation']['proposed_label'], payload['value']), external)
                else:
                    self.assertEqual(payload['source'], 'local_scenario_catalog')
                    self.assertNotIn(payload['value'], {v for _, v in external})

    def test_field_coverage_is_complete_and_pending_values_are_not_claimed_verified(self):
        with (DATA / 'field-coverage.csv').open(encoding='utf-8-sig', newline='') as f:
            fields = list(csv.DictReader(f))
        self.assertEqual(len(fields), 620)
        self.assertEqual({r['位置'] for r in fields}, {'header', 'query', 'path', 'body'})
        self.assertTrue(all(int(r['候選中存在筆數']) > 0 for r in fields))
        self.assertTrue(all(r['實機已驗證'] == 'False' for r in fields))
        self.assertTrue(any(r['填入狀態'] == '待綁定憑證／實例值' for r in fields))


if __name__ == '__main__':
    unittest.main()
