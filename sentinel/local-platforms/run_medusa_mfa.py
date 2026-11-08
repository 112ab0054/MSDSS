"""Real isolated TOTP lifecycle. All enrollment secrets and one-time codes are redacted."""
import base64
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import struct
import time
import uuid
from http_evidence import EvidenceClient

HERE = Path(__file__).resolve().parent


def totp(secret):
    key = base64.b32decode(secret.upper() + '=' * ((8 - len(secret) % 8) % 8))
    value = hmac.new(key, struct.pack('>Q', int(time.time()) // 30), hashlib.sha1).digest()
    offset = value[-1] & 15
    return str((struct.unpack('>I', value[offset:offset + 4])[0] & 0x7fffffff) % 1000000).zfill(6)


def main():
    config = json.loads((HERE / '.runtime/medusa.json').read_text(encoding='utf-8-sig'))
    c = EvidenceClient('medusa', 'http://127.0.0.1:18084',
        HERE / 'reports' / ('medusa-mfa-' + uuid.uuid4().hex + '.json'),
        {'x-publishable-api-key': config['publishable_api_key']})
    try:
        email = 'mfa-' + uuid.uuid4().hex + '@example.test'
        password = secrets.token_urlsafe(24) + 'Aa1!'
        auth = c.request('POST', '/auth/customer/emailpass/register', {'email': email, 'password': password}, '/auth/customer/{auth_provider}/register')
        c.headers['Authorization'] = 'Bearer ' + auth['token']
        customer = c.request('POST', '/store/customers', {'email': email})['customer']
        login = c.request('POST', '/auth/customer/emailpass', {'email': email, 'password': password}, '/auth/customer/{auth_provider}')
        c.headers['Authorization'] = 'Bearer ' + login['token']
        factors = c.request('GET', '/auth/mfa/factors')['mfa_factors']
        c.verify(factors == [], '全新實體顧客尚無 MFA 因子', -1)
        enrollment = c.request('POST', '/auth/mfa/factors', {'provider': 'totp', 'label': 'MSDSS local test', 'issuer': 'MSDSS'})
        enroll = len(c.rows) - 1
        factor = enrollment['mfa_factor']
        secret = enrollment['secret']
        c.verify(bool(secret) and bool(enrollment['otpauth_url']) and factor['status'] != 'enabled', '真實 TOTP 註冊取得秘密並處於尚未啟用狀態', enroll)
        code = totp(secret)
        c.remember({'token': code})
        verified = c.request('POST', '/auth/mfa/factors/' + factor['id'] + '/verify', {'code': code}, '/auth/mfa/factors/{id}/verify')['mfa_factor']
        verify_row = len(c.rows) - 1
        factors = c.request('GET', '/auth/mfa/factors')['mfa_factors']
        c.verify(verified['status'] == 'enabled' and any(f['id'] == factor['id'] and f['status'] == 'enabled' for f in factors), '真實 TOTP 驗證後重新查得相同啟用因子', verify_row, -1)
        recovery = c.request('POST', '/auth/mfa/recovery-codes', {'count': 3})
        c.verify(len(recovery['recovery_codes']) == 3 and len(set(recovery['recovery_codes'])) == 3, '啟用後產生三組不同備援碼；公開紀錄全部遮蔽', -1)
        # Recovery codes can also be used for disabling; this verifies native consumption.
        codes = recovery['recovery_codes']
        for value in codes:
            c.remember({'token': value})
        disabled = c.request('DELETE', '/auth/mfa/factors/' + factor['id'],
            {'method': 'recovery-code', 'code': codes[0]}, '/auth/mfa/factors/{id}')
        disable_row = len(c.rows) - 1
        factors = c.request('GET', '/auth/mfa/factors')['mfa_factors']
        c.verify(disabled['mfa_factor']['status'] == 'disabled' and not any(f['id'] == factor['id'] and f['status'] == 'enabled' for f in factors), '原生備援碼停用因子後重新確認未啟用', disable_row, -1)
        c.save('passed')
        print('MFA 流程通過；證據：', c.output)
        return 0
    except (RuntimeError, KeyError, TypeError, ValueError):
        c.save('failed', 'MFA 真實流程尚未通過；詳見遮蔽證據，秘密與驗證碼不顯示。')
        print('MFA 流程未通過；證據：', c.output)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
