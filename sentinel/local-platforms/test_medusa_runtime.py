"""狀態不能把路由探查或HTTP200誤當完整業務成功。"""
import json
from pathlib import Path
import unittest
from audit_medusa_runtime import classify, json_sha256
from import_gateway_scores import collect


class RuntimeStatusTests(unittest.TestCase):
    def test_empty_200_and_negative_404_are_not_passed(self):
        op = {'method': 'GET', 'path': '/store/return-reasons/{id}'}
        self.assertEqual(classify(op, [{'status': 200, 'response_body': {}, 'route_probe_only': True,
                          'precondition_limitation': 'no real ID'}], True)[0], 'blocked_prerequisite')
        self.assertEqual(classify(op, [{'status': 404, 'route_probe_only': True,
                          'precondition_limitation': 'no real ID'}], True)[0], 'blocked_prerequisite')

    def test_version_failure_and_partial_success_are_distinct(self):
        op = {'method': 'POST', 'path': '/store/search'}
        self.assertEqual(classify(op, [{'status': 404}], False)[0], 'unavailable_feature')
        self.assertEqual(classify(op, [{'status': 500}], True)[0], 'failed_runtime')
        op['path'] = '/store/carts/{id}/promotions'
        self.assertEqual(classify(op, [{'status': 200, 'business_verified': True}], True)[0], 'partial_pass')

    def test_json_fingerprint_survives_git_presentation_line_endings(self):
        value = {'raw_body': 'A\r\nB', 'raw_query': 'q=%3Cscript%3E'}
        outer = json.dumps(value, indent=2)
        self.assertEqual(json_sha256(json.loads(outer)), json_sha256(json.loads(outer.replace('\n', '\r\n'))))
        self.assertNotEqual(json_sha256(value), json_sha256(dict(value, raw_body='A\nB')))

    def test_manifest_all79_have_honest_runtime_status(self):
        root = Path(__file__).resolve().parents[2]
        value = json.loads((root / 'sentinel/analysis/api-extension/medusa-holdout-inventory.json').read_text(encoding='utf-8'))
        self.assertEqual(len(value['operations']), 79)
        self.assertTrue(all(o['runtime_status'] != 'not_run' and o['runtime_http_attempted'] for o in value['operations']))
        self.assertEqual(sum(value['runtime_verification']['status_counts'].values()), 79)
        self.assertEqual(value['runtime_verification']['not_run'], 0)

    def test_log_import_rejects_missing_or_conflicting_observations(self):
        uid = '12345678-1234-1234-1234-123456789abc'
        evidence = {'requests': [{'request_id': uid}]}
        line = 'prediction label=normal mode=offline exploratory=True request_id=' + uid + ' probabilities={"normal":0.8,"sqli":0.1,"xss":0.1}'
        self.assertEqual(collect(line, evidence)['scores'][0]['label'], 'normal')
        with self.assertRaises(ValueError): collect('', evidence)
        with self.assertRaises(ValueError): collect(line + '\n' + line.replace('label=normal', 'label=sqli'), evidence)

    def test_known_provider_and_disabled_translation_have_verified_reasons(self):
        proof = {'manual_fulfillment': {'can_calculate_false': True, 'calculate_price_explicit_error': True},
                 'tested_shipping_option': {'provider_id': 'manual_manual'}, 'translation_module_disabled': True}
        self.assertEqual(classify({'path': '/store/shipping-options/{id}/calculate'}, [{'status': 500}], True, proof)[0], 'blocked_prerequisite')
        status, reason = classify({'path': '/store/locales'}, [{'status': 404}], True, proof)
        self.assertEqual(status, 'unavailable_feature'); self.assertIn('disable=true', reason)

    def test_user_document_review_has_all_original32_and_byte_identity(self):
        root = Path(__file__).resolve().parents[2]
        proof = json.loads((root / 'sentinel/local-platforms/reports/medusa-demo-v9-user-document-audit.json').read_text(encoding='utf-8'))
        self.assertEqual(proof['reviewed_operations'], 32)
        self.assertEqual(proof['parsed_user_document_operations'], 77)
        import hashlib
        self.assertEqual(hashlib.sha256((root / 'sentinel/analysis/history/2026-11-09/medusa-77-user-reference.md').read_bytes()).hexdigest(), proof['user_document_sha256'])

    def test_tls_scheme_header_cannot_be_spoofed_by_client(self):
        import asyncio
        from unittest.mock import patch
        from tls_demo_gateway import TransportScheme
        seen = []
        async def fake(scope, receive, send): seen.append(scope)
        with patch('tls_demo_gateway.gateway', fake):
            asyncio.run(TransportScheme()({'type': 'http', 'scheme': 'https', 'headers': [(b'x-forwarded-proto', b'http')]}, None, None))
        self.assertEqual(dict(seen[0]['headers'])[b'x-forwarded-proto'], b'https')


if __name__ == '__main__': unittest.main()
