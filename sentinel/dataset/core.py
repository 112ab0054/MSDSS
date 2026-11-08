"""Dataset boundaries: request-only model input, traceability, review and grouping."""
import hashlib
import json
from pathlib import Path
import re
import urllib.parse

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'sentinel/analysis/api-extension/active-api-manifest.json'
PRIVATE = re.compile(r'password|passwd|authorization|cookie|token|secret|api.?key|access.?key|storefront.?key|session.?id|recovery.?codes|backup.?codes|otpauth|qr.?code', re.I)
IDENTIFIER = re.compile(r'(^id$|Id$|_id$|^ids$|^referencedId$)', re.I)
HEADERS = {'accept', 'content-type', 'accept-language'}
LABELS = ('normal', 'sqli', 'xss')


def sha(value):
    raw = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()


def manifest():
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    if len(data['operations']) != data['operation_count'] or data['operation_count'] != 62:
        raise ValueError('採用清單改變；須先審查採集範圍')
    return data


def scrub(value, key=''):
    if PRIVATE.search(key):
        return '[REDACTED]'
    if IDENTIFIER.search(key) and value is not None:
        return '[ID]'
    if isinstance(value, dict):
        return {k: scrub(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v, key.rstrip('s')) for v in value]
    if isinstance(value, str):
        if value.lower().startswith('otpauth://'):
            return '[REDACTED]'
        # IRI/resource identifiers embedded in body fields are also normalized.
        value = re.sub(r'(/api/v2/shop/orders/)[^/?\s]+', r'\1[ID]', value)
        value = re.sub(r'(?<![\w])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w])', '[EMAIL]', value)
        return value
    return value


def model_input(row, version=2):
    url = urllib.parse.urlsplit(row['path'])
    query = urllib.parse.parse_qs(url.query, keep_blank_values=True, max_num_fields=1000)
    if version == 1:
        # 舊證據必須照當時白名單還原，避免更版使已保存的對帳失效。
        return {'method': row['method'], 'path': row['operation_path'], 'query': scrub(query),
                'headers': {k.lower(): v for k, v in row.get('request_headers', {}).items() if k.lower() in HEADERS},
                'body': scrub(row.get('request_body'))}
    if version != 2:
        raise ValueError('不支援的請求輸入版本')
    # 不依參數白名單挑欄位：保留完整 query、本文與所有實際擷取到的 header。
    # 只將敏感值遮蔽、追蹤 ID 正規化，不保存可用憑證。
    headers = {}
    for key, value in row.get('request_headers', {}).items():
        name = key.lower()
        headers[name] = '[ID]' if name in {'x-request-id', 'traceparent', 'tracestate'} else scrub(value, name)
    # URL 仍保存路由模板；各 path 參數另存，讓路徑中的惡意字串也能被檢查。
    pattern = '^' + re.sub(r'\\\{[^}]+\\\}', '([^/]+)', re.escape(row['operation_path'])) + '$'
    match = re.match(pattern, url.path)
    names = re.findall(r'\{([^}]+)\}', row['operation_path'])
    path_parameters = {name: ('[REDACTED]' if PRIVATE.search(name) else urllib.parse.unquote(value))
                       for name, value in zip(names, match.groups() if match else [])}
    return {'method': row['method'], 'path': row['operation_path'], 'query': scrub(query),
            'headers': headers, 'body': scrub(row.get('request_body')),
            'path_parameters': path_parameters}



def near_fingerprint(request):
    # Conservative literal-level approximation, not a claim of semantic deduplication.
    text = json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(',', ':')).lower()
    text = re.sub(r'\b\d+\b', '#', text)
    text = re.sub(r'\s+', ' ', text)
    return sha(text)


