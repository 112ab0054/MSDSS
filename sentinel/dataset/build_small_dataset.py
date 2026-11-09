"""Build a small, document-complete request candidate set; never send platform HTTP.

CSV is a machine-learning interchange format here, not an Excel workbook.
All generated rows require live binding, HTTP collection and review before training.
"""
import argparse
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import random
import re
import sys
from urllib.parse import quote, urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'sentinel/model'))
from request_input import SENSITIVE

COMMIT = '926670a710283f87c05b554680facf3f9530548c'
SOURCE = f'https://raw.githubusercontent.com/Morzeux/HttpParamsDataset/{COMMIT}'
PLATFORMS = ('bagisto', 'shopware', 'sylius')
FIELDS = ('header', 'query', 'path', 'body')


def sha(value):
    raw = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def read_documents():
    """Table header determines mode: a BODY field named query is not a query parameter."""
    operations, hashes = {}, {}
    for platform in PLATFORMS:
        file = ROOT / f'sentinel/analysis/selected-api-contracts/{platform}/API_parameters.md'
        hashes[file.relative_to(ROOT).as_posix()] = sha(file.read_bytes().replace(b'\r\n', b'\n'))
        current, mode = None, None
        for number, line in enumerate(file.read_text(encoding='utf-8-sig').splitlines(), 1):
            match = re.fullmatch(r'`(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) ([^`]+)`', line.strip())
            if line.startswith('## '):
                current, mode = None, None
            if match:
                current = (platform, *match.groups())
                operations[current] = {'fields': {}, 'content_type': None}
            if not current:
                continue
            if line.startswith('### '):
                mode = None
            if line.startswith('- Content-Type：') and not operations[current]['content_type']:
                operations[current]['content_type'] = re.search(r'`([^`]+)`', line)[1]
            if not line.startswith('|'):
                continue
            cells = [s.strip() for s in re.split(r'(?<!\\)\|', line.strip().strip('|'))]
            if cells[0] == '位置':
                mode = 'parameter'
                continue
            if cells[0] == '本文字段':
                mode = 'body'
                continue
            if cells[0].startswith('-'):
                continue
            if mode == 'parameter' and cells[0] in FIELDS and len(cells) >= 6:
                location, name, required, kind, values, meaning = cells[:6]
            elif mode == 'body' and len(cells) >= 5:
                location = 'body'
                name, required, kind, values, meaning = cells[:5]
            else:
                continue
            name = name.strip('`')
            operations[current]['fields'][location, name] = {
                'required': required, 'type': kind, 'values': values, 'meaning': meaning,
                'source': file.relative_to(ROOT).as_posix(), 'line': number}
    manifest = json.loads((ROOT / 'sentinel/analysis/api-extension/active-api-manifest.json').read_text(encoding='utf-8'))
    expected = {(o['platform'], o['method'], o['path']) for o in manifest['operations']}
    if set(operations) != expected:
        raise ValueError('API 文件與採用清單不一致，不自動補造操作')
    return operations, hashes


def put(target, name, value):
    """Assign dotted/[] body paths with real nested objects and arrays."""
    parts = name.split('.')
    cursor = target
    for i, part in enumerate(parts):
        array = part.endswith('[]')
        key = part[:-2] if array else part
        last = i == len(parts) - 1
        if last:
            cursor[key] = [value] if array else value
        elif array:
            if not isinstance(cursor.get(key), list) or not cursor[key]:
                cursor[key] = [{}]
            if not isinstance(cursor[key][0], dict):
                cursor[key][0] = {}
            cursor = cursor[key][0]
        else:
            if not isinstance(cursor.get(key), dict):
                cursor[key] = {}
            cursor = cursor[key]


def get(target, name):
    cursor = target
    for part in name.split('.'):
        array = part.endswith('[]')
        key = part[:-2] if array else part
        if not isinstance(cursor, dict) or key not in cursor:
            return False, None
        cursor = cursor[key]
        if array:
            if not isinstance(cursor, list) or not cursor:
                return False, None
            cursor = cursor[0]
    return True, cursor


