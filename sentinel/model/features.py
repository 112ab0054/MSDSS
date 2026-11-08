"""Raw-value numeric baseline. Training/serving share input rules and header slots."""
import json
import re
from request_input import SENSITIVE, prepare_request, redact_fields

VERSION = 4
LABELS = ['normal', 'sqli', 'xss']
PATTERNS = [r'\b(or|and)\b', r'\bunion\b', r'\bselect\b', r'\bsleep\b|\bbenchmark\b',
            r'--|/\*|\*/', r'<script\b', r'\bon\w+\s*=', r'javascript\s*:']


def clean(value):
    return redact_fields(value)


def text(value):
    # A string is already input text, not an invitation to parse it again as JSON/form.
    return value if isinstance(value, str) else json.dumps(redact_fields(value), ensure_ascii=False)


def signals(value):
    # Ignore case for keyword counting only; never rewrite the stored input.
    return [len(value), *[value.count(c) for c in ['%', "'", '"', '<', '>', ';', '=']],
            *[len(re.findall(pattern, value, re.I)) for pattern in PATTERNS]]


def header_features(headers, header_names):
    observed = {str(k).lower(): v for k, v in headers.items()}
    ordinary = {k: v for k, v in headers.items() if not SENSITIVE.search(str(k))}
    result = [len(headers), sum(bool(SENSITIVE.search(str(k))) for k in headers)] + signals(text(ordinary))
    # One named block for EACH header from the three API documents, not Content-Type only.
    for name in header_names:
        present = name in observed
        result.append(int(present))
        result += signals(text(observed[name])) if present and not SENSITIVE.search(name) else [0] * 16
    return result


def features(request, header_names=None):
    if header_names is None:
        from header_contracts import documented_headers
        header_names, _ = documented_headers()
    request = prepare_request(request)
    headers = request['headers']
    content_type = next((str(v).lower() for k, v in headers.items() if k.lower() == 'content-type'), '')
    result = [int(request['method'].upper() == m) for m in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']]
    result += [int(t in content_type) for t in ['json', 'form', 'multipart']]
    query = request['raw_query'] if request['raw_query'] is not None else text(request['query'])
    body = request['raw_body'] if request['raw_body'] is not None else text(request['body'])
    for value in (query, body, request['path']):
        result += signals(value)
    result += header_features(headers, header_names)
    return result  # 74 + 17 * documented header count; currently 278 dimensions.
