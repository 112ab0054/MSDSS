"""依手寫文件補齊輸入，經驗證TLS測Cookie；不修改Medusa服務設定。"""
import argparse
import http.cookiejar
import json
from pathlib import Path
import secrets
import ssl
import urllib.parse
import urllib.request
import uuid
from http_evidence import EvidenceClient, NoRedirect, CaptureRequestHeaders
from run_medusa_remaining import CookieMetadata

HERE = Path(__file__).resolve().parent


class TLSClient(EvidenceClient):
    def __init__(self, base, output, key, ca):
        url = urllib.parse.urlsplit(base)
        if url.scheme != 'https' or url.hostname != '127.0.0.1' or url.username or url.password or url.path:
            raise ValueError('只允許明確本機HTTPS origin')
        super().__init__('medusa', 'http://127.0.0.1:' + str(url.port), output, {'x-publishable-api-key': key})
        self.base = base
        self.evidence_metadata = {'verification_target': base, 'tls_certificate_verification': True}
        context = ssl.create_default_context(cafile=str(ca))
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPSHandler(context=context), urllib.request.HTTPCookieProcessor(self.cookie_jar),
            CaptureRequestHeaders(self), CookieMetadata(self))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url', default='https://127.0.0.1:18443')
    p.add_argument('--config', type=Path, default=HERE / '.runtime/medusa-demo.json')
    p.add_argument('--ca', type=Path, default=HERE / '.runtime/medusa-document-check-tls.crt')
    p.add_argument('--output', type=Path, default=HERE / 'reports/medusa-demo-v9-document-input-checks.json')
    args = p.parse_args(); config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    c = TLSClient(args.base_url, args.output, config['publishable_api_key'], args.ca)
    email = 'document-' + uuid.uuid4().hex + '@example.test'; password = secrets.token_urlsafe(24) + 'Aa1!'
    auth = c.request('POST', '/auth/customer/emailpass/register', {'email': email, 'password': password}, '/auth/customer/{auth_provider}/register')
    c.headers['Authorization'] = 'Bearer ' + auth['token']
    customer = c.request('POST', '/store/customers', {'email': email})['customer']
    login = c.request('POST', '/auth/customer/emailpass', {'email': email, 'password': password}, '/auth/customer/{auth_provider}')
    c.headers['Authorization'] = 'Bearer ' + login['token']
    c.verify(c.request('GET', '/store/customers/me')['customer']['id'] == customer['id'], '先確認文件要求的一般登入JWT有效', -1)
    c.request('POST', '/auth/customer/emailpass/update', {'email': email, 'password': secrets.token_urlsafe(24) + 'Aa1!'},
              '/auth/customer/{auth_provider}/update', allowed_status={401})
    c.rows[-1]['document_input_check'] = '本次補齊文件的email與password；仍用一般登入JWT做負向對照，不冒充合法重設token'
    c.rows[-1]['negative_control'] = True
    c.rows[-1]['precondition_limitation'] = '依文件需reset-password通知token，與一般登入JWT不同；補email後仍401 Invalid token'
    c.request('POST', '/auth/session'); session = len(c.rows) - 1
    c.headers.pop('Authorization')
    me = c.request('GET', '/store/customers/me')
    observed = list(c.cookie_jar)
    c.verify(bool(observed) and all(x.secure for x in observed) and me['customer']['id'] == customer['id'],
             '真正HTTPS、驗證憑證、取得Secure Cookie後，移除Bearer仍讀回同一顧客', session, -1)
    c.rows[session]['verification_transport'] = 'https; trusted local certificate; proxy header derived from actual TLS scope'
    c.request('DELETE', '/auth/session'); logout = len(c.rows) - 1
    c.request('GET', '/store/customers/me', allowed_status={401, 403})
    c.verify(c.rows[-1]['status'] in (401, 403) and not list(c.cookie_jar),
             '真正Cookie session刪除後，Cookie已清除且同一HTTPS連線再查本人被拒絕', logout, -1)
    c.rows[logout]['verification_transport'] = 'https; actual Secure Cookie sent by CookieJar; no manually fabricated session'
    c.save('passed_with_documented_reset_token_precondition')
    print(json.dumps({'requests': len(c.rows), 'https_cookie_login_and_logout': True, 'tls_certificate_verification': True}, ensure_ascii=False))


if __name__ == '__main__': main()