def initial_value(location, name, spec):
    if SENSITIVE.search(name):
        return '[REDACTED]', '憑證遮蔽；執行前須由私有環境綁定'
    values, kind = spec['values'], spec['type']
    for prefix in ('固定值：', '預設值：', '範例：'):
        if prefix in values:
            match = re.search(r'`([^`]+)`', values.split(prefix, 1)[1])
            if match:
                text = match[1]
                try:
                    value = json.loads(text)
                    if 'string' in kind and not isinstance(value, str):
                        value = text
                    return value, '文件列值（尚未實機驗證）'
                except ValueError:
                    return text, '文件列值（尚未實機驗證）'
    if location == 'path' or re.search(r'(^id$|Id$|_id$|Code$|^code$|^ids$|^referencedId$)', name):
        return '${LIVE:' + name + '}', '動態識別值待綁定，不是假造有效 ID'
    if 'boolean' in kind:
        return True, '合成布林測試值'
    if 'integer' in kind or 'number' in kind:
        minimum = re.search(r'最小值：(\d+(?:\.\d+)?)', values)
        return max(1, float(minimum[1])) if minimum else 1, '合成數值；業務限制尚待確認'
    if 'array' in kind:
        return ['${LIVE:' + name + '[]}'], '陣列成員待依實例／結構綁定'
    if 'object' in kind:
        return {}, '文件未展開物件；不編造其內部結構'
    common = {'email': 'customer@example.test', 'firstName': 'Mei', 'lastName': 'Chen',
              'first_name': 'Mei', 'last_name': 'Chen', 'city': 'Taipei', 'street': '1 Test Road',
              'postcode': '100', 'phoneNumber': '0200000000', 'company': 'MSDSS Test'}
    return common.get(name, 'MSDSS cotton'), '合成文字；格式／業務限制尚待確認'


def source_payloads():
    raw = urlopen(SOURCE + '/payload_full.csv', timeout=60).read()
    license_text = urlopen(SOURCE + '/LICENSE', timeout=30).read().decode('utf-8')
    all_rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    pools = {}
    for kind in ('norm', 'sqli', 'xss'):
        candidates = [(i + 2, r['payload']) for i, r in enumerate(all_rows)
                      if r['attack_type'] == kind and 0 < len(r['payload']) <= 256
                      and not any(ord(c) < 32 for c in r['payload'])]
        # Exact-value dedup only. Do not strip/decode/lower payload strings.
        unique = list({v: (n, v) for n, v in reversed(candidates)}.values())
        random.Random('MSDSS-small-v1-' + kind).shuffle(unique)
        pools['normal' if kind == 'norm' else kind] = unique[:8]
    return pools, {r['payload'] for r in all_rows}, {
        'repository': 'https://github.com/Morzeux/HttpParamsDataset', 'commit': COMMIT,
        'url': SOURCE + '/payload_full.csv', 'sha256': sha(raw), 'source_rows': len(all_rows),
        'license': 'MIT', 'sampling': 'seeded shuffle; max 256 characters; no control characters; 8 per class',
        'excluded_attack_types': ['cmdi', 'path-traversal']}, license_text


def catalog_payloads(external_values):
    pools = {'train': {'sqli': [], 'xss': []}, 'test': {'sqli': [], 'xss': []}}
    test_families = {'sql.error', 'sql.stacked', 'xss.js-string', 'xss.js-template'}
    with (ROOT / 'sentinel/dataset/scenario-catalog.csv').open(encoding='utf-8-sig', newline='') as file:
        for row in csv.DictReader(file):
            case = json.loads(row['完整情境JSON'])
            label, value = case['proposed_label'], case.get('value')
            if label not in ('sqli', 'xss') or not isinstance(value, str) or value in external_values:
                continue
            if case['variant_kind'] != 'base':
                continue
            split = 'test' if case['family_id'] in test_families else 'train'
            item = {'value': value, 'source': 'local_scenario_catalog', 'source_id': case['base_case_id'],
                    'family': case['family_id'], 'can_collect_http': case['can_collect_http']}
            if not any(x['value'] == value for x in pools[split][label]):
                pools[split][label].append(item)
    if any(not items for p in pools.values() for items in p.values()):
        raise ValueError('去除外部資料重複後，某類別沒有候選，不以重複 payload 補數')
    return pools


