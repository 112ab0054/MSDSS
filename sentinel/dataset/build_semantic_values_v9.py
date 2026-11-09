"""按文件語義及唯讀資料庫目錄多樣化正常控制；保留原攻擊、骨架與切分。"""
import argparse
import base64
import copy
import gzip
import io
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'sentinel/model'))
from data_io import read_rows
from request_input import SENSITIVE
from document_values import constants, type_names, violations
from build_small_dataset import sha, read_documents, field_value, finalize, write_csv
from build_train_v5 import flat
from build_xss_v3 import set_field
from annotate_attack_facets import attack_facets, COLUMN

SPLITS = ('train', 'test', 'validation', 'challenge')
# 示例地址只供離線字串分類，不表示可投遞、真人地址或已完成購物。
PROFILES = [
    ('US', 'Seattle', '98101', 'WA', 'Washington', 'Pine Street'),
    ('DE', 'Berlin', '10115', 'BER', 'Berlin', 'Invalidenstrasse'),
    ('FR', 'Paris', '75002', '75', 'Paris', 'Rue Montmartre'),
    ('CA', 'Toronto', 'M5V 2T6', 'ON', 'Ontario', 'King Street West'),
    ('US', 'Boston', '02108', 'MA', 'Massachusetts', 'Beacon Street'),
    ('DE', 'Munich', '80331', 'BAY', 'Bayern', 'Sendlinger Strasse'),
    ('FR', 'Lyon', '69002', '69', 'Rhône', 'Rue de la Charite'),
    ('CA', 'Vancouver', 'V6B 1A1', 'BC', 'British Columbia', 'Water Street'),
    ('US', 'Austin', '78701', 'TX', 'Texas', 'Congress Avenue'),
    ('DE', 'Hamburg', '20095', 'HAM', 'Hamburg', 'Steinstrasse'),
    ('FR', 'Marseille', '13001', '13', 'Bouches-du-Rhône', 'Rue Paradis'),
    ('CA', 'Montreal', 'H2Y 1C6', 'QC', 'Quebec', 'Rue Saint Paul'),
]
GIVEN = 'Emily Noah Sofia Lucas Amelie Oliver Hannah Felix Clara Leo Maya Ethan Alice Theo Eva Liam Elise Henry Nina Oscar Mila Arthur Zoe Louis'.split()
FAMILY = 'Chen Martin Fischer Brown Bernard Wilson Weber Taylor Laurent Anderson Schneider Thomas Moreau Jackson Wagner White Petit Harris Becker Clark Dubois Lewis Hoffmann Walker'.split()
COMPANY = ['Cedar Textiles', 'Maple Books', 'Harbour Ceramics', 'Willow Furniture', 'North Star Outfitters',
           'River Paperworks', 'Oak Homeware', 'Seaside Crafts', 'Birch Kitchen', 'Meadow Clothing',
           'Juniper Stationery', 'Pine Outdoor', 'Elm Workshop', 'Aspen Design', 'Iris Goods',
           'Fern Accessories', 'Alder Lighting', 'Orchid Studio', 'Hazel Toys', 'Sage Trading',
           'Laurel Fabrics', 'Acorn Supplies', 'Dahlia Market', 'Linden Sports']
DEPT = ['Customer Service', 'Purchasing', 'Warehouse', 'Accounting', 'Retail Sales', 'Operations',
        'Online Sales', 'Product Design', 'Logistics', 'Quality Assurance', 'Returns Desk', 'Office Supplies']
NOTES = ['Please leave the parcel at reception', 'Please use the side entrance', 'Please include a paper receipt',
         'Please pack the glass items separately', 'Please use recyclable packaging', 'Please ring the doorbell once',
         'Please deliver during office hours', 'Please add a blank gift card', 'Please keep the two items together',
         'Please avoid extra plastic bags', 'Please include the care instructions', 'Please label the package as a gift',
         'Please use a small shipping box', 'Please contact the reception desk', 'Please attach the return instructions',
         'Please place the invoice inside the box', 'Bitte an der Rezeption abgeben', 'Bitte die Rechnung beilegen',
         'Merci de joindre le recu', 'Merci de proteger les articles fragiles', 'Please check the selected colour',
         'Please fold the shirts neatly', 'Please include the product manual', 'Please use the main entrance']
