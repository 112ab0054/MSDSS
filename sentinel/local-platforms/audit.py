"""Read-only comparison of protected inputs; reports never change the active manifest."""
import collections
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
REPORTS = HERE / 'reports'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(name, data):
    (REPORTS / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    REPORTS.mkdir(exist_ok=True)
    baseline = read(HERE / 'protected-baseline.json')
    preserved = []
    for item in baseline:
        file = PROJECT / item['path']
        actual = hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else None
        preserved.append({**item, 'current_sha256': actual, 'unchanged': actual == item['sha256']})
    write('protected-files.json', {'all_unchanged': all(x['unchanged'] for x in preserved), 'files': preserved})
    manifest = read(PROJECT / 'sentinel/analysis/api-extension/active-api-manifest.json')
    selected = read(HERE / 'versions.json')
    original = read(PROJECT / manifest['sources']['bagisto']['contract'])
    release = read(HERE / 'upstream/bagisto-api-v2.4.4-shop.json')
    differences = []
    for op in manifest['operations']:
        if op['platform'] != 'bagisto':
            continue
        old = original['paths'][op['path']][op['method'].lower()]
        new = release['paths'].get(op['path'], {}).get(op['method'].lower())
        changed = [k for k in ('parameters', 'requestBody', 'responses', 'security') if old.get(k) != (new or {}).get(k)]
        differences.append({'method': op['method'], 'path': op['path'], 'present_in_release_snapshot': new is not None,
                            'changed_sections': changed, 'live_verified': False})
    write('bagisto-release-contract-comparison.json', {'live_test': False, 'operations': differences})
    evidence = []
    for file in REPORTS.glob('*.json'):
        if not any(file.name.startswith(p + '-') for p in ('bagisto', 'shopware', 'sylius')):
            continue
        data = read(file)
        if data.get('outcome') == 'passed':
            evidence.append((file.name, data))
    rows = []
    sylius_live = read(HERE / 'upstream/sylius-standard-2.2.4-core-2.2.12-live-openapi.json')
    for op in manifest['operations']:
        platform = op['platform']
        matches = [(name, row) for name, data in evidence if data.get('platform') == platform
                   for row in data.get('requests', []) if row.get('method') == op['method']
                   and row.get('operation_path') == op['path'] and row.get('business_verified')
                   and 200 <= row.get('status', 0) < 300]
        redirects = [(name, row) for name, data in evidence if data.get('platform') == platform
                     for row in data.get('requests', []) if row.get('method') == op['method']
                     and row.get('operation_path') == op['path'] and row.get('business_verified')
                     and row.get('status') in (301, 302, 307, 308)]
        absent = platform == 'sylius' and op['method'].lower() not in sylius_live['paths'].get(op['path'], {})
        status = '成功' if matches or redirects else '版本差異' if absent else '尚未測試'
        rows.append({'platform': platform, 'method': op['method'], 'path': op['path'], 'role': op['role'],
                     'test_status': status,
                     'reason': '實機匯出規格沒有此路由；未以 HTTP 404 當成業務驗證' if absent else
                         '301 canonical 跳轉後已核對同一商品' if redirects and not matches else
                         '完整正常流程與業務斷言' if matches else '尚無實機通過證據',
                     'evidence_files': sorted({name for name, _ in matches + redirects}),
                     'contract_status': '實例規格缺失' if absent else '已保存實例規格，尚未逐欄核對全部參數',
                     'ready_for_collection': False})
    write('api-status.json', {'operation_count': len(rows), 'counts': dict(collections.Counter(r['test_status'] for r in rows)),
                             'note': '成功僅採用完整流程 passed 且有業務斷言的證據；其他操作不由靜態檢查推定成功。',
                             'operations': rows})
    with (REPORTS / 'api-status.csv').open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    assert len(rows) == 64
    assert all(not s['ready_for_collection'] for s in manifest['sources'].values())
    print(json.dumps({'protected_unchanged': all(x['unchanged'] for x in preserved),
                      'api_status_counts': dict(collections.Counter(r['test_status'] for r in rows)),
                      'selected_versions': selected['selected_on']}, ensure_ascii=False))
    return 0 if all(x['unchanged'] for x in preserved) else 1


if __name__ == '__main__':
    raise SystemExit(main())
