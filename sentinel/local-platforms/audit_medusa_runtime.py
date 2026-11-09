"""核對79操作的HTTP／業務／負向探查證據；可明確同步manifest runtime欄位。"""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPORTS = HERE / 'reports'
INVENTORY = ROOT / 'sentinel/analysis/api-extension/medusa-holdout-inventory.json'
LABELS = {'passed': '成功', 'partial_pass': '部分成功', 'blocked_prerequisite': '前置條件不足',
          'unavailable_feature': '版本／功能差異', 'failed_runtime': '實測失敗', 'not_run': '尚未測試'}


def normalize(path):
    return re.sub(r'\{[^}]+\}', '{}', path.replace('/auth/customer/', '/auth/{actor_type}/'))


def json_sha256(data):
    # 僅固定證據JSON的外層序列化，內嵌請求字串、空白、大小寫與編碼不改。
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def classify(operation, matches, native_present, environment=None):
    environment = environment or {}
    if not matches: return 'not_run', '沒有本次展示站證據'
    successful = [r for r in matches if 200 <= r.get('status', 0) < 300 and r.get('business_verified') and not r.get('route_probe_only') and not r.get('negative_control')]
    if successful:
        if operation['path'].endswith('/reset-password') and not any(r.get('reset_request_event_observed') for r in successful):
            if any(r.get('reset_request_token_persisted') for r in successful):
                return 'partial_pass', 'HTTP已唯讀證實產生並輪替原生reset Token、舊JWT失效；不存在帳號也回201但不產生Token。尚未獨立觀測該HTTP事件或郵件送達，仍保留部分成功'
            return 'partial_pass', '已有受理分支的業務斷言，但未取得Token持久化與事件的獨立觀測，不能當完整重設成功'
        if operation['path'].endswith('/promotions') and not any(r.get('promotion_effect_verified') for r in successful):
            return 'partial_pass', '合法空promo_codes分支已查回同一車與空促銷清單；沒有有效促銷碼，未驗證折扣套用／移除'
        return 'passed', '真實HTTP與業務斷言通過；只代表已覆蓋分支，不代表所有參數分支全通過'
    if operation['path'].endswith('/reset-password') and any(r.get('document_request_validated') and r.get('status') == 201 for r in matches):
        return 'partial_pass', '依手寫文件送已存在測試帳號identifier並回201；未取得token事件的獨立觀測證據，沒有把郵件投遞當成此API的必填參數'
    if not native_present and all(r.get('status') == 404 for r in matches):
        return 'unavailable_feature', '本機2.21.0安裝套件無對應方法／路由，HTTP探查也404；不是正常業務成功'
    if all(r.get('status') == 404 for r in matches) and not any(r.get('route_probe_only') for r in matches):
        if operation['path'] == '/store/locales' and environment.get('translation_module_disabled'):
            return 'unavailable_feature', '路由自2.12.3已存在；實際translation module disable=true，功能未啟用造成404，非版本缺少此路由'
        return 'unavailable_feature', '安裝套件有路由但展示站實際404，功能未掛載／啟用原因尚未定位，不能只歸因版本'
    if any(r.get('status', 0) >= 500 for r in matches):
        provider = environment.get('manual_fulfillment', {})
        option = environment.get('tested_shipping_option', {})
        if operation['path'] == '/store/shipping-options/{id}/calculate' and option.get('provider_id') == 'manual_manual' and provider.get('can_calculate_false') and provider.get('calculate_price_explicit_error'):
            return 'blocked_prerequisite', '文件必填cart_id與真實option ID已送；實際使用flat／manual_manual，原生canCalculate=false且calculatePrice明確拋錯。HTTP500保留，正向驗收需支援動態計價的提供者，不是缺data參數'
        return 'failed_runtime', '使用真實車與配送ID計價回500；目前manual提供者，根因仍待定位，不算通過'
    explanations = [r.get('precondition_limitation') or r.get('test_case_limitation') for r in matches]
    explanations = list(dict.fromkeys(x for x in explanations if x))
    if explanations: return 'blocked_prerequisite', '；'.join(explanations)
    return 'blocked_prerequisite', '已送HTTP但缺完整業務斷言或必要實例；不把HTTP受理／拒絕當成成功'