SEARCH = [a + ' ' + b for a in ['blue', 'linen', 'cotton', 'navy', 'summer', 'wool', 'ceramic', 'recycled']
          for b in ['shirt', 'bag', 'scarf', 'notebook', 'jacket', 'gift set']]
ADDRESS_FIELDS = {'address1', 'street', 'address', 'city', 'country', 'countryCode', 'countryId',
                  'state', 'postcode', 'zipcode', 'provinceName', 'phone', 'phoneNumber'}
STRUCTURAL = {'sort', 'sort[]', 'order', 'price', 'suggest', 'type', 'total-count-mode', '_criteria',
              'manufacturer', 'properties', 'property-whitelist', 'imageFilter', 'sw-context-source'}


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def load_catalogs():
    catalogs = {}
    sources = []
    for platform in ('bagisto', 'sylius'):
        path = ROOT / f'sentinel/local-platforms/reports/{platform}-database-catalog.json'
        data = json.loads(path.read_text(encoding='utf-8'))
        if not data.get('read_only') or not data.get('languages'):
            raise ValueError('缺少唯讀資料庫選項證據')
        catalogs[platform] = data
        sources.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path.read_bytes())})
    countries = {}
    for path in sorted((ROOT / 'sentinel/local-platforms/reports').glob('shopware-*.json')):
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        if data.get('outcome') != 'passed':
            continue
        found = []
        def walk(x):
            if isinstance(x, dict):
                if x.get('apiAlias') == 'country' and x.get('active') and x.get('iso'):
                    countries[x['iso']] = x['id']; found.append(x['iso'])
                for v in x.values():
                    if isinstance(v, (dict, list)): walk(v)
            elif isinstance(x, list):
                for v in x: walk(v)
        walk(data)
        if found:
            sources.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path.read_bytes())})
    catalogs['shopware_countries'] = countries
    return catalogs, sources


def name_parts(name):
    leaf = name.split('.')[-1]
    if '.' in name and name.split('.')[0] in ('billingAddress', 'shippingAddress'):
        return name.split('.')[0], leaf
    for prefix in ('billing', 'shipping'):
        if leaf.startswith(prefix) and len(leaf) > len(prefix):
            rest = leaf[len(prefix):]
            return prefix, rest[:1].lower() + rest[1:]
    return '', leaf


def strategy(location, name, spec):
    _, leaf = name_parts(name)
    if SENSITIVE.search(name): return 'credential_redacted'
    if location == 'path': return 'existing_instance_identifier'
    if 'string' not in type_names(spec): return 'non_string_or_structure'
    if name in ('X-Locale', 'Accept-Language', 'sw-language-id') or leaf == 'languageId': return 'database_language'
    if leaf in ADDRESS_FIELDS: return 'coherent_address'
    if leaf in ('firstName', 'lastName', 'email', 'username', 'company', 'companyName', 'department',
                'address2', 'additionalAddressLine1', 'additionalAddressLine2', 'title', 'dateOfBirth',
                'specialNote', 'notes', 'customerComment', 'term', 'search', 'query', 'label', 'vatId',
                'affiliateCode', 'campaignCode') or name == 'translations.name' or leaf.endswith('Url'):
        return 'semantic_free_text'
    if name in STRUCTURAL: return 'structured_value_not_arbitrary_text'
    if name in ('X-Channel', 'X-Currency'): return 'database_channel_or_currency'
    if name.split('.')[-1] in ('paymentMethod', 'shippingMethod', 'productVariant', 'id'): return 'existing_identifier_or_unbound_optional'
    if constants(spec): return 'documented_enum'
    if re.search(r'(?:Id|Ids|Code|_id)$|^(?:code|ids)$', leaf): return 'existing_identifier_or_unbound_optional'
    if 'string' not in type_names(spec): return 'non_string_or_structure'
    return 'needs_semantic_review'


