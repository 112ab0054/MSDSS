"""Raw-value numeric baseline. Training/serving share input rules and header slots."""
import json
import re
from sklearn.feature_extraction.text import HashingVectorizer
from request_input import SENSITIVE, prepare_request, redact_fields

VERSION = 5
LABELS = ['normal', 'sqli', 'xss']
PATTERNS = [r'\b(or|and)\b', r'\bunion\b', r'\bselect\b', r'\bsleep\b|\bbenchmark\b',
            r'--|/\*|\*/', r'<script\b', r'\bon\w+\s*=', r'javascript\s*:']
HASH_BUCKETS = 512
EXTRA_SYMBOLS = ['(', ')', '{', '}', '$', '`', '/', '\\', ':', '&', '#']
EXTRA_PATTERNS = [r'\b(?:alert|prompt|confirm|eval|Function|setTimeout|setInterval|void|console\.info|String\.fromCharCode)\s*\(',
                  r'\b(?:document|window|location)\s*\.', r'\$\{', r'["\'`]\s*;',
                  r'</(?:script|textarea|style|title)',
                  r'%(?:3c|3e|22|27|28|29|3b|24|7b|7d)',
                  r'(?:%3c\s*script|on\w+%3d|javascript%3a)',
                  r'&#(?:x[0-9a-f]+|\d+);|&(?:lt|gt|quot|apos);']


def raw_ngrams(value):
    # Callable analyzer avoids sklearn's built-in char whitespace compression.
    for size in range(2, 6):
        for start in range(max(0, len(value) - size + 1)):
            yield value[start:start + size]


HASHER = HashingVectorizer(analyzer=raw_ngrams, n_features=HASH_BUCKETS,
                          norm=None, alternate_sign=False, lowercase=False)


def feature_count(header_names):
    return 74 + 17 * len(header_names) + 4 * (HASH_BUCKETS + len(EXTRA_SYMBOLS) + len(EXTRA_PATTERNS))


def layout():
    return {'version': VERSION, 'hash_buckets_per_channel': HASH_BUCKETS,
            'ngram_sizes': [2, 3, 4, 5], 'channels': ['query', 'body', 'path', 'headers'],
            'normalization': None, 'lowercase_values': False, 'vocabulary_fit': False,
            'extra_symbols': EXTRA_SYMBOLS, 'extra_patterns': EXTRA_PATTERNS}


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
    # Header names are case-insensitive identifiers; values are preserved verbatim.
    ordinary = {str(k).lower(): v for k, v in headers.items() if not SENSITIVE.search(str(k))}
    header_text = json.dumps(ordinary, ensure_ascii=False, sort_keys=True)
    for value in (query, body, request['path'], header_text):
        result += [value.count(c) for c in EXTRA_SYMBOLS]
        result += [len(re.findall(pattern, value, re.I)) for pattern in EXTRA_PATTERNS]
        result += HASHER.transform([value]).toarray()[0].tolist()
    return result