def sample(platform, source, row, batch, label='normal', family=None, pair=None,
           kind='historical_reference', proposed=None, eligibility=True, reason=None, versions=None):
    if label not in LABELS:
        raise ValueError('不支援的標籤')
    selected = manifest()
    key = platform, row['method'], row['operation_path']
    if key not in {(o['platform'], o['method'], o['path']) for o in selected['operations']}:
        raise ValueError('非採用操作')
    request = model_input(row)
    valid = not row.get('transport_error') and isinstance(row.get('status'), int)
    return {'sample_id': sha([source, row['request_id']]), 'input': request,
            'annotation': {'proposed_label': proposed or label, 'review_status': 'pending_human_review',
                'label_basis': reason or '完整 passed 正常流程內、具業務斷言的非攻擊請求',
                'eligible_for_review': bool(eligibility and valid)},
            'metadata': {'platform': platform, 'versions': versions or {}, 'origin': kind,
                'batch_id': batch, 'session_group': batch, 'family_id': family,
                'request_input_version': 2,
                'pair_group': pair, 'source_evidence': source, 'request_id': row['request_id'],
                'manifest_sha256': sha(MANIFEST.read_bytes()), 'source_contract_sha256': selected['sources'][platform]['sha256'],
                'fingerprint': sha(request), 'near_fingerprint': near_fingerprint(request), 'http_status': row.get('status'),
                'business_verified': bool(row.get('business_verified')), 'training_approved': False}}


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows), encoding='utf-8')
    temp.replace(path)


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


def evidence_digest_mode(raw, expected):
    """跨 Windows/Linux 檢查既存 SHA，不更改預期雜湊或證據檔。

    Git checkout 可能將 CRLF 改為 LF。僅當重建原換行後的完整位元組
    SHA 確實等於原紀錄才接受，不接受任意內容的重新雜湊。
    """
    if sha(raw) == expected:
        return 'exact_bytes'
    lf = raw.replace(b'\r\n', b'\n')
    if sha(lf) == expected:
        return 'original_lf_reconstructed'
    if sha(lf.replace(b'\n', b'\r\n')) == expected:
        return 'original_crlf_reconstructed'
    return None


def verify_evidence(row):
    """Bind an export to an existing local HTTP artifact, not just a proposed label."""
    meta = row['metadata']
    source = (ROOT / meta.get('source_evidence', '')).resolve()
    allowed = [(ROOT / 'sentinel/local-platforms/reports').resolve(),
               (ROOT / 'sentinel/dataset/evidence').resolve()]
    if not any(source.is_relative_to(folder) for folder in allowed) or not source.is_file():
        return False
    raw = source.read_bytes()
    if not evidence_digest_mode(raw, meta.get('source_evidence_sha256')):
        return False
    data = json.loads(raw)
    if not isinstance(data, dict) or data.get('platform') != meta['platform']:
        return False
    matches = [r for r in data.get('requests', []) if r.get('request_id') == meta.get('request_id')]
    return len(matches) == 1 and not matches[0].get('transport_error') and matches[0].get('status') == meta.get('http_status') and model_input(matches[0], version=meta.get('request_input_version', 1)) == row['input']


def grouped(rows):
    """Conservative connected components; never split sessions, families or exact duplicates."""
    parents = list(range(len(rows)))
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parents[max(a, b)] = min(a, b)
    seen = {}
    for i, row in enumerate(rows):
        meta = row['metadata']
        for field in ('session_group', 'family_id', 'pair_group', 'fingerprint', 'near_fingerprint'):
            value = meta.get(field)
            if not value:
                continue
            key = field, value
            if key in seen:
                union(i, seen[key])
            else:
                seen[key] = i
    return [f'group-{find(i):06d}' for i in range(len(rows))]


def numeric_features(request):
    """Stateless B-method measurements; no labels, responses or platform metadata."""
    text = json.dumps({'query': request['query'], 'body': request['body']}, ensure_ascii=False, sort_keys=True)
    n = max(len(text), 1)
    return {'length': len(text), 'quote_ratio': (text.count("'") + text.count('"')) / n,
            'angle_ratio': (text.count('<') + text.count('>')) / n,
            'percent_ratio': text.count('%') / n, 'non_ascii_ratio': sum(ord(c) > 127 for c in text) / n,
            'query_fields': len(request['query']), 'body_present': int(request['body'] is not None)}
