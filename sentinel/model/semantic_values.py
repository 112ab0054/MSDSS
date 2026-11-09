"""離線語義填值的資料庫目錄及地址關聯檢查，不驗證實機購物或郵遞。"""
import hashlib
import json


def audit_semantic_values(data_dir, sets, provenance):
    errors = []; config = provenance.get('semantic_correction', {}); catalogs = {}
    try:
        for platform in ('bagisto', 'sylius'):
            raw = (data_dir / (platform + '-database-catalog.json')).read_bytes()
            if hashlib.sha256(raw).hexdigest() != config['catalog_sha256'][platform]:
                errors.append(platform + '資料庫目錄指紋不符')
            catalogs[platform] = json.loads(raw)
            if not catalogs[platform].get('read_only'): errors.append('資料庫目錄缺少唯讀查核資訊')
        raw = (data_dir / 'semantic-policy.json').read_bytes()
        if hashlib.sha256(raw).hexdigest() != config['semantic_policy_sha256']:
            errors.append('語義填值規則指紋不符')
        policy = json.loads(raw)
    except (OSError, ValueError, KeyError, TypeError):
        return ['缺少完整語義填值規則或資料庫選項快照']
    languages = {p: {x['code'] for x in d['languages']} for p, d in catalogs.items()}
    countries = {p: {x['code'] for x in d['countries']} for p, d in catalogs.items()}
    country_ids = {v: k for k, v in policy['shopware_country_ids'].items()}
    states = {(x['country_code'], x['code']) for x in catalogs['bagisto']['states']}
    profiles = policy['address_profiles']
    for split, rows in sets.items():
        problems = []
        for row in rows:
            if row['annotation'].get('label', row['annotation'].get('proposed_label')) != 'normal': continue
            platform = row['metadata']['platform']; headers = row['input']['headers']
            for name, p in [('X-Locale', 'bagisto'), ('Accept-Language', 'sylius')]:
                if platform == p and name in headers and headers[name] not in languages[p]:
                    problems.append('語言不在資料庫目錄')
            def address(value, prefix=''):
                if not isinstance(value, dict): return
                def field(name):
                    key = prefix + name[0].upper() + name[1:] if prefix else name
                    return value.get(key)
                code = field('country') or field('countryCode')
                country_id = field('countryId')
                if country_id:
                    if country_id not in country_ids: problems.append('未知國家ID')
                    code = country_ids.get(country_id)
                if code:
                    if platform in countries and code not in countries[platform]: problems.append('國家不在資料庫目錄')
                    city = field('city'); postcode = field('postcode') or field('zipcode')
                    if city and postcode and (code, city, postcode) not in {(p[0], p[1], p[2]) for p in profiles}:
                        problems.append('國家城市郵遞區號未對應地址組合')
                    if platform == 'bagisto' and field('state') and (code, field('state')) not in states:
                        problems.append('州省不屬於指定國家')
                if not prefix:
                    for name in ('billingAddress', 'shippingAddress'):
                        if isinstance(value.get(name), dict): address(value[name])
                    for name in ('billing', 'shipping'):
                        if name + 'Country' in value: address(value, name)
            address(row['input']['body'])
        if problems: errors.append(split + '語義填值問題：' + '、'.join(sorted(set(problems))))
    return errors
