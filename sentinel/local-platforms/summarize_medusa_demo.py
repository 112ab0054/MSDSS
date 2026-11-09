"""將實際HTTP證據與gateway分數按UUID比對，逐項列出79個API狀態。"""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPORTS = HERE / 'reports'


def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)


def main():
    # 補測完成後以新版完整證據為準，避免重跑此舊入口又把狀態降回42項。
    remaining = REPORTS / 'medusa-demo-v9-remaining.json'
    if remaining.is_file() and json.loads(remaining.read_text(encoding='utf-8')).get('outcome') == 'coverage_complete_with_limitations':
        from audit_medusa_runtime import audit
        audit(sync_inventory=False)
        return
    inventory = json.loads((ROOT / 'sentinel/analysis/api-extension/medusa-holdout-inventory.json').read_text(encoding='utf-8'))
    flow = json.loads((REPORTS / 'medusa-demo-v9-flow.json').read_text(encoding='utf-8'))
    probes = json.loads((REPORTS / 'medusa-demo-v9-readonly-probes.json').read_text(encoding='utf-8'))
    scores = {r['request_id']: r for r in json.loads((REPORTS / 'medusa-demo-v9-gateway-scores.json').read_text(encoding='utf-8'))['scores']}
    rows = []; observed = []
    for source, requests in [('normal_flow', flow['requests']), ('read_only_probes', probes['requests'])]:
        for r in requests:
            score = scores.get(r['request_id'])
            if score is None: raise ValueError('缺少實際gateway分數，不能用重算結果代替')
            observed.append({'source': source, 'request_id': r['request_id'], 'method': r['method'], 'api': r['operation_path'],
                'http_status': r['status'], 'business_verified': r['business_verified'],
                'intent': r.get('probe_intent', 'normal'), 'predicted': score['label'],
                'normal_score': score['probabilities']['normal'], 'sqli_score': score['probabilities']['sqli'],
                'xss_score': score['probabilities']['xss']})
    for operation in inventory['operations']:
        matching = [r for r in flow['requests'] if (r['method'], r['operation_path']) == (operation['method'], operation['path'])]
        status = '尚未測試'; reason = '不在本次正常購物流程；需額外功能、實例或測試情境'
        if matching:
            if any(r.get('version_difference') for r in matching):
                status = '版本／功能差異'; reason = next(r['version_difference'] for r in matching if r.get('version_difference'))
            elif any(r.get('precondition_limitation') for r in matching) and not any(r.get('business_verified') for r in matching):
                status = '前置條件不足'; reason = next(r['precondition_limitation'] for r in matching if r.get('precondition_limitation'))
            elif any(r.get('business_verified') for r in matching):
                status = '成功'; reason = '已對真實Medusa送出並完成記錄中的回應／業務斷言；不代表全部參數已覆蓋'
            else:
                status = '僅HTTP受理'; reason = '尚無足夠業務斷言，不列為完整成功'
        # 清單為空的目錄不捏造明細ID。
        if not matching and operation['method'] == 'GET' and operation['path'].endswith('/{id}'):
            parent = operation['path'][:-5]
            parents = [r for r in flow['requests'] if r['method'] == 'GET' and r['operation_path'] == parent]
            if parents and isinstance(parents[0].get('response_body'), dict):
                lists = [x for x in parents[0]['response_body'].values() if isinstance(x, list)]
                if lists and all(not x for x in lists): status = '前置條件不足'; reason = '真實目錄清單為空，沒有明細ID可測'
        rows.append({'method': operation['method'], 'api': operation['path'], 'status': status, 'reason': reason,
                     'http_statuses': ','.join(map(str, sorted({r['status'] for r in matching}))), 'request_count': len(matching)})
    assert len(rows) == 79
    write_csv(REPORTS / 'medusa-demo-v9-api-status.csv', rows)
    write_csv(REPORTS / 'medusa-demo-v9-predictions.csv', observed)
    checks = flow.get('business_checks', flow.get('checks', []))
    summary = {'actual_medusa_version': '2.21.0', 'gateway': 'http://127.0.0.1:18085', 'upstream': 'http://127.0.0.1:9100',
        'model_sha256': hashlib.sha256((ROOT / 'sentinel/gateway/model/model.json').read_bytes()).hexdigest(),
        'flow_outcome': flow['outcome'], 'flow_requests': len(flow['requests']), 'actual_gateway_score_matches': len(observed),
        'business_checks': len(checks), 'business_checks_passed': sum(bool(c['passed']) for c in checks),
        'api_status_counts': dict(Counter(r['status'] for r in rows)),
        'normal_intent_flow_predictions': dict(Counter(r['predicted'] for r in observed if r['source'] == 'normal_flow')),
        'read_only_probe_results': [{'intent': r['intent'], 'predicted': r['predicted']} for r in observed if r['source'] == 'read_only_probes'],
        'payment': 'pp_system_default; order authorized; captured_amount=0; no real charge',
        'scope': 'new isolated Sentinel gateway to existing real Medusa; not Mirage/storefront end-to-end or all79 business success',
        'training_data': False}
    (REPORTS / 'medusa-demo-v9-summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
