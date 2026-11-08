"""Complete document candidates using verified historical values and schema semantics.

No credential values are exported and no platform HTTP is sent by this builder.
Historical IDs are not certified to be current. Shape examples are not live fixtures.
"""
import argparse
from collections import Counter, defaultdict
import copy
import itertools
import json
from pathlib import Path
import random
import sys

from build_small_dataset import (ROOT, COMMIT, SENSITIVE, sha, read_documents, source_payloads,
                                 catalog_payloads, build, finalize, put, get, field_value, write_csv)
sys.path.insert(0, str(ROOT / 'sentinel/model'))
from real_requests import read_rows, refresh


def walk(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key, child
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


class Completion:
    def __init__(self):
        rows = refresh(read_rows(ROOT / 'sentinel/dataset/reference/normal-candidates.csv'))
        self.by_operation = defaultdict(list)
        self.named = defaultdict(dict)
        self.evidence = {}
        self.session_sources = {}
        self.current_split = None
        for platform in ('bagisto', 'shopware', 'sylius'):
            paths = sorted({r['metadata']['source_evidence'] for r in rows if r['metadata']['platform'] == platform})
            if platform == 'sylius':
                self.session_sources['validation', platform] = paths[-1]
            else:
                if len(paths) < 2:
                    raise ValueError('訓練／測試需要不同歷史 session 來源')
                self.session_sources['train', platform] = paths[0]
                self.session_sources['test', platform] = paths[1]
        for row in rows:
            meta = row['metadata']
            platform = meta['platform']
            path = meta['source_evidence']
            split = next((s for (s, p), source in self.session_sources.items() if p == platform and source == path), None)
            if split is None:
                continue
            self.by_operation[split, platform, row['input']['method'], meta['operation_path']].append(row)
            if path in self.evidence:
                continue
            self.evidence[path] = meta['source_evidence_sha256']
            report = json.loads((ROOT / path).read_text(encoding='utf-8-sig'))
            for record in report['requests']:
                for name, value in walk([record.get('request_body'), record.get('response_body')]):
                    if not SENSITIVE.search(name) and value is not None and value != '[REDACTED]':
                        self.named[split, platform].setdefault(name, copy.deepcopy(value))

    def actual(self, platform, name):
        value = self.named[self.current_split, platform].get(name)
        if value is None:
            raise ValueError(f'缺少可追溯實例值：{platform}/{name}')
        return copy.deepcopy(value)

    def resolve(self, key, location, name, spec, old):
        platform, method, path = key
        if SENSITIVE.search(name):
            return '[REDACTED]', '憑證已遮蔽；執行器本機取得，非缺少物件結構'
        if platform == 'sylius' and name == '（本文）':
            return {}, '來源 object 無具名欄位；既有 POST orders 實測使用 {}，不是漏填'
        # Prefer the exact operation's observed field over generated examples.
        for original in self.by_operation[(self.current_split, *key)]:
            found, value = field_value(original['input'], location, name)
            if found and value is not None and value not in ({}, [], '[REDACTED]'):
                return copy.deepcopy(value), '既有正常 HTTP 證據原值；不是本次即時有效性驗證'
        if platform == 'shopware':
            country = self.actual(platform, 'countryId')
            entity = ('order' if path == '/order' else 'customer_address' if 'address' in path
                      else 'payment_method' if path == '/payment-method'
                      else 'shipping_method' if path == '/shipping-method' else 'product')
            if name in ('reduce-aggregations', 'no-aggregations', 'only-aggregations'):
                return '1', '原始 schema oneOf string/null，為存在旗標；人工表 object 型別差異另記'
            if name == 'associations':
                association = 'country' if entity == 'customer_address' else 'lineItems' if entity == 'order' else 'media' if entity == 'product' else 'translations'
                return {association: {'limit': 1}}, '來源 Associations→Criteria；依端點實體選關聯'
            if name in ('includes', 'excludes'):
                return {entity: ['id', 'name'] if name == 'includes' else ['createdAt', 'updatedAt']}, '來源 Includes/Excludes：實體名稱對應欄位陣列；兩者不選同欄'
            if name in ('filter', 'filter[]', 'post-filter', 'post-filter[]'):
                return [{'type': 'equals', 'field': 'active', 'value': True}] if entity in ('product', 'payment_method', 'shipping_method') else [{'type': 'equals', 'field': 'id', 'value': self.actual(platform, 'orderId' if entity == 'order' else 'billingAddressId')}], '來源 Filter→EqualsFilter 結構；ID 取自正常證據'
            if name in ('sort', 'sort[]'):
                return [{'field': 'id', 'order': 'ASC'}], '來源 FieldSorting；穩定識別欄排序'
            if name in ('aggregations', 'aggregations[]'):
                return [{'name': 'record_count', 'type': 'count', 'field': 'id'}], '來源 Aggregation count，非空陣列佔位'
            if name in ('fields', 'fields[]', 'grouping', 'grouping[]'):
                return ['id'], '文件為欄位名稱陣列，使用 id'
            if name == 'ids[]' or (name == 'ids' and path not in ('/checkout/cart/line-item/delete',)):
                id_name = 'orderId' if entity == 'order' else 'billingAddressId' if entity == 'customer_address' else 'paymentMethodId' if entity == 'payment_method' else 'shippingMethodId' if entity == 'shipping_method' else 'referencedId'
                return [self.actual(platform, id_name)], '依查詢實體使用既有正常證據 ID'
            if name in ('billingAddress', 'shippingAddress'):
                return {'firstName': 'MSDSS', 'lastName': 'Test', 'street': 'Phase One Street 12',
                        'zipcode': '10115', 'city': 'Berlin', 'countryId': country}, '依 Address required 六欄補齊；countryId 取正常證據'
            if name in ('customFields', 'items[].payload'):
                return {'msdss_test_note': 'local normal shopping'}, '來源允許附加鍵值；customFields 儲存仍須實例定義，不冒充已建立'
            if name == 'vatIds':
                return ['GB123456789'], '依文件 VAT 範例建立字串陣列；不是已驗證稅籍'
            if name in ('affiliateCode', 'campaignCode'):
                return 'MSDSS-LOCAL', '聯盟／活動追蹤代碼測試值；非關聯 ID'
            if name == 'items[].coverId':
                cover = self.named[self.current_split, platform].get('cover')
                if isinstance(cover, dict):
                    media_id = cover.get('mediaId') or (cover.get('media') or {}).get('id')
                    if media_id:
                        return media_id, '既有商品回應 cover.mediaId，非杜撰 UUID'
            if name in ('countryStateId', 'items[].coverId'):
                # These are optional relations; an invented UUID would be misleading.
                return None, '選填關聯：無對應正常證據，明確 null 候選；實例若拒絕須省略，另列差異'
            leaf = name.split('.')[-1]
            if leaf in self.named[self.current_split, platform] and ('${LIVE:' in json.dumps(old) or leaf.endswith('Id')):
                return self.actual(platform, leaf), '既有正常 HTTP 證據中的同名識別值；需重新確認存續'
        if platform == 'bagisto':
            examples = {'superAttribute': {'1': 1}, 'qty': {'1': 1}, 'bundleOptions': {'1': [1]},
                        'bundleOptionQty': {'1': 1}, 'booking': {'date': '2026-11-16', 'slot': '1794819600-1794823200'},
                        'links': [1], 'vatId': 'GB123456789'}
            if name in examples:
                note = ('文件／核心商品型別程式的結構範例；數字鍵是示例，不是已建立的屬性／組合／預約種子 ID'
                        if name != 'vatId' else '文件列出的 VAT 範例')
                return examples[name], note
        if platform == 'sylius':
            if name == 'countryCode':
                return 'US', '正常地址證據的 ISO 國家碼'
            if name in ('provinceCode', 'couponCode'):
                return None, '文件允許 null；不編造不存在的省份／優惠券'
            if name == 'productTaxons.taxon.code[]':
                main = self.named[self.current_split, platform].get('mainTaxon')
                if isinstance(main, str) and main.startswith('/api/v2/shop/taxons/'):
                    return [main.rsplit('/', 1)[-1]], '正常商品 mainTaxon IRI 中的實際分類代碼'
                taxons = self.named[self.current_split, platform].get('productTaxons') or []
                for _, value in walk(taxons):
                    if isinstance(value, dict) and value.get('code'):
                        return [value['code']], '正常商品回應中的分類代碼'
                return ['category'], '字串陣列結構已填；分類代碼尚無可追溯實例值'
        if '${LIVE:' in json.dumps(old):
            raise ValueError(f'尚未處理動態欄位：{key} {location}/{name}')
        return old, '保留文件列值／合成值；尚未實機驗證'


def complete(rows, operations, resolver):
    notes = {}
    for row in rows:
        req, meta = row['input'], row['metadata']
        resolver.current_split = meta['split']
        initial_request = copy.deepcopy(req)
        key = meta['platform'], req['method'], meta['operation_path']
        for (location, name), spec in sorted(operations[key]['fields'].items(), key=lambda x: x[0][1].count('.')):
            found, old = field_value(req, location, name)
            if not found and location == 'body':
                found, old = field_value(initial_request, location, name)
            if not found:
                continue  # mutually exclusive headers stay mutually exclusive
            value, note = resolver.resolve(key, location, name, spec, old)
            notes[key, location, name] = note
            source = req[{'header': 'headers', 'query': 'query', 'path': 'path_parameters', 'body': 'body'}[location]]
            if name == '（本文）' and location == 'body':
                req['body'] = value
            elif location == 'body':
                put(source, name, value)
            else:
                source[name] = value
        if meta['payload']:
            location, name = meta['target_location'], meta['target_parameter']
            source = req[{'header': 'headers', 'query': 'query', 'path': 'path_parameters', 'body': 'body'}[location]]
            if location == 'body':
                put(source, name, meta['payload']['value'])
            else:
                source[name] = meta['payload']['value']
        finalize(req, meta['operation_path'])
        meta.update(origin='small_document_candidates_v2', completion='historical_values_and_schema_shapes',
                    credentials_redacted=True, historical_id_current_validity='not_verified',
                    historical_source_report=resolver.session_sources[meta['split'], meta['platform']],
                    unresolved_binding='${LIVE:' in json.dumps(req))
        row['sample_id'] = sha([meta['split'], req, meta['payload']])
    return notes


def rebalance(rows, operations, external, catalog):
    """140 matched normal/SQLi/XSS triples; preserve header presence across labels."""
    pool = [r for r in rows if r['annotation']['proposed_label'] == 'normal']
    bases = [r for r in rows if r['metadata']['variant'] == 'document_baseline']
    targets_by_operation = defaultdict(set)
    for row in rows:
        meta = row['metadata']
        if meta['payload']:
            targets_by_operation[meta['platform'], row['input']['method'], meta['operation_path']].add(
                (meta['target_location'], meta['target_parameter']))

    def targets_for(row):
        m = row['metadata']
        key = m['platform'], row['input']['method'], m['operation_path']
        return sorted(t for t in targets_by_operation[key] if field_value(row['input'], *t)[0])

    def clone(base, target=None, payload=None, remove=None):
        row = copy.deepcopy(base)
        req, meta = row['input'], row['metadata']
        if remove:
            req['headers'].pop(remove, None)
        if target:
            location, name = target
            source = req[{'header': 'headers', 'query': 'query', 'path': 'path_parameters', 'body': 'body'}[location]]
            if location == 'body':
                put(source, name, payload['value'])
            else:
                source[name] = payload['value']
            meta.update(target_location=location, target_parameter=name, payload=payload, variant='single_field_payload')
        else:
            meta.update(variant='optional_header_absence', payload=None, target_location=None, target_parameter=None)
        finalize(req, meta['operation_path'])
        row['sample_id'] = sha([meta['split'], req, meta['payload']])
        row['annotation']['proposed_label'] = payload['label'] if payload else 'normal'
        return row

    for base in bases:
        meta = base['metadata']
        key = meta['platform'], base['input']['method'], meta['operation_path']
        optional = []
        for (location, name), spec in operations[key]['fields'].items():
            if location == 'header' and spec['required'] == '選填' and not SENSITIVE.search(name):
                optional.append(name)
                pool.append(clone(base, remove=name))
        for first, second in itertools.combinations(optional, 2):
            variant = clone(base, remove=first)
            variant['input']['headers'].pop(second, None)
            finalize(variant['input'], meta['operation_path'])
            variant['sample_id'] = sha([meta['split'], variant['input'], None])
            pool.append(variant)
    chosen = []
    for split, per_label in [('train', 84), ('test', 28), ('validation', 28)]:
        candidates = [r for r in pool if r['metadata']['split'] == split and targets_for(r)]
        unique = {sha(r['input']): r for r in reversed(candidates)}
        candidates = list(unique.values())
        random.Random('MSDSS-v2-' + split).shuffle(candidates)
        must_keep = [r for r in candidates if r['metadata']['variant'] in ('document_baseline', 'exclusive_session_cookie_alternative')]
        if len(must_keep) > per_label:
            raise ValueError('保留完整文件欄位所需正常基底超出類別配額')
        selection = list(must_keep)
        groups = defaultdict(list)
        for r in candidates:
            if r not in must_keep:
                m = r['metadata']
                groups[m['platform'], m['operation_path']].append(r)
        for batch in itertools.zip_longest(*groups.values()):
            for row in batch:
                if row is not None and len(selection) < per_label:
                    selection.append(row)
        if len(selection) != per_label:
            raise ValueError(f'無足夠不重複正常對照：{split} {len(selection)}/{per_label}')
        usage = Counter()
        for normal in selection:
            normal = copy.deepcopy(normal)
            meta = normal['metadata']
            pair = sha([split, normal['input']])
            meta['pair_group'] = pair
            chosen.append(normal)
            key = meta['platform'], normal['input']['method'], meta['operation_path']
            targets = targets_for(normal)
            offset = int(sha(key)[:8], 16)
            target = targets[(offset + usage[key]) % len(targets)]
            usage[key] += 1
            for label in ('sqli', 'xss'):
                if split == 'validation':
                    payloads = [{'value': value, 'source': 'httpParamsDataset', 'source_id': f'payload_full.csv:{line}',
                                 'family': None, 'commit': COMMIT, 'can_collect_http': False} for line, value in external[label]]
                else:
                    payloads = catalog[split][label]
                payload = payloads[int(sha([pair, label])[:8], 16) % len(payloads)]
                attack = clone(normal, target, {**payload, 'label': label})
                attack['metadata'].update(pair_group=pair, control_sample_id=normal['sample_id'])
                chosen.append(attack)
    return chosen


def export(output):
    if output.exists():
        raise ValueError('輸出目錄已存在，不覆寫舊版本')
    operations, hashes = read_documents()
    external, external_values, provenance, license_text = source_payloads()
    catalog = catalog_payloads(external_values)
    rows, _ = build(operations, external, catalog)
    resolver = Completion()
    notes = complete(rows, operations, resolver)
    rows = rebalance(rows, operations, external, catalog)
    fields = []
    for key, operation in sorted(operations.items()):
        samples = [r for r in rows if (r['metadata']['platform'], r['input']['method'], r['metadata']['operation_path']) == key]
        for (location, name), spec in operation['fields'].items():
            values = []
            for row in samples:
                found, value = (True, row['input']['body']) if name == '（本文）' else field_value(row['input'], location, name)
                if found:
                    values.append(value)
            if not values:
                raise ValueError(f'平衡取樣遺漏文件欄位 {key} {location}/{name}')
            note = notes.get((key, location, name), '互斥 header 的獨立候選')
            example = values[0]
            status = ('憑證安全遮蔽' if SENSITIVE.search(name) else '整個空本文是合法結構' if name == '（本文）'
                      else '條件商品種子待建立；結構已填' if '商品型別' in note
                      else '需實例定義自訂欄位' if name == 'customFields'
                      else '缺可追溯分類代碼' if '尚無可追溯' in note
                      else '選填關聯 null 接受方式待實測' if '實例若拒絕' in note
                      else '值已填；實機有效性待確認')
            fields.append({'平台': key[0], '集合': samples[0]['metadata']['split'], '方法': key[1], 'API': key[2],
                '位置': location, '參數': name, '文件型別': spec['type'], '填入值JSON': json.dumps(example, ensure_ascii=False),
                '來源與限制': note, '狀態': status, '存在筆數': len(values), '實機已驗證': False,
                '文件': spec['source'], '行號': spec['line']})
    output.mkdir(parents=True)
    stats = {}
    for split in ('train', 'test', 'validation'):
        data = [r for r in rows if r['metadata']['split'] == split]
        flat = []
        for row in data:
            req, meta = row['input'], row['metadata']
            flat.append({'樣本ID': row['sample_id'], '平台': meta['platform'], '集合': split,
                '候選類別': row['annotation']['proposed_label'], '方法': req['method'], 'API模板': meta['operation_path'],
                'Path': req['path'], 'Header_JSON': json.dumps(req['headers'], ensure_ascii=False),
                'Query_JSON': json.dumps(req['query'], ensure_ascii=False), 'Body_JSON': json.dumps(req['body'], ensure_ascii=False),
                '原始Query': req['raw_query'], '原始Body': req['raw_body'], '變動位置': meta['target_location'],
                '變動欄位': meta['target_parameter'], 'Payload原文': (meta['payload'] or {}).get('value'),
                '實際送出': False, '可正式訓練': False, '完整紀錄JSON': json.dumps(row, ensure_ascii=False)})
        write_csv(output / f'{split}.csv', flat)
        stats[split] = {'rows': len(data), 'labels': dict(Counter(r['annotation']['proposed_label'] for r in data))}
    write_csv(output / 'field-coverage.csv', fields)
    write_csv(output / 'external-payloads.csv', [{'類別': label, '來源紀錄起始行': line, 'payload': value, 'commit': COMMIT}
              for label, values in external.items() for line, value in values])
    (output / 'HTTPPARAMS-LICENSE.txt').write_text(license_text, encoding='utf-8')
    summary = {'splits': stats, 'ratio': '60:20:20', 'labels_balanced_within_each_split': True,
        'document_fields': len(fields), 'field_status': dict(Counter(f['狀態'] for f in fields)),
        'live_binding_markers_remaining': sum('${LIVE:' in json.dumps(r['input']) for r in rows),
        'http_executed': 0, 'training_approved': 0, 'medusa_included': False,
        'parameter_document_sha256': hashes, 'historical_evidence_sha256': resolver.evidence,
        'historical_session_sources': {f'{s}/{p}': source for (s, p), source in resolver.session_sources.items()},
        'external_source': provenance}
    (output / 'provenance.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'README.md').write_text('# 小規模 API 候選 v2\n\n'
        '420 筆候選，train/test/validation=252/84/84（60/20/20），各集合 normal/sqli/xss 等量。'
        '這個比例是方便檢查的小版本設計，不是跨平台評估的強制比例，也不是有效性的證明。\n\n'
        'train/test 只用 Bagisto＋Shopware，操作及本地攻擊家族不跨集合；validation 僅 Sylius，payload 使用固定外部來源。'
        'Medusa 不納入。來源及切分欄位只在 metadata，不作模型輸入。\n\n'
        '物件已依三份文件、原始 schema 與既有正常 HTTP 證據補形狀／值。憑證仍遮蔽，正常 ID 是歷史證據原值，'
        '不能推定目前仍有效。複合商品的結構範例不代表屬性／組合／預約種子已建立。全部候選未新送出、未核准訓練。\n\n'
        '欄位細節見 field-coverage.csv，待辦與規格差異另見完成紀錄.md；舊 small-api-v1 保留供對照。\n\n'
        '```json\n' + json.dumps(summary, ensure_ascii=False, indent=2) + '\n```\n', encoding='utf-8')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'sentinel/dataset/small-api-v2')
    print(json.dumps(export(parser.parse_args().output), ensure_ascii=False))