def finalize(request, template):
    request['path'] = template
    for name, value in request['path_parameters'].items():
        request['path'] = request['path'].replace('{' + name + '}', quote(str(value), safe=''))
    def pairs(name, value):
        if isinstance(value, dict) and value:
            for child, item in value.items():
                yield from pairs(f'{name}[{child}]', item)
        elif isinstance(value, list) and value:
            for index, item in enumerate(value):
                if isinstance(item, (dict, list)):
                    yield from pairs(f'{name.removesuffix("[]")}[{index}]', item)
                else:
                    yield name, str(item)
        elif isinstance(value, (dict, list)):
            # Empty undocumented structures remain visible skeletons, not valid deepObject claims.
            yield name, json.dumps(value, separators=(',', ':'))
        else:
            yield name, str(value)
    request['raw_query'] = urlencode([pair for name, value in request['query'].items() for pair in pairs(name, value)])
    request['raw_body'] = json.dumps(request['body'], ensure_ascii=False, separators=(',', ':')) if request['body'] is not None else ''


def field_value(request, location, name):
    source = request[{'header': 'headers', 'query': 'query', 'path': 'path_parameters', 'body': 'body'}[location]]
    return get(source, name) if location == 'body' else (name in source, source.get(name))


def build(operations, external, catalog):
    rows, field_records = [], []
    assignment = {}
    for platform in PLATFORMS:
        keys = sorted(k for k in operations if k[0] == platform)
        random.Random('MSDSS-small-v1-' + platform).shuffle(keys)
        for i, key in enumerate(keys):
            assignment[key] = 'validation' if platform == 'sylius' else ('test' if i < 4 else 'train')
    for key in sorted(operations):
        platform, method, path = key
        spec, split = operations[key], assignment[key]
        request = {'method': method, 'headers': {'Accept': 'application/json'},
                   'query': {}, 'path_parameters': {}, 'body': None}
        if spec['content_type']:
            request['headers']['Content-Type'] = spec['content_type']
            request['body'] = {}
        notes = {}
        for (location, name), field in sorted(spec['fields'].items(), key=lambda x: x[0][1].count('.')):
            value, note = initial_value(location, name, field)
            if location == 'header' and not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
            target = {'header': 'headers', 'query': 'query', 'path': 'path_parameters', 'body': 'body'}[location]
            if request[target] is None:
                request[target] = {}
            if location == 'body':
                put(request[target], name, value)
            else:
                request[target][name] = value
            notes[location, name] = note
        context_token = next((n for n in request['headers'] if n.lower() == 'sw-context-token'), None)
        context_source = next((n for n in request['headers'] if n.lower() == 'sw-context-source'), None)
        alternative = None
        if context_token and context_source:
            alternative = copy.deepcopy(request)
            alternative['headers'].pop(context_token)
            alternative['headers']['Cookie'] = '[REDACTED]'
            request['headers'].pop(context_source)
        elif context_source:
            request['headers']['Cookie'] = '[REDACTED]'
        finalize(request, path)
        operation_rows = []

        def emit(req, label='normal', target=None, payload=None, variant='document_baseline'):
            finalize(req, path)
            meta = {'platform': platform, 'operation_path': path, 'split': split,
                    'origin': 'small_document_candidates_v1', 'request_input_version': 3,
                    'http_executed': False, 'training_approved': False, 'source_evidence': None,
                    'raw_target_captured': False, 'raw_body_captured': False,
                    'raw_text_origin': 'generated_serialization_not_captured_wire',
                    'schema_validity': 'not_validated', 'business_verified': False,
                    'session_group': None, 'requires_live_session': True,
                    'pair_group': sha(key), 'variant': variant,
                    'target_location': target[0] if target else None,
                    'target_parameter': target[1] if target else None,
                    'payload': payload, 'unresolved_binding': '${LIVE:' in json.dumps(req) or '[REDACTED]' in json.dumps(req),
                    'parameter_document': next(iter(spec['fields'].values()))['source']}
            sample = {'sample_id': sha([key, variant, target, payload, req]), 'input': copy.deepcopy(req),
                      'annotation': {'proposed_label': label, 'eligible_for_review': False,
                                     'review_status': 'pending_live_binding_http_and_review',
                                     'label_basis': '輸入來源／攻擊意圖；不是 HTTP 成功或漏洞成立的證明'},
                      'metadata': meta}
            rows.append(sample)
            operation_rows.append(sample)

        emit(request)
        if alternative:
            emit(alternative, variant='exclusive_session_cookie_alternative')
        targets = []
        for location in FIELDS:
            options = [(loc, name) for (loc, name), field in spec['fields'].items()
                       if loc == location and not SENSITIVE.search(name)
                       and not any(t in field['type'] for t in ('array', 'object'))
                       and field_value(request, loc, name)[0]]
            # Prefer unrestricted text and business text over IDs/enum headers.
            options.sort(key=lambda t: (not ('string' in spec['fields'][t]['type'] and '固定值：' not in spec['fields'][t]['values']),
                                        not bool(re.search('query|search|notes|name|Name|street|company|label', t[1])), t[1]))
            if options:
                targets.append(options[0])
        for index, target in enumerate(targets):
            labels = ('normal', 'sqli', 'xss') if split == 'validation' else ('sqli', 'xss')
            for label in labels:
                if split == 'validation':
                    line, value = external[label][int(sha([key, target, label])[:8], 16) % len(external[label])]
                    payload = {'value': value, 'source': 'httpParamsDataset', 'source_id': f'payload_full.csv:{line}',
                               'family': None, 'commit': COMMIT, 'can_collect_http': False}
                    # Benign external text only in unrestricted string fields, not enum/numeric IDs.
                    field = spec['fields'][target]
                    if label == 'normal' and (target[0] == 'path' or 'string' not in field['type'] or '固定值：' in field['values']):
                        continue
                else:
                    options = catalog[split][label]
                    payload = options[int(sha([key, target, label])[:8], 16) % len(options)]
                changed = copy.deepcopy(request)
                target_dict = changed[{'header': 'headers', 'query': 'query', 'path': 'path_parameters', 'body': 'body'}[target[0]]]
                if target[0] == 'body':
                    put(target_dict, target[1], payload['value'])
                else:
                    target_dict[target[1]] = payload['value']
                emit(changed, label, target, payload, 'single_field_payload')
        for (location, name), field in spec['fields'].items():
            present = [field_value(r['input'], location, name) for r in operation_rows]
            values = [v for found, v in present if found]
            example = values[0] if values else None
            encoded = json.dumps(example, ensure_ascii=False)
            status = ('待綁定憑證／實例值' if '${LIVE:' in encoded or '[REDACTED]' in encoded
                      else '結構待依實例補充' if example in ({}, []) else '已填候選值；未實測')
            field_records.append({'平台': platform, '集合': split, '方法': method, 'API': path,
                '位置': location, '參數': name, '必填': field['required'], '型別': field['type'],
                '候選中存在筆數': len(values), '範例值JSON': json.dumps(values[0], ensure_ascii=False) if values else '',
                '值的來源與限制': notes[location, name], '填入狀態': status, '實機已驗證': False,
                '文件': field['source'], '行號': field['line']})
    return rows, field_records


