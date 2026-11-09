"""Raw-value request input shared by collection, training and serving.

Only credential values are redacted. IDs, emails, case, whitespace, hosts and
encoded spellings are not normalized. Parsed views are separate from raw text.
"""
import json
import re
from urllib.parse import parse_qs, unquote_plus, urlsplit

INPUT_VERSION = 3
SENSITIVE = re.compile(r'password|passwd|authorization|cookie|token|secret|api.?key|access.?key|storefront.?key|session.?id|recovery.?codes|backup.?codes|otpauth|qr.?code', re.I)
REDACTED = '[REDACTED]'


def redact_fields(value, key=''):
    if SENSITIVE.search(key):
        return REDACTED
    if isinstance(value, dict):
        return {k: redact_fields(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_fields(v) for v in value]
    if isinstance(value, str) and value.lower().startswith('otpauth://'):
        return REDACTED
    return value


def redact_query(raw):
    """Preserve encoding/order/duplicates; replace only credential parameter values."""
    result = []
    for part in str(raw).split('&'):
        key, sep, value = part.partition('=')
        result.append(key + sep + (REDACTED if sep and SENSITIVE.search(unquote_plus(key)) else value))
    return '&'.join(result)


def redact_path(path):
    # Sylius tokenValue grants order access. It is a credential, not an ordinary ID.
    return re.sub(r'(/api/v2/shop/orders/)[^/?#]+', r'\1[REDACTED]', str(path))


def redact_target(target):
    path, sep, query = str(target).partition('?')
    return redact_path(path) + (sep + redact_query(query) if sep else '')


def redact_json_text(raw):
    """Replace sensitive JSON values by spans; preserve all other source characters."""
    decoder = json.JSONDecoder()
    spans = []
    def whitespace(i):
        while i < len(raw) and raw[i] in ' \r\n\t': i += 1
        return i
    def walk(i):
        i = whitespace(i)
        if raw[i] == '{':
            i = whitespace(i + 1)
            if raw[i] == '}': return i + 1
            while True:
                key, end = decoder.raw_decode(raw, i)
                i = whitespace(end)
                if not isinstance(key, str) or raw[i] != ':': raise ValueError('invalid object')
                start = whitespace(i + 1)
                if SENSITIVE.search(key):
                    _, end = decoder.raw_decode(raw, start)
                    spans.append((start, end))
                else:
                    end = walk(start)
                i = whitespace(end)
                if raw[i] == '}': return i + 1
                if raw[i] != ',': raise ValueError('invalid object')
                i = whitespace(i + 1)
        if raw[i] == '[':
            i = whitespace(i + 1)
            if raw[i] == ']': return i + 1
            while True:
                i = whitespace(walk(i))
                if raw[i] == ']': return i + 1
                if raw[i] != ',': raise ValueError('invalid array')
                i = whitespace(i + 1)
        return decoder.raw_decode(raw, i)[1]
    end = walk(0)
    if raw[end:].strip(): raise ValueError('trailing content')
    for start, end in reversed(spans):
        raw = raw[:start] + json.dumps(REDACTED) + raw[end:]
    return raw


def redact_body_text(raw, content_type=''):
    if raw is None: return None
    if not isinstance(raw, str): raise TypeError('raw body must be text')
    content_type = content_type.lower()
    if 'form-urlencoded' in content_type:
        return redact_query(raw)
    if 'json' in content_type or raw.lstrip().startswith(('{', '[')):
        try:
            return redact_json_text(raw)
        except (ValueError, IndexError, RecursionError):
            # A malformed credential-bearing document cannot safely be exported verbatim.
            keys = re.findall(r'"((?:[^"\\]|\\.)*)"\s*:', raw)
            def sensitive_key(key):
                try:
                    return bool(SENSITIVE.search(json.loads('"' + key + '"')))
                except ValueError:
                    return True
            if any(sensitive_key(key) for key in keys) or SENSITIVE.search(raw):
                return '[REDACTED: malformed credential-bearing body]'
    elif '=' in raw and any(SENSITIVE.search(unquote_plus(part.partition('=')[0])) for part in raw.split('&')):
        return redact_query(raw)
    return raw


def prepare_request(request):
    """Do not synthesize missing wire bytes. None means historical capture unavailable."""
    headers = {str(k): redact_fields(v, str(k)) for k, v in request.get('headers', {}).items()}
    for key in headers:
        if key.lower() in {'referer', 'location'} and isinstance(headers[key], str):
            headers[key] = redact_target(headers[key])
    content_type = next((str(v) for k, v in headers.items() if k.lower() == 'content-type'), '')
    path = request.get('path', '')
    raw_query = request.get('raw_query')
    if raw_query is None and '?' in path:
        path, raw_query = path.split('?', 1)
    raw_query = redact_query(raw_query) if raw_query is not None else None
    query = parse_qs(raw_query, keep_blank_values=True, max_num_fields=1000) if raw_query is not None else request.get('query', {})
    result = {'method': request.get('method', 'GET'), 'path': redact_path(path),
        'raw_query': raw_query, 'query': redact_fields(query), 'headers': headers,
        'body': redact_fields(request.get('body')),
        'raw_body': redact_body_text(request.get('raw_body'), content_type)}
    if 'path_parameters' in request:
        result['path_parameters'] = redact_fields(request['path_parameters'])
    return result


def from_evidence(row):
    target = row.get('request_target', row['path'])
    url = urlsplit(target)
    pattern = '^' + re.sub(r'\\\{[^}]+\\\}', '([^/]+)', re.escape(row.get('operation_path', ''))) + '$'
    match = re.match(pattern, urlsplit(row['path']).path)
    names = re.findall(r'\{([^}]+)\}', row.get('operation_path', ''))
    path_parameters = dict(zip(names, match.groups() if match else []))
    return prepare_request({'method': row['method'], 'path': url.path,
        'raw_query': row.get('raw_query', url.query), 'headers': row.get('request_headers', {}),
        'body': row.get('request_body'), 'raw_body': row.get('request_body_raw'), 'path_parameters':path_parameters})
