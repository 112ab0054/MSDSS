"""Local-only HTTP evidence. Never a training-data collector."""
import datetime as dt
import hashlib
import http.cookiejar
import http.client
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

SENSITIVE = re.compile(r'password|passwd|authorization|cookie|token|secret|api.?key|access.?key|storefront.?key|session.?id|recovery.?codes|backup.?codes|otpauth|qr.?code', re.I)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class CaptureRequestHeaders(urllib.request.HTTPHandler):
    """在 Cookie 與 urllib 預設標頭加入後，保存實際送出前的 header。

    這是 HTTP 客戶端層的觀測，不宣稱是封包擷取；資料寫檔仍經 redact。
    不修改任何 header 或請求內容。
    """
    handler_order = 600

    def __init__(self, client):
        super().__init__()
        self.client = client

    def http_request(self, request):
        request = self.do_request_(request)
        if self.client.rows:
            headers = dict(request.header_items())
            self.client.remember(headers)
            self.client.rows[-1]['request_headers'] = headers
            self.client.rows[-1]['header_capture'] = 'urllib_pre_send'
        return request

    https_request = http_request

    def http_open(self, request):
        client = self.client

        class Connection(http.client.HTTPConnection):
            # http.client 還會自動加入 Accept-Encoding 等標頭，須在最終層觀測。
            def putheader(self, name, *values):
                if not hasattr(self, 'observed_headers'):
                    self.observed_headers = {}
                self.observed_headers[name] = ', '.join(str(v) for v in values)
                return super().putheader(name, *values)

            def endheaders(self, *args, **kwargs):
                client.remember(self.observed_headers)
                client.rows[-1]['request_headers'] = self.observed_headers.copy()
                client.rows[-1]['header_capture'] = 'http_client_sent_headers'
                return super().endheaders(*args, **kwargs)

        return self.do_open(Connection, request)


class EvidenceClient:
    def __init__(self, platform, base_url, output, headers=None):
        url = urllib.parse.urlsplit(base_url)
        if url.scheme != 'http' or url.hostname != '127.0.0.1' or url.username or url.password:
            raise ValueError('只允許明確的 http://127.0.0.1 本機測試位址')
        self.base = base_url.rstrip('/')
        self.platform = platform
        self.output = Path(output)
        self.headers = {'Accept': 'application/json', **(headers or {})}
        self.secrets = set()
        self.rows = []
        self.checks = []
        self.code_sha256 = {}
        for source in (Path(__file__), Path(sys.argv[0])):
            if source.is_file():
                self.code_sha256[source.name] = hashlib.sha256(source.read_bytes()).hexdigest()
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPCookieProcessor(self.cookie_jar), CaptureRequestHeaders(self))
        self.remember(self.headers)

    def remember(self, value):
        if isinstance(value, dict):
            for key, item in value.items():
                if SENSITIVE.search(key) and isinstance(item, (str, int)) and str(item):
                    self.secrets.add(str(item))
                self.remember(item)
        elif isinstance(value, list):
            for item in value:
                self.remember(item)

    def redact(self, value):
        if isinstance(value, dict):
            return {k: '[REDACTED]' if SENSITIVE.search(k) else self.redact(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.redact(v) for v in value]
        if isinstance(value, str):
            if value.lower().startswith('otpauth://'):
                return '[REDACTED]'
            for secret in sorted(self.secrets, key=len, reverse=True):
                # Short strings are masked by field name; replacing them globally destroys evidence.
                if len(secret) >= 6:
                    value = value.replace(secret, '[REDACTED]').replace(urllib.parse.quote(secret, safe=''), '[REDACTED]')
            return value
        return value

    def request(self, method, path, body=None, template=None, content_type='application/json', allowed_status=None):
        if not path.startswith('/') or path.startswith('//'):
            raise ValueError('請求路徑必須位於本機平台內')
        headers = dict(self.headers)
        request_id = str(uuid.uuid4())
        headers['X-Request-ID'] = request_id
        data = None
        if body is not None:
            headers['Content-Type'] = content_type
            data = json.dumps(body).encode()
        self.remember(headers)
        self.remember(body)
        row = {'request_id': request_id, 'method': method, 'path': path,
               'operation_path': template or path, 'request_headers': headers,
               'request_body': body, 'business_verified': False}
        self.rows.append(row)
        request = urllib.request.Request(self.base + path, data=data, headers=headers, method=method)
        try:
            response = self.opener.open(request, timeout=60)
        except urllib.error.HTTPError as error:
            response = error
        except (urllib.error.URLError, TimeoutError, OSError):
            row['transport_error'] = '本機連線失敗或逾時'
            self.save('blocked')
            raise RuntimeError('本機平台無法連線；未通過任何後續業務驗證') from None
        with response:
            row['status'] = response.status
            # Only safe, relevant headers; never dump server headers wholesale.
            row['response_headers'] = {key: response.headers[key] for key in
                ('Content-Type', 'sw-context-token', 'Location') if key in response.headers}
            self.remember(row['response_headers'])
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                row['response_body'] = {'omitted': '回應超過 2 MiB'}
                self.save('failed')
                raise RuntimeError('回應過大；停止驗證')
            try:
                payload = json.loads(raw) if raw else None
            except (ValueError, UnicodeError):
                payload = {'omitted': '非 JSON 回應不保存'}
            self.remember(payload)
            row['response_body'] = payload
            new_token = response.headers.get('sw-context-token')
            if isinstance(payload, dict):
                new_token = payload.get('contextToken') or new_token
            if new_token:
                self.headers['sw-context-token'] = new_token
                self.remember({'token': new_token})
        self.save('running')
        accepted = row['status'] in allowed_status if allowed_status is not None else 200 <= row['status'] < 300
        if not accepted:
            raise RuntimeError(f"HTTP {row['status']}：詳見已遮蔽的證據")
        if 200 <= row['status'] < 300 and isinstance(payload, dict) and payload.get('errors'):
            raise RuntimeError('回應包含錯誤；不能視為業務成功')
        return payload

    def verify(self, condition, description, *row_indexes):
        self.checks.append({'description': description, 'passed': bool(condition),
                            'request_ids': [self.rows[i]['request_id'] for i in row_indexes]})
        if not condition:
            self.save('failed')
            raise RuntimeError('業務核對失敗：' + description)
        for index in row_indexes:
            self.rows[index]['business_verified'] = True
        self.save('running')

    def save(self, outcome, error=None):
        result = {'platform': self.platform, 'recorded_at': dt.datetime.now(dt.timezone.utc).isoformat(),
                  'outcome': outcome, 'training_data': False, 'code_sha256': self.code_sha256, 'requests': self.rows,
                  'checks': self.checks, 'error': error}
        self.output.parent.mkdir(parents=True, exist_ok=True)
        temp = self.output.with_suffix('.tmp')
        temp.write_text(json.dumps(self.redact(result), ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(self.output)
