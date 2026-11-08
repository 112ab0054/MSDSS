"""Compare the retained 77-operation document, current inventory and bundled specification."""
import hashlib
import json
from pathlib import Path
import re
import yaml
from collections import Counter

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent


def main():
    inventory = json.loads((PROJECT / 'sentinel/analysis/api-extension/medusa-holdout-inventory.json').read_text(encoding='utf-8'))
    spec_path = PROJECT / inventory['source']
    spec = yaml.safe_load(spec_path.read_text(encoding='utf-8'))
    legacy = (PROJECT / 'Medusa_77_API_填寫參數.md').read_text(encoding='utf-8')
    old_ops = set(re.findall(r'`(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+([^`\s]+)`', legacy))
    selected = {(o['method'], o['path']) for o in inventory['operations']}
    actual = {(m.upper(), p) for p, methods in spec['paths'].items() for m in methods
              if m.lower() in ('get', 'post', 'put', 'patch', 'delete', 'head', 'options')}
    passed = {}
    limitations = {}
    probes = {}
    for path in (HERE / 'reports').glob('medusa-*.json'):
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('outcome') != 'passed':
            continue
        for row in data.get('requests', []):
            key = (row['method'], row['operation_path'])
            if row.get('precondition_limitation'):
                limitations[key] = (row['precondition_limitation'], path.name)
            if row.get('route_probe_only'):
                probes[key] = (row.get('status'), path.name)
            if row.get('business_verified') and 200 <= row.get('status', 0) < 300:
                passed.setdefault((row['method'], row['operation_path']), []).append(path.name)
    routes = json.loads((HERE / 'reports/medusa-2.22.4-code-routes.json').read_text(encoding='utf-8'))
    def normalize(path):
        return re.sub(r'\{[^}]+\}', '{}', path.replace('/auth/customer/', '/auth/{actor_type}/'))
    code_routes = {(method, normalize(r['path'])) for r in routes for method in r['methods']}
    operations = []
    for op in inventory['operations']:
        key = (op['method'], op['path'])
        conditional = any(x in op['path'] for x in ('mfa', 'verification', 'callback', 'reset-password', '/update'))
        code_present = (op['method'], normalize(op['path'])) in code_routes
        missing = key in probes and probes[key][0] == 404 and not code_present
        status = '成功' if key in passed else '版本差異' if missing else '前置條件不足' if conditional or key in limitations else '尚未測試'
        reason = '有真實回應與業務斷言證據（主流程或獨立功能探查）' if key in passed else (
            'bundled 規格列有，但原生／工作區編譯 route 無對應且本機探查 404；不是業務成功' if missing else
            'manual 提供者 canCalculate()=false、calculatePrice() 明確拋錯；本機 calculate 回 500。需要支援計價的提供者；固定費率配送與結帳已成功。' if op['path'] == '/store/shipping-options/{id}/calculate' else
            limitations[key][0] if key in limitations else
            'MFA 實機註冊回 400：未配置 MFA encryption key；不以拒絕回應當成成功' if '/mfa/' in op['path'] else
            '沒有郵件／第三方登入／驗證碼送達的完整情境，不能使用虛假 Token 補造成功' if conditional else
            '尚無通過的實機情境；退貨須已履約訂單、移轉須雙方與有效移轉 token、促銷須有效折扣資料')
        proof = sorted(set(passed.get(key, [])))
        if missing:
            proof.append(probes[key][1])
        if key in limitations and not proof:
            proof.append(limitations[key][1])
        operations.append({**op, 'in_legacy_77_document': key in old_ops, 'in_current_bundled_spec': key in actual,
            'in_installed_code_routes': code_present, 'runtime_status': status,
            'runtime_reason': reason, 'evidence_files': proof})
    report = {'application_version': inventory['application_version'], 'spec_info_version': spec['info']['version'],
        'spec_sha256': hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        'source_hash_matches_inventory': hashlib.sha256(spec_path.read_bytes()).hexdigest() == inventory['sha256'],
        'legacy_operation_count': len(old_ops), 'selected_operation_count': len(selected), 'bundled_operation_count': len(actual),
        'selected_missing_from_spec': sorted(selected - actual), 'legacy_missing_from_spec': sorted(old_ops - actual),
        'added_since_legacy': sorted(selected - old_ops),
        'existing_unmodified_container_observation': {'container': 'mirage-commerce-real-medusa-1', 'port': 9100,
            'installed_medusa_version': '2.21.0', 'node_version': '22.23.2',
            'method': 'Read-only package metadata via docker exec; no service configuration or database writes',
            'interpretation': 'This separate pre-existing container is not evidence of the MSDSS 2.22.4 deployment; the historical port-8000 observation cannot be reconstructed from it.'},
        'isolated_test_target': 'http://127.0.0.1:18084', 'training_or_tuning_on_medusa': False,
        'status_counts': dict(Counter(o['runtime_status'] for o in operations)), 'operations': operations}
    (HERE / 'reports/medusa-api-status.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Medusa 選定 API 與舊文件核對紀錄', '', '更新日期：2026-11-08（Asia/Taipei）。原 77 API 文件保留，這份是新增的核對結果。', '',
        f"- 舊文件：{len(old_ops)} 個操作；現行選定：{len(selected)} 個；bundled 規格：{len(actual)} 個。",
        f"- 應用套件固定 {inventory['application_version']}；bundled OpenAPI info.version={spec['info']['version']}，兩者不混用。",
        '- 目前既有 9100 容器另經唯讀確認為 Medusa 2.21.0；本次另建 18084 的 2.22.4，兩者資料庫隔離，不能補造舊 8000 測試細節。',
        '- 所有有副作用的本次測試只允許獨立的 127.0.0.1:18084，不操作既有 Medusa／Mirage 資料庫。',
        '- 這次核對 API、契約與正常流程，不使用 Medusa 訓練模型、選特徵或調門檻。', '', '## 舊清單與現行清單差異', '']
    for method, path in sorted(selected - old_ops):
        lines.append(f'- 現行新增 `{method} {path}`；不直接改寫舊文件。')
    lines += ['', f'舊操作在現行規格中缺失：{len(old_ops - actual)}；選定操作在現行規格中缺失：{len(selected - actual)}。這只證明契約路徑／方法存在，不代表每個操作都已實機成功。', '',
        '## 逐操作實測狀態', '', '| Method | Path | 舊 77 清單 | 現行契約 | 實測狀態 | 說明／證據 |', '|---|---|---|---|---|---|']
    for op in operations:
        proof = op['runtime_reason'] + ('；' + ', '.join(op['evidence_files']) if op['evidence_files'] else '')
        lines.append(f"| {op['method']} | `{op['path']}` | {'有' if op['in_legacy_77_document'] else '無'} | {'存在' if op['in_current_bundled_spec'] else '缺失'} | {op['runtime_status']} | {proof} |")
    lines += ['', '## 解讀限制', '', '統計：' + '、'.join(f'{k} {v}' for k, v in report['status_counts'].items()) + '。', '',
        '路徑／方法、文件版本與實機情境分開核對。尚未逐欄確認的舊參數含義不因路徑存在而視為正確。具體參數錯誤與證據見 [Medusa_API_參數差異.md](Medusa_API_參數差異.md)。MFA、郵件驗證、第三方登入及重設流程需要各自前置條件，不能使用虛假 Token 或 401／404 代替驗證。路由探查可使用明確標示的未發行禮卡／儲值帳戶識別值，只用於路由與程式碼比對，從不當成正常業務成功。', '']
    (HERE / 'Medusa_API_核對紀錄.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('legacy_operation_count', 'selected_operation_count', 'bundled_operation_count', 'source_hash_matches_inventory', 'added_since_legacy')}, ensure_ascii=False))
    return 0 if selected <= actual and old_ops <= actual and report['source_hash_matches_inventory'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