def audit(sync_inventory=False):
    inventory = json.loads(INVENTORY.read_text(encoding='utf-8'))
    before = {(o['method'], o['path']) for o in inventory['operations']}
    assert len(before) == 79
    route_path = REPORTS / 'medusa-2.21.0-demo-code-routes.json'
    native = json.loads(route_path.read_text(encoding='utf-8'))
    methods = {(m, normalize(o['path'])) for o in native for m in o['methods']}
    sources = ['medusa-demo-v9-flow.json', 'medusa-demo-v9-remaining.json', 'medusa-demo-v9-remaining-followups.json']
    for name in ['medusa-demo-v9-document-input-checks.json', 'medusa-demo-v9-native-token-transfers.json', 'medusa-demo-v9-reset-event-check.json', 'medusa-demo-v9-fixture-checks.json', 'medusa-demo-v9-verification-fixture-checks.json', 'medusa-demo-v9-reset-state-checks.json', 'medusa-demo-v9-payment-alternative.json']:
        if (REPORTS / name).is_file(): sources.append(name)
    environment_path = REPORTS / 'medusa-demo-v9-document-environment-proof.json'
    environment = json.loads(environment_path.read_text(encoding='utf-8')) if environment_path.is_file() else {}
    document_path = REPORTS / 'medusa-demo-v9-user-document-audit.json'
    document_reviews = {}
    if document_path.is_file():
        document_reviews = {(o['method'], o['path']): o for o in json.loads(document_path.read_text(encoding='utf-8'))['operations']}
    scores = {}
    score_files = ['medusa-demo-v9-gateway-scores.json', 'medusa-demo-v9-remaining-gateway-scores.json', 'medusa-demo-v9-followup-gateway-scores.json']
    for name in ['medusa-demo-v9-document-check-gateway-scores.json', 'medusa-demo-v9-reset-gateway-scores.json', 'medusa-demo-v9-fixture-gateway-scores.json', 'medusa-demo-v9-reset-state-gateway-scores.json', 'medusa-demo-v9-payment-alternative-gateway-scores.json']:
        if (REPORTS / name).is_file(): score_files.append(name)
    for name in score_files:
        for row in json.loads((REPORTS / name).read_text(encoding='utf-8'))['scores']: scores[row['request_id']] = row
    requests = []; predictions = []; checks = []; source_hashes = {}; latest = ''; targets = set()
    for name in sources:
        raw = (REPORTS / name).read_bytes(); data = json.loads(raw); source_hashes[name] = json_sha256(data)
        latest = max(latest, data['recorded_at']); checks.extend(data['checks'])
        targets.add(data.get('verification_target', 'http://127.0.0.1:18085'))
        for row in data['requests']:
            r = dict(row, runtime_evidence_file='sentinel/local-platforms/reports/' + name,
                     runtime_verification_target=data.get('verification_target', 'http://127.0.0.1:18085'))
            requests.append(r)
            score = scores.get(r['request_id'])
            if score is None: raise ValueError('HTTP沒有實際gateway分數，不能用離線重算補造')
            predictions.append({'source': name, 'request_id': r['request_id'], 'method': r['method'], 'api': r['operation_path'],
                'status': r['status'], 'role': 'negative_auth_control' if r.get('negative_control') else 'negative_route_probe' if r.get('route_probe_only') else 'normal_intent_or_precondition',
                'business_verified': r['business_verified'], 'label': score['label'], **{k + '_score': v for k, v in score['probabilities'].items()}})
    operations = []; table = []
    for old in inventory['operations']:
        key = old['method'], old['path']
        matching = [r for r in requests if (r['method'], r['operation_path']) == key]
        present = (old['method'], normalize(old['path'])) in methods
        status, reason = classify(old, matching, present, environment)
        op = dict(old, runtime_status=status, runtime_reason=reason, runtime_application_version='2.21.0',
                  runtime_http_attempted=bool(matching), runtime_http_statuses=sorted({r['status'] for r in matching}),
                  runtime_request_count=len(matching), runtime_business_verified=status == 'passed',
                  runtime_negative_probe_only=bool(matching) and all(r.get('route_probe_only') for r in matching),
                  runtime_in_installed_routes=present, runtime_checked_at=latest,
                  runtime_evidence_files=sorted({r['runtime_evidence_file'] for r in matching}),
                  runtime_request_ids=[r['request_id'] for r in matching],
                  runtime_coverage_limitations=sorted({r['coverage_limitation'] for r in matching if r.get('coverage_limitation')}))
        op['runtime_success_targets'] = sorted({r['runtime_verification_target'] for r in matching if r.get('business_verified') and 200 <= r.get('status', 0) < 300 and not r.get('route_probe_only') and not r.get('negative_control')})
        if old['path'].endswith('/reset-password') and (REPORTS / 'medusa-demo-v9-reset-state-proof.json').is_file():
            op['runtime_evidence_files'].append('sentinel/local-platforms/reports/medusa-demo-v9-reset-state-proof.json')
            op['runtime_evidence_files'].append('sentinel/local-platforms/reports/medusa-demo-v9-followup-source-proof.json')
        if old['path'] == '/auth/session' and status == 'passed':
            op['runtime_coverage_limitations'].append('成功範圍為真正HTTPS與自動Secure Cookie；原HTTP18085依然不能視為Cookie成功')
        if old['path'] in ('/store/locales', '/store/shipping-options/{id}/calculate') and environment:
            op['runtime_evidence_files'].append('sentinel/local-platforms/reports/' + environment_path.name)
        if old['path'] in ('/store/orders/{id}/transfer/accept', '/store/orders/{id}/transfer/decline') and status == 'passed':
            op['runtime_evidence_files'].append('sentinel/local-platforms/reports/medusa-demo-v9-native-token-provenance.json')
        if status == 'passed' and any('fixture-checks.json' in r['runtime_evidence_file'] for r in matching):
            op['runtime_evidence_files'].append('sentinel/local-platforms/reports/medusa-demo-v9-native-fixture-provenance.json')
        if key in document_reviews:
            review = document_reviews[key]
            op['runtime_user_document_reference'] = review['user_document']
            op['runtime_document_review_note'] = review['confirmed_explanation']
            op['runtime_evidence_files'].append('sentinel/local-platforms/reports/' + document_path.name)
        if op['path'] in ('/store/orders/{id}/transfer/request', '/store/orders/{id}/transfer/cancel'):
            state_path = REPORTS / 'medusa-demo-v9-transfer-state.json'
            state = json.loads(state_path.read_text(encoding='utf-8'))
            if state.get('read_only') and state.get('asserted_cancel_soft_deleted'):
                op['runtime_evidence_files'].append('sentinel/local-platforms/reports/' + state_path.name)
                op['runtime_backend_state_check'] = '自己的測試訂單transfer change存在，取消後依原生workflow實作soft-delete；未改資料庫'
        operations.append(op)
        table.append({'method': op['method'], 'api': op['path'], 'runtime_status': status, 'status': LABELS[status],
                      'http_attempted': bool(matching), 'business_verified': op['runtime_business_verified'],
                      'negative_probe_only': op['runtime_negative_probe_only'], 'request_count': len(matching),
                      'http_statuses': ','.join(map(str, op['runtime_http_statuses'])), 'reason': reason})
    assert {(o['method'], o['path']) for o in operations} == before
    counts = dict(Counter(o['runtime_status'] for o in operations))
    summary = {'target': 'http://127.0.0.1:18085', 'upstream': 'http://127.0.0.1:9100', 'application_version': '2.21.0',
               'verified_targets': sorted(targets),
               'model_sha256': hashlib.sha256((ROOT / 'sentinel/gateway/model/model.json').read_bytes()).hexdigest(),
               'checked_at': latest, 'operations': 79, 'http_attempted_operations': sum(o['runtime_http_attempted'] for o in operations),
               'not_run': counts.get('not_run', 0), 'status_counts': counts, 'http_requests': len(requests),
               'actual_gateway_prediction_matches': len(predictions), 'business_assertions_passed': sum(c['passed'] for c in checks),
               'business_assertions_failed': sum(not c['passed'] for c in checks), 'source_sha256': source_hashes,
               'source_sha256_format': 'parsed JSON sorted keys UTF-8; outer line endings only; raw request strings unchanged',
               'native_route_sha256': json_sha256(native),
               'document_environment_proof_sha256': json_sha256(environment) if environment else None,
               'scope': 'HTTP coverage includes explicit negative probes; not79 successful normal workflows; Medusa not training data'}
    result = {'runtime_verification': summary, 'operations': operations}
    (REPORTS / 'medusa-demo-v9-runtime-status.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary_path = REPORTS / 'medusa-demo-v9-summary.json'
    short = json.loads(summary_path.read_text(encoding='utf-8'))
    short.setdefault('initial_api_status_counts', short['api_status_counts'])
    short['api_status_counts'] = {LABELS[k]: v for k, v in counts.items()}
    short['runtime_verification'] = summary
    short['scope'] = 'latest79 runtime coverage below; original58-request normal flow and7 read-only probes retain separate counts'
    summary_path.write_text(json.dumps(short, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for path, rows in [(REPORTS / 'medusa-demo-v9-api-status.csv', table), (REPORTS / 'medusa-demo-v9-all-runtime-predictions.csv', predictions)]:
        with path.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    if sync_inventory:
        inventory['runtime_verification'] = summary; inventory['operations'] = operations
        INVENTORY.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sync-inventory', action='store_true')
    args = parser.parse_args(); audit(args.sync_inventory)
