"""平台原生服務產生自己帳號的驗證碼，再經HTTP確認／重用拒絕；不宣稱郵件送達。"""
import base64
import json
from pathlib import Path
import secrets
import uuid
from run_medusa_document_checks import TLSClient
from medusa_native_fixture_runner import native_fixture

HERE = Path(__file__).resolve().parent


def main():
    config = json.loads((HERE / '.runtime/medusa-demo.json').read_text(encoding='utf-8-sig'))
    c = TLSClient('https://127.0.0.1:18444', HERE / 'reports/medusa-demo-v9-verification-fixture-checks.json',
                  config['publishable_api_key'], HERE / '.runtime/medusa-document-check-tls.crt')
    email = 'verify-fixture-' + uuid.uuid4().hex + '@example.test'; password = secrets.token_urlsafe(24) + 'Aa1!'
    registration = c.request('POST', '/auth/customer/emailpass/register', {'email': email, 'password': password}, '/auth/customer/{auth_provider}/register')
    c.headers['Authorization'] = 'Bearer ' + registration['token']
    c.request('POST', '/store/customers', {'email': email})
    login = c.request('POST', '/auth/customer/emailpass', {'email': email, 'password': password}, '/auth/customer/{auth_provider}')
    c.headers['Authorization'] = 'Bearer ' + login['token']
    payload = login['token'].split('.')[1]
    identity = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4)))['auth_identity_id']
    requested = c.request('POST', '/auth/verification/request', {'entity_id': email, 'entity_type': 'email', 'code_provider': 'token'})
    c.verify(requested['verification']['entity_id'] == email and not requested['verification'].get('verified_at'), '原生HTTP驗證要求屬於自己帳號且尚未驗證', -1)
    native = native_fixture({'mode': 'verification', 'email': email, 'auth_identity_id': identity})
    c.remember({'token': native['token']})
    response = c.request('POST', '/auth/verification/confirm', {'code': native['token'], 'code_provider': 'token'})
    c.verify(response.get('entity_id') == email and response.get('entity_type') == 'email' and response.get('code_provider') == 'token'
             and bool(response.get('verified_at')), 'HTTP確認真實原生驗證碼後回傳同一帳號與非空verified_at', -1)
    c.rows[-1]['coverage_limitation'] = native['scope']
    c.request('POST', '/auth/verification/confirm', {'code': native['token'], 'code_provider': 'token'}, allowed_status={400, 401, 403})
    c.rows[-1]['negative_control'] = True
    c.verify(c.rows[-1]['status'] in (400, 401, 403), '同一驗證碼重用被拒絕，沒有冒稱可重複使用', -1)
    c.save('passed_with_unverified_email_delivery')
    print(json.dumps({'requests': len(c.rows), 'assertions': len(c.checks), 'email_delivery_verified': False}))


if __name__ == '__main__': main()
