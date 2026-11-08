"""Privacy unit tests only; these do not validate any shopping platform."""
import json
from pathlib import Path
import tempfile
import unittest
from http_evidence import EvidenceClient


class EvidencePrivacyTests(unittest.TestCase):
    def test_mfa_enrollment_and_recovery_material_is_masked(self):
        c = EvidenceClient('medusa', 'http://127.0.0.1:18084', Path('unused.json'))
        data = {'secret': 'BASE32ENROLLMENTSECRET', 'otpauth_url': 'otpauth://totp/test?secret=BASE32ENROLLMENTSECRET',
                'recovery_codes': ['recovery-private-one', 'recovery-private-two'], 'qr_code': 'private-qr-data',
                'elsewhere': 'otpauth://totp/another?secret=hidden'}
        c.remember(data)
        encoded = json.dumps(c.redact(data))
        for secret in ('BASE32ENROLLMENTSECRET', 'otpauth://', 'recovery-private', 'private-qr-data'):
            self.assertNotIn(secret, encoded)

    def test_nested_credentials_and_token_in_iri(self):
        with tempfile.TemporaryDirectory() as directory:
            c = EvidenceClient('sylius', 'http://127.0.0.1:18083', Path(directory) / 'report.json')
            token = 'private-token-83a2a1'
            data = {'tokenValue': token, 'address': {'password': 'DoNotStoreMe'},
                    '@id': '/api/v2/shop/orders/' + token, 'quantity': 2}
            c.remember(data)
            encoded = json.dumps(c.redact(data))
            self.assertNotIn(token, encoded)
            self.assertNotIn('DoNotStoreMe', encoded)
            self.assertEqual(c.redact(data)['quantity'], 2)

    def test_headers_registration_and_query_are_masked(self):
        with tempfile.TemporaryDirectory() as directory:
            c = EvidenceClient('bagisto', 'http://127.0.0.1:18081', Path(directory) / 'report.json')
            data = {'Authorization': 'Bearer credential-abc123', 'Set-Cookie': 'sid=private-cookie',
                    'confirmPassword': 'confirm-secret-123', 'sw-access-key': 'access-secret-123',
                    'sw-context-token': 'context-secret-123', 'X-STOREFRONT-KEY': 'storefront-secret-123',
                    'nested': [{'api_key': 'api-secret-123'}]}
            c.remember(data)
            encoded = json.dumps(c.redact(data))
            for secret in ('credential-abc123', 'private-cookie', 'confirm-secret-123', 'access-secret-123',
                           'context-secret-123', 'api-secret-123', 'storefront-secret-123'):
                self.assertNotIn(secret, encoded)

    def test_disk_report_never_contains_raw_secrets(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'report.json'
            c = EvidenceClient('shopware', 'http://127.0.0.1:18082/store-api', output,
                               {'sw-access-key': 'key-known-secret-123'})
            c.rows.append({'request_headers': c.headers, 'request_body': {'password': 'password-known-secret'}})
            c.save('not_run')
            raw = output.read_text()
            self.assertNotIn('key-known-secret-123', raw)
            self.assertNotIn('password-known-secret', raw)
            self.assertFalse(json.loads(raw)['training_data'])

    def test_remote_and_credential_urls_rejected(self):
        for url in ('https://example.com', 'http://localhost:18082', 'http://127.0.0.1.evil.test',
                    'http://u:p@127.0.0.1:18082'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                EvidenceClient('test', url, Path('unused.json'))

    def test_protocol_relative_request_rejected_before_network(self):
        c = EvidenceClient('test', 'http://127.0.0.1:18082', Path('unused.json'))
        with self.assertRaises(ValueError):
            c.request('GET', '//example.com')


if __name__ == '__main__':
    unittest.main()
