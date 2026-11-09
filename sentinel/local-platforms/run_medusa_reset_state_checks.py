"""實際HTTP要求重設密碼，唯讀確認Token產生／輪替，並驗證舊Token被拒絕。"""
import json
from pathlib import Path
import re
import secrets
import uuid
from medusa_native_fixture_runner import native_fixture
from run_medusa_document_checks import TLSClient
from run_medusa_native_transfer_tokens import db_query

HERE = Path(__file__).resolve().parent


def token_rows(email):
    if not re.fullmatch(r'[A-Za-z0-9@._+-]+', email): raise ValueError('僅接受本輪自建測試帳號')
    return db_query("SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT id,entity_id,created_at,expires_at FROM auth_password_reset_token WHERE entity_id='" + email + "' AND deleted_at IS NULL ORDER BY created_at) t")


def main():
    config = json.loads((HERE / '.runtime/medusa-demo.json').read_text(encoding='utf-8-sig'))
    c = TLSClient('https://127.0.0.1:18444', HERE / 'reports/medusa-demo-v9-reset-state-checks.json',
                  config['publishable_api_key'], HERE / '.runtime/medusa-document-check-tls.crt')
    email = 'reset-state-' + uuid.uuid4().hex + '@example.test'; password = secrets.token_urlsafe(24) + 'Aa1!'
    registration = c.request('POST', '/auth/customer/emailpass/register', {'email': email, 'password': password}, '/auth/customer/{auth_provider}/register')
    c.headers['Authorization'] = 'Bearer ' + registration['token']
    customer = c.request('POST', '/store/customers', {'email': email})['customer']
    login = c.request('POST', '/auth/customer/emailpass', {'email': email, 'password': password}, '/auth/customer/{auth_provider}')
    c.headers['Authorization'] = 'Bearer ' + login['token']
    c.verify(c.request('GET', '/store/customers/me')['customer']['id'] == customer['id'], '確認本輪帳號存在且可登入', -1)
    native = native_fixture({'mode': 'reset', 'email': email}); c.remember({'token': native['token']})
    before = token_rows(email)
    c.headers.pop('Authorization')
    c.request('POST', '/auth/customer/emailpass/reset-password', {'identifier': email}, '/auth/customer/{auth_provider}/reset-password')
    first_row = len(c.rows)-1; after_first = token_rows(email)
    c.verify(len(before) == 1 and len(after_first) == 1 and before[0]['id'] != after_first[0]['id'],
             'HTTP重設請求確實產生新的持久化Token資料列，舊資料列已失效', first_row)
    c.rows[first_row]['reset_request_token_persisted'] = True
    c.rows[first_row]['document_request_validated'] = True
    c.rows[first_row]['coverage_limitation'] = '已唯讀證實HTTP產生原生Token；未觀測事件消費或郵件送達，不將其他程序的原生Token當成本次HTTP回傳'
    c.headers['Authorization'] = 'Bearer ' + native['token']
    c.request('POST', '/auth/customer/emailpass/update', {'email': email, 'password': secrets.token_urlsafe(24)+'Bb2!'},
              '/auth/customer/{auth_provider}/update', allowed_status={401})
    c.rows[-1]['negative_control'] = True
    c.verify(c.rows[-1]['status'] == 401, 'HTTP發出新重設要求後，先前原生reset JWT被拒絕', -1)
    c.headers.pop('Authorization')
    login = c.request('POST', '/auth/customer/emailpass', {'email': email, 'password': password}, '/auth/customer/{auth_provider}')
    c.headers['Authorization'] = 'Bearer '+login['token']
    c.verify(c.request('GET', '/store/customers/me')['customer']['id'] == customer['id'], '被拒絕的舊reset JWT沒有改掉原密碼，仍登入同一帳號', -1)
    c.headers.pop('Authorization')
    c.request('POST', '/auth/customer/emailpass/reset-password', {'identifier': email}, '/auth/customer/{auth_provider}/reset-password')
    second_row = len(c.rows)-1; after_second = token_rows(email)
    c.verify(len(after_second) == 1 and after_second[0]['id'] != after_first[0]['id'], '再次HTTP要求重設，僅保留最新有效Token資料列', second_row)
    c.rows[second_row]['reset_request_token_persisted'] = True
    c.rows[second_row]['document_request_validated'] = True
    missing = 'unregistered-reset-' + uuid.uuid4().hex + '@example.test'
    c.request('POST', '/auth/customer/emailpass/reset-password', {'identifier': missing}, '/auth/customer/{auth_provider}/reset-password')
    c.rows[-1]['negative_control'] = True
    c.verify(c.rows[-1]['status'] == 201 and token_rows(missing) == [], '不存在帳號也回201但不產生Token，證明201不能單獨作成功證據', -1)
    proof = {'scope': 'only own new identity; all database observations BEGIN READ ONLY / ROLLBACK; no token hashes or values published',
             'customer_id': customer['id'], 'before': before, 'after_first_http': after_first, 'after_second_http': after_second,
             'http_first_request_id': c.rows[first_row]['request_id'], 'http_second_request_id': c.rows[second_row]['request_id'],
             'old_native_token_rejected': True, 'event_consumer_observed': False, 'email_delivery_verified': False}
    (HERE / 'reports/medusa-demo-v9-reset-state-proof.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding='utf-8')
    c.save('token_generation_and_invalidation_verified_event_delivery_unobserved')
    print(json.dumps({'requests': len(c.rows), 'assertions': len(c.checks), 'http_token_generation_verified': True, 'event_delivery_verified': False}))


if __name__ == '__main__': main()