def build(source, output):
    if output.exists(): raise ValueError('保留舊版，輸出不可已存在')
    ops, docs = read_documents(); catalogs, sources = load_catalogs()
    counters = Counter(); address_counters = Counter(); changes = []; mapping = []; preserved = []; sets = {}
    lookup_languages = json.loads((source / 'shopware-language-inventory.json').read_text(encoding='utf-8'))
    sw_languages = sorted(x['id'] for x in lookup_languages['languages'] if x.get('accepted'))
    sw_countries = catalogs['shopware_countries']
    country_pools = {'bagisto': {x['code'] for x in catalogs['bagisto']['countries']},
                     'sylius': {x['code'] for x in catalogs['sylius']['countries'] if x['enabled'] == '1'},
                     'shopware': set(sw_countries)}
    states = {(x['country_code'], x['code']) for x in catalogs['bagisto']['states']}
    for profile in PROFILES:
        if (profile[0], profile[3]) not in states: raise ValueError('地址範例州省不在Bagisto資料庫')
    old_sets = {s: read_rows(source / (s + '.csv')) for s in SPLITS}
    for split in SPLITS:
        groups = defaultdict(list)
        for row in old_sets[split]: groups[row['metadata']['pair_group']].append(row)
        rebuilt = {}
        for old_pair, triple in groups.items():
            normal = next(r for r in triple if r['annotation']['proposed_label'] == 'normal')
            req = copy.deepcopy(normal['input']); platform = normal['metadata']['platform']
            key = platform, req['method'], normal['metadata']['operation_path']
            context = normal['metadata'].get('benign_content_context') or {}
            profiles = {}; edits = []
            # 文件只把地址列為object時，仍處理目前已存在的地址子欄位；
            # 子欄位語義／約束引用同平台已記錄的地址欄位，不新增未知屬性。
            operation_fields = dict(ops[key]['fields'])
            if isinstance(req['body'], dict):
                for parent in ('billingAddress', 'shippingAddress'):
                    address = req['body'].get(parent)
                    if not isinstance(address, dict): continue
                    parent_spec = operation_fields.get(('body', parent))
                    if parent_spec is None: continue
                    for child, value in address.items():
                        candidates = [spec for k, op in ops.items() if k[0] == platform
                                      for (loc, name), spec in op['fields'].items()
                                      if loc == 'body' and name == child]
                        if candidates and isinstance(value, (str, type(None))):
                            operation_fields['body', parent + '.' + child] = candidates[0]
            # 先決定每組地址，讓較早出現的VAT等相關欄位也能引用同一國家。
            for (loc, name), spec in operation_fields.items():
                if strategy(loc, name, spec) != 'coherent_address' or not field_value(req, loc, name)[0]: continue
                prefix, _ = name_parts(name)
                if prefix not in profiles:
                    valid = [p for p in PROFILES if p[0] in country_pools[platform]]
                    ai = address_counters[platform, prefix]; address_counters[platform, prefix] += 1
                    profiles[prefix] = (valid[ai % len(valid)], ai)
            for (loc, name), spec in operation_fields.items():
                present, old = field_value(req, loc, name)
                if not present: continue
                policy = strategy(loc, name, spec)
                if policy in ('credential_redacted', 'existing_instance_identifier', 'structured_value_not_arbitrary_text', 'database_channel_or_currency',
                              'existing_identifier_or_unbound_optional', 'non_string_or_structure', 'needs_semantic_review'): continue
                if context.get('value') is not None and old == context['value']:
                    preserved.append({'split': split, 'sample_id': normal['sample_id'], 'parameter': name,
                                      'reason': 'preserve_original_benign_literal_or_external_normal_source'})
                    continue
                counters[platform, loc, name] += 1; index = counters[platform, loc, name] - 1
                prefix, leaf = name_parts(name); new = old; basis = policy
                if policy == 'database_language':
                    if name == 'X-Locale': pool = sorted(x['code'] for x in catalogs['bagisto']['languages'])
                    elif name == 'Accept-Language':
                        pool = sorted(set(x['code'] for x in catalogs['sylius']['languages']) & set(constants(spec)))
                    else: pool = sw_languages
                    if not pool: raise ValueError('資料庫語系與文件無交集')
                    # v8已平衡的Shopware header不重新洗牌；body語言切換用另個有效ID。
                    new = old if name == 'sw-language-id' else pool[index % len(pool)]
                    basis = 'database_catalog_offline_not_channel_http_verified'
                elif policy == 'coherent_address':
                    if prefix not in profiles:
                        valid = [p for p in PROFILES if p[0] in country_pools[platform]]
                        ai = address_counters[platform, prefix]; address_counters[platform, prefix] += 1
                        profiles[prefix] = (valid[ai % len(valid)], ai)
                    (country, city, postcode, state, province, street), ai = profiles[prefix]
                    address = f'{street} {12 + ai * 3}'
                    phone = {'US': '1202555', 'CA': '1416555', 'DE': '4930555', 'FR': '331555'}[country] + f'{100 + ai % 100:04d}'
                    new = {'address1': address, 'address': address, 'street': address, 'city': city,
                           'country': country, 'countryCode': country, 'countryId': sw_countries.get(country),
                           'state': state, 'postcode': postcode, 'zipcode': postcode, 'provinceName': province,
                           'phone': phone, 'phoneNumber': phone}[leaf]
                elif policy == 'documented_enum':
                    pool = constants(spec); new = pool[index % len(pool)]
                    # 只多樣化字串列舉，不把數字或布林型別改成字串。
                    if not isinstance(old, str): new = old
                elif policy == 'semantic_free_text':
                    if leaf == 'firstName': new = GIVEN[index % len(GIVEN)]
                    elif leaf == 'lastName': new = FAMILY[index % len(FAMILY)]
                    elif leaf in ('email', 'username'): new = GIVEN[index % len(GIVEN)].lower() + '.' + FAMILY[(index * 5) % len(FAMILY)].lower() + f'{index // len(GIVEN) or ""}@example.test'
                    elif leaf in ('company', 'companyName'): new = COMPANY[index % len(COMPANY)]
                    elif leaf == 'department': new = DEPT[index % len(DEPT)]
                    elif leaf in ('address2', 'additionalAddressLine1', 'additionalAddressLine2'):
                        new = ['Apartment', 'Suite', 'Floor', 'Building', 'Unit', 'Office'][index % 6] + ' ' + str(2 + index)
                    elif leaf == 'dateOfBirth': new = f'{1976 + index % 25:04d}-{index % 12 + 1:02d}-{index % 27 + 1:02d}'
                    elif leaf == 'title': new = ['Mr', 'Ms', 'Dr', 'Prof'][index % 4]
                    elif leaf in ('specialNote', 'notes', 'customerComment'): new = NOTES[index % len(NOTES)]
                    elif leaf in ('term', 'search', 'query', 'label') or name == 'translations.name': new = SEARCH[index % len(SEARCH)]
                    elif leaf in ('affiliateCode', 'campaignCode'): new = ['spring-newsletter', 'member-week', 'summer-catalog', 'welcome-offer', 'autumn-home', 'winter-gifts'][index % 6]
                    elif leaf.endswith('Url'):
                        kind = 'success' if 'Success' in leaf else 'cancel' if 'Cancel' in leaf else 'failure'
                        new = f'http://127.0.0.1:18081/test-payment/{["web", "mobile", "checkout", "guest"][index % 4]}/{index + 1}/{kind}'
                    elif leaf == 'vatId':
                        # 合成稅號字串僅代表格式樣本，未登記或驗證，並非有效稅籍證明。
                        country = profiles.get(prefix, (PROFILES[index % len(PROFILES)], 0))[0][0]
                        new = ('DE' + str(900000000 + index)) if country == 'DE' else ('FR00' + str(900000000 + index)) if country == 'FR' else ''
                    else: raise ValueError('自由文字缺少語義策略：' + name)
                if new == old: continue
                errors = violations(new, loc, name, spec)
                if errors: raise ValueError(str((platform, loc, name, errors)))
                set_field(req, loc, name, new)
                edits.append({'split': split, 'platform': platform, 'old_normal_sample_id': normal['sample_id'],
                    'location': loc, 'parameter': name, 'old_value': canon(old), 'new_value': canon(new),
                    'basis': basis, 'document': spec['source'], 'document_line': spec['line']})
            # 壓縮criteria與更新後的query保持一致；這是明確資料修正，不是推論正規化。
            if platform == 'shopware' and '_criteria' in req['query']:
                allowed = {'page', 'limit', 'term', 'query', 'filter', 'ids', 'sort', 'associations', 'post-filter',
                           'aggregations', 'fields', 'grouping', 'includes', 'excludes', 'total-count-mode'}
                criteria = {n.removesuffix('[]'): v for n, v in req['query'].items() if n.removesuffix('[]') in allowed}
                raw = json.dumps(criteria, ensure_ascii=False, separators=(',', ':')).encode(); buffer = io.BytesIO()
                with gzip.GzipFile(fileobj=buffer, mode='wb', mtime=0, filename='') as stream: stream.write(raw)
                req['query']['_criteria'] = base64.urlsafe_b64encode(buffer.getvalue()).decode().rstrip('=')
            finalize(req, key[2])
            pair = sha(['semantic-values-v9', old_pair, req]); ids = {}
            for old in triple:
                row = copy.deepcopy(old); label = row['annotation']['proposed_label']; request = copy.deepcopy(req)
                if label != 'normal':
                    m = old['metadata']; set_field(request, m['target_location'], m['target_parameter'], m['payload']['value']); finalize(request, key[2])
                row['input'] = request; row['sample_id'] = sha([pair, label, request]); ids[label] = row['sample_id']
                row['metadata'].update(pair_group=pair, semantic_source_sample_id=old['sample_id'],
                    semantic_values_revision=9, origin='document-v9-semantic-offline', http_executed=False, business_verified=False)
                rebuilt[old['sample_id']] = row
                mapping.append({'split': split, 'old_sample_id': old['sample_id'], 'new_sample_id': row['sample_id'],
                                'input_changed': old['input'] != request})
            for old in triple:
                if old['annotation']['proposed_label'] != 'normal': rebuilt[old['sample_id']]['metadata']['control_sample_id'] = ids['normal']
            changes.extend(edits)
        sets[split] = [rebuilt[r['sample_id']] for r in old_sets[split]]
    all_inputs = [sha(r['input']) for rows in sets.values() for r in rows]
    if len(set(all_inputs)) != len(all_inputs): raise ValueError('修正後重複請求，不丟棄或湊數')
    # 620個文件位置逐一列出狀態，另彙整跨API同名欄位的實際多樣性。
    fields = []; aggregate = {}
    for key, op in sorted(ops.items()):
        old_rows = [r for rs in old_sets.values() for r in rs if r['annotation']['proposed_label'] == 'normal' and (r['metadata']['platform'], r['input']['method'], r['metadata']['operation_path']) == key]
        new_rows = [r for rs in sets.values() for r in rs if r['annotation']['proposed_label'] == 'normal' and (r['metadata']['platform'], r['input']['method'], r['metadata']['operation_path']) == key]
        for (loc, name), spec in op['fields'].items():
            old_values = [field_value(r['input'], loc, name)[1] for r in old_rows if field_value(r['input'], loc, name)[0]]
            new_values = [field_value(r['input'], loc, name)[1] for r in new_rows if field_value(r['input'], loc, name)[0]]
            policy = strategy(loc, name, spec)
            status = 'absent_optional_or_document_branch' if not new_values else 'fewer_than_three_occurrences' if len(new_values) < 3 else policy
            fields.append({'platform': key[0], 'method': key[1], 'api': key[2], 'location': loc, 'parameter': name,
                'meaning': spec['meaning'], 'document': spec['source'], 'document_line': spec['line'], 'strategy': policy,
                'normal_occurrences': len(new_values), 'before_unique': len(set(map(canon, old_values))),
                'after_unique': len(set(map(canon, new_values))), 'status': status})
            agg = aggregate.setdefault((key[0], loc, name), {'old': [], 'new': [], 'strategy': policy})
            agg['old'].extend(old_values); agg['new'].extend(new_values)
    diversity = []
    for (platform, loc, name), values in sorted(aggregate.items()):
        if not values['new']: continue
        unique = len(set(map(canon, values['new']))); count = len(values['new'])
        policy = values['strategy']
        if policy == 'semantic_free_text' and count >= 3 and unique < 3:
            raise ValueError('自由文字仍過於單一：' + str((platform, loc, name, count, unique)))
        diversity.append({'platform': platform, 'location': loc, 'parameter': name, 'strategy': policy,
            'normal_occurrences': count, 'before_unique': len(set(map(canon, values['old']))), 'after_unique': unique,
            'limit': 'only_one_or_two_occurrences_do_not_duplicate_rows' if count < 3 else 'database_or_fixed_options' if policy != 'semantic_free_text' else 'semantic_pool_and_preserved_source_controls'})
    output.mkdir(parents=True)
    for name in ('skeleton-catalog.csv', 'external-payloads.csv', 'HTTPPARAMS-LICENSE.txt', 'attack-facets-rules.json',
                 'document-value-rules.json', 'shopware-language-inventory.json'):
        shutil.copy2(source / name, output / name)
    for platform in ('bagisto', 'sylius'):
        shutil.copy2(ROOT / f'sentinel/local-platforms/reports/{platform}-database-catalog.json', output / f'{platform}-database-catalog.json')
    (output / 'shopware-historical-country-ids.json').write_text(json.dumps({'countries': sw_countries, 'sources': sources}, ensure_ascii=False, indent=2), encoding='utf-8')
    semantic_policy = {'address_profiles': PROFILES, 'shopware_country_ids': sw_countries,
                       'catalog_scope': 'database_catalog_offline_not_channel_http_verified'}
    (output / 'semantic-policy.json').write_text(json.dumps(semantic_policy, ensure_ascii=False, indent=2), encoding='utf-8')
    for split, rows in sets.items():
        values = []
        for r in rows:
            value = flat(r); value[COLUMN] = '；'.join(attack_facets(r)); values.append(value)
        write_csv(output / (split + '.csv'), values)
    write_csv(output / 'semantic-value-changes.csv', changes); write_csv(output / 'semantic-source-sample-map.csv', mapping)
    write_csv(output / 'document-field-status.csv', fields); write_csv(output / 'free-text-diversity.csv', diversity)
    write_csv(output / 'preserved-source-controls.csv', preserved)
    saved = json.loads((source / 'provenance.json').read_text(encoding='utf-8'))
    saved.update(dataset_revision='v9-semantic-values', parent_dataset=source.name,
        parent_csv_sha256={s: sha((source / (s + '.csv')).read_bytes()) for s in SPLITS}, parameter_document_sha256=docs,
        frozen_holdout_sha256={s: sha((output / (s + '.csv')).read_bytes()) for s in SPLITS if s != 'train'},
        holdout_change_reason='Explicit user-requested semantic diversity; all normal controls and paired backgrounds updated, no metric-based selection',
        semantic_correction={'field_changes': len(changes), 'document_positions': len(fields), 'input_rows_changed': sum(x['input_changed'] for x in mapping),
            'database_sources': sources, 'language_scope': 'database catalogue as requested; Sylius channel assignments remain en_US; no HTTP verification',
            'address_scope': 'synthetic coherent country/city/postcode/state profiles; not verified deliverability',
            'generator_sha256': sha(Path(__file__).read_bytes().replace(b'\r\n', b'\n')),
            'semantic_policy_sha256': sha((output / 'semantic-policy.json').read_bytes()),
            'catalog_sha256': {p: sha((output / f'{p}-database-catalog.json').read_bytes()) for p in ('bagisto', 'sylius')},
            'preserved_source_controls': len(preserved), 'http_executed': 0})
    (output / 'provenance.json').write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'README.md').write_text('# v9：按參數含意產生多樣化文字\n\n原v8保留。1098筆、標籤、集合、骨架與攻擊原文不變，正常控制及配對背景明確修正，原文不是在推論時正規化。\n\nBagisto資料庫只有en，不能捏造其他已建立語言。Sylius使用資料庫與文件交集的8種語言，現有通路僅en_US，按使用者指定作資料庫目錄範圍的離線訓練，沒有假稱這些語言已在通路HTTP驗收。國家與州省使用資料庫選項；地址、人名、公司、電話與稅號文字都是合成示例，不表示真實聯絡或稅籍有效。\n\n自由字串按含意改寫，保留原正常字面程式碼對照及外部normal內容。只有1或2筆的欄位最多只有1或2個不同值，不為湊多樣性複製資料。固定值、憑證、實例ID與結構化值另列原因。620個文件位置皆有狀態；整批仍offline，需重新訓練，不沿用舊版模型分數或自動替換gateway。\n\n' + json.dumps(saved['semantic_correction'], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return saved['semantic_correction']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'sentinel/dataset/small-api-v8')
    parser.add_argument('--output', type=Path, default=ROOT / 'sentinel/dataset/small-api-v9')
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output), ensure_ascii=False, indent=2))