def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def export(output):
    if output.exists():
        raise ValueError('輸出已存在；不覆寫既有資料，請另選目錄')
    operations, hashes = read_documents()
    external, external_values, provenance, license_text = source_payloads()
    catalog = catalog_payloads(external_values)
    rows, fields = build(operations, external, catalog)
    if any(f['候選中存在筆數'] == 0 for f in fields):
        raise ValueError('有文件欄位完全未填，停止輸出')
    sets = {split: [r for r in rows if r['metadata']['split'] == split] for split in ('train', 'test', 'validation')}
    fingerprints = {s: {sha(r['input']) for r in data} for s, data in sets.items()}
    if any(fingerprints[a] & fingerprints[b] for a, b in [('train', 'test'), ('train', 'validation'), ('test', 'validation')]):
        raise ValueError('跨集合有完全相同的請求')
    output.mkdir(parents=True)
    for split, data in sets.items():
        flat = []
        for row in data:
            req, meta = row['input'], row['metadata']
            flat.append({'樣本ID': row['sample_id'], '平台': meta['platform'], '集合': split,
                '候選類別': row['annotation']['proposed_label'], '方法': req['method'], 'API模板': meta['operation_path'],
                'Path': req['path'], 'Header_JSON': json.dumps(req['headers'], ensure_ascii=False),
                'Query_JSON': json.dumps(req['query'], ensure_ascii=False),
                'Body_JSON': json.dumps(req['body'], ensure_ascii=False),
                '原始Query': req['raw_query'], '原始Body': req['raw_body'],
                '變動位置': meta['target_location'], '變動欄位': meta['target_parameter'],
                'Payload原文': (meta['payload'] or {}).get('value'),
                'Payload來源': (meta['payload'] or {}).get('source', 'API文件／合成基底'),
                '完整紀錄JSON': json.dumps(row, ensure_ascii=False)})
        write_csv(output / f'{split}.csv', flat)
    write_csv(output / 'field-coverage.csv', fields)
    selected = [{'類別': label, '來源紀錄起始行': line, 'payload': value, 'commit': COMMIT}
                for label, pool in external.items() for line, value in pool]
    write_csv(output / 'external-payloads.csv', selected)
    (output / 'HTTPPARAMS-LICENSE.txt').write_text(license_text, encoding='utf-8')
    summary = {'splits': {s: {'rows': len(data), 'labels': {label: sum(r['annotation']['proposed_label'] == label for r in data)
               for label in ('normal', 'sqli', 'xss')}, 'platforms': sorted({r['metadata']['platform'] for r in data})}
               for s, data in sets.items()}, 'api_operations': len(operations), 'document_fields': len(fields),
               'fields_present_in_candidates': sum(bool(f['候選中存在筆數']) for f in fields),
               'field_binding_status': {status: sum(f['填入狀態'] == status for f in fields)
                                        for status in sorted({f['填入狀態'] for f in fields})},
               'http_executed': 0, 'training_approved': 0, 'parameter_document_sha256': hashes,
               'scenario_catalog_sha256': sha((ROOT / 'sentinel/dataset/scenario-catalog.csv').read_bytes()),
               'external_source': provenance, 'split_rule': 'operation-disjoint 4 held-out APIs per training platform; family-disjoint local attack catalog',
               'medusa_included': False, 'normalization': 'none; transport serialization only; credential values redacted'}
    (output / 'provenance.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'README.md').write_text('# 小規模 API 文件導向候選資料集\n\n'
        '這是新候選版本，不覆寫舊資料；不是已完成實機採集或可正式訓練的資料。\n\n'
        '- train.csv／test.csv：Bagisto＋Shopware；每平台保留 4 個 API 作測試，操作不跨集合。\n'
        '- validation.csv：僅 Sylius；攻擊與額外正常輸入來自固定 commit 的 httpParamsDataset。\n'
        '- Medusa 不參與任何集合。來源標記只放 metadata，不是模型輸入。\n'
        '- 每個 API 的文件欄位全部列在 field-coverage.csv，包含 Header、Query、Path、巢狀 Body。\n'
        '- API 沒有的參數位置不硬加；sw-context-token／sw-context-source 分成互斥候選，session 方案須綁 Cookie。\n'
        '- 原文保留，不做大小寫、ID、空白、編碼正規化；raw 欄是新生成的傳輸文字，不冒充歷史封包。\n'
        '- 憑證只保留 [REDACTED]；${LIVE:...} 代表尚缺實例值，不是假造可用 ID。\n'
        '- 文件未展開的物件保留 {}，陣列成員可能待綁定；合成值、篩選組合、認證、業務限制均未驗證。\n'
        '- Query 物件使用括號式欄位；空物件／空陣列仍為可見骨架，序列化和 API 接受方式待實機核對，不能宣稱其結構已填完。\n'
        '- 外部 norm 僅表示原資料標籤，不代表一定符合電商欄位格式；攻擊意圖不代表漏洞成立。\n'
        '- 每 API 每個可變動位置只選一欄放 payload，控制總量；不表示每欄都已測攻擊／每種家族全覆蓋。\n'
        '- 外部 payload 全檔與本地攻擊原文做精確排重；不宣稱語意或近似家族完全獨立。\n'
        '- 訓練／測試家族不同，這是較難的初步設計；各平台比例與 API 難度未配平，不能據此報告效果。\n'
        '- 不調參使用 test 或 validation；實際採集時另建獨立 session 並維持同流程／同來源家族分組。\n'
        '- 尚需：本機綁定、正常流程業務斷言、逐筆 HTTP 證據、格式／標籤審核，再匯出正式資料。\n\n'
        '目前統計：\n\n```json\n' + json.dumps(summary, ensure_ascii=False, indent=2) + '\n```\n\n'
        '重現：在專案根目錄執行 `python -B sentinel/dataset/build_small_dataset.py --output <新的輸出目錄>`。'
        '產生器只下載固定來源並寫候選，不啟動平台、不發送攻擊、不訓練模型。\n', encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'sentinel/dataset/small-api-v1')
    print(json.dumps(export(parser.parse_args().output), ensure_ascii=False))
