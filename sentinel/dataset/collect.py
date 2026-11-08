"""Sequential real HTTP pilot, only against the three isolated Compose projects.

No HTTP mocks; failures stay in evidence/quarantine. Requires >=4 GiB disk,
the existing resource check and an already-started dedicated local platform.
"""
import argparse
import collections
import copy
import importlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.parse
import uuid

from core import ROOT, manifest, sample, sha, write_jsonl
from scenarios import cases

HERE = Path(__file__).resolve().parent
LOCAL = ROOT / 'sentinel/local-platforms'
sys.path.insert(0, str(LOCAL))
from http_evidence import EvidenceClient

PORTS = {'bagisto': 18081, 'shopware': 18082, 'sylius': 18083}
ADDRESS = {'bagisto': '/customer-addresses', 'shopware': '/account/address', 'sylius': '/api/v2/shop/addresses'}


class PilotEvidenceClient(EvidenceClient):
    """Exclude evidence-file writes from client request timing; still not a DB timing oracle."""
    saved_seconds = 0.0
    last_http_ms = None

    def save(self, *args, **kwargs):
        start = time.perf_counter()
        try:
            return super().save(*args, **kwargs)
        finally:
            self.saved_seconds += time.perf_counter() - start

    def request(self, *args, **kwargs):
        start, saved = time.perf_counter(), self.saved_seconds
        try:
            return super().request(*args, **kwargs)
        finally:
            self.last_http_ms = round(max(0, time.perf_counter() - start - (self.saved_seconds - saved)) * 1000, 3)


def preflight(platform, run):
    if shutil.disk_usage(ROOT).free < 4 * 1024**3:
        raise RuntimeError('C 槽不足 4 GiB，未發送請求')
    contracts = subprocess.run([sys.executable, str(ROOT / 'sentinel/scripts/active_api_contracts.py')],
        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
    if contracts.returncode:
        raise RuntimeError('採用契約、來源 SHA 或認證結構檢查未通過；未發送請求')
    shell = shutil.which('pwsh')
    if not shell:
        raise RuntimeError('需要 PowerShell 7 執行既有資源檢查')
    result = subprocess.run([shell, '-NoProfile', '-File', str(LOCAL / 'preflight.ps1'),
        '-MinimumDiskGiB', '4', '-OutputPath', str(HERE / 'reports' / (run + '-preflight.json'))],
        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
    if result.returncode:
        raise RuntimeError('既有資源檢查未通過；沒有啟動服務或發送平台請求')
    container = f'msdss-phase1-{platform}-app-1'
    result = subprocess.run(['docker', 'inspect', container], capture_output=True, text=True, timeout=20)
    if result.returncode:
        raise RuntimeError('本次獨立平台尚未啟動')
    data = json.loads(result.stdout)[0]
    if not data['State']['Running'] or data['Config']['Labels'].get('com.docker.compose.project') != 'msdss-phase1-' + platform:
        raise RuntimeError('不是本次獨立平台')
    bindings = [b for values in data['NetworkSettings']['Ports'].values() if values for b in values]
    if not bindings or any(b['HostIp'] != '127.0.0.1' for b in bindings) or not any(b['HostPort'] == str(PORTS[platform]) for b in bindings):
        raise RuntimeError('平台埠號或本機綁定不符')
    other = subprocess.run(['docker', 'ps', '--format', '{{.Label "com.docker.compose.project"}}'], capture_output=True, text=True, timeout=20)
    if other.returncode or any(p.startswith('msdss-phase1-') and p != 'msdss-phase1-' + platform for p in other.stdout.splitlines()):
        raise RuntimeError('只允許逐個本次平台採集')
    fixed = json.loads((LOCAL / 'versions.json').read_text(encoding='utf-8'))
    return {'image_id': data['Image'], 'container': container, 'local_port': PORTS[platform],
            'fixed_source_record': fixed[platform], 'versions_record_sha256': sha((LOCAL / 'versions.json').read_bytes())}


def client(platform, path, config):
    if platform == 'bagisto':
        return PilotEvidenceClient(platform, 'http://127.0.0.1:18081/api/shop', path,
            {'X-STOREFRONT-KEY': config['storefront_key'], 'X-Locale': config['locale'],
             'X-Channel': config['channel'], 'X-Currency': config['currency']})
    if platform == 'shopware':
        return PilotEvidenceClient(platform, 'http://127.0.0.1:18082/store-api', path, {'sw-access-key': config['access_key']})
    return PilotEvidenceClient(platform, 'http://127.0.0.1:18083', path, {'Accept': 'application/ld+json'})


def values(platform, payload):
    if platform == 'shopware':
        return payload.get('elements', []) if isinstance(payload, dict) else []
    if platform == 'sylius' and isinstance(payload, dict):
        return payload.get('hydra:member', payload.get('member', []))
    return payload if isinstance(payload, list) else []


def valid_search_response(platform, payload):
    if platform == 'bagisto':
        items = payload if isinstance(payload, list) else None
        key = 'id'
    elif platform == 'shopware':
        items = payload.get('elements') if isinstance(payload, dict) else None
        key = 'id'
    else:
        items = payload if isinstance(payload, list) else payload.get('hydra:member', payload.get('member')) if isinstance(payload, dict) else None
        key = 'code'
    return isinstance(items, list) and all(isinstance(p, dict) and p.get(key) is not None for p in items)


def search(c, platform, text):
    if platform == 'bagisto':
        return c.request('GET', '/products?' + urllib.parse.urlencode({'query': text, 'per_page': 50}), template='/products', allowed_status=set(range(200, 600)))
    if platform == 'shopware':
        return c.request('POST', '/search', {'search': text, 'limit': 50}, allowed_status=set(range(200, 600)))
    return c.request('GET', '/api/v2/shop/products?' + urllib.parse.urlencode({'translations.name': text, 'itemsPerPage': 30}),
        template='/api/v2/shop/products', allowed_status=set(range(200, 600)))


def search_gate(c, platform):
    """Positive and impossible normal query must show that the target actually filters."""
    product_rows = [r for r in c.rows if r['method'] == 'GET' and r['operation_path'] in ('/products', '/api/v2/shop/products')]
    if platform == 'shopware':
        product_rows = [r for r in c.rows if r['method'] == 'POST' and r['operation_path'] == '/product']
    products = values(platform, product_rows[0]['response_body']) if product_rows else []
    if not products:
        return False
    product = products[0]
    term = product.get('name') or product.get('translation', {}).get('name')
    if not term and platform == 'sylius':
        detail_rows = [r for r in c.rows if r['operation_path'] == '/api/v2/shop/products/{code}']
        detail = detail_rows[0]['response_body'] if detail_rows else {}
        term = detail.get('name') or detail.get('translation', {}).get('name')
    if not term:
        return False
    yes_payload = search(c, platform, term)
    yes = values(platform, yes_payload)
    yes_status = c.rows[-1]['status']
    no_payload = search(c, platform, 'zz' + uuid.uuid4().hex)
    no = values(platform, no_payload)
    no_status = c.rows[-1]['status']
    identity = product.get('id', product.get('code'))
    return yes_status == no_status == 200 and valid_search_response(platform, yes_payload) and valid_search_response(platform, no_payload) and any(p.get('id', p.get('code')) == identity for p in yes) and not no


def restore_login(c, platform):
    path = {'bagisto': '/customer/login', 'shopware': '/account/login', 'sylius': '/api/v2/shop/customers/token'}[platform]
    original = next(r for r in c.rows if r['operation_path'] == path)
    auth = c.request('POST', path, copy.deepcopy(original['request_body']))
    if platform != 'shopware':
        if not auth.get('token'):
            raise RuntimeError('重新登入未取得有效認證')
        c.headers['Authorization'] = 'Bearer ' + auth['token']
    if platform == 'bagisto':
        profile = c.request('GET', '/customer-profile')
        if not any(p.get('email') == original['request_body']['email'] for p in profile):
            raise RuntimeError('重新登入後身分不符')
    elif platform == 'shopware':
        profile = c.request('POST', '/account/customer', {})
        if profile.get('email') != original['request_body']['username']:
            raise RuntimeError('重新登入後身分不符')


def address_check(c, platform, response, expected):
    if platform == 'bagisto':
        aid = response.get('id') or response.get('addressId')
        return bool(aid) and any(str(a.get('id')) == str(aid) and a.get('firstName') == expected
            for a in values(platform, c.request('GET', '/customer-addresses?per_page=100', template='/customer-addresses')))
    if platform == 'shopware':
        aid = response.get('id')
        result = c.request('POST', '/account/list-address', {'limit': 100, 'filter': [{'type': 'equals', 'field': 'id', 'value': aid}]})
        return bool(aid) and any(a.get('id') == aid and a.get('firstName') == expected for a in values(platform, result))
    iri = response.get('@id')
    if not isinstance(iri, str) or not iri.startswith('/api/v2/shop/addresses/'):
        return False
    readback = c.request('GET', iri, template='/api/v2/shop/addresses/{id}')
    return readback.get('firstName') == expected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', choices=PORTS, required=True)
    parser.add_argument('--execute', action='store_true', help='明確啟用本機實機採集')
    args = parser.parse_args()
    if not args.execute:
        parser.error('必須指定 --execute；單純建立情境請執行 scenarios.py')
    platform = args.platform
    run = platform + '-' + uuid.uuid4().hex
    output = HERE / 'pilot' / (run + '.jsonl')
    status_path = HERE / 'reports' / (run + '.json')
    status_path.parent.mkdir(parents=True, exist_ok=True)
    samples, controls, target_gates, skipped, workflow_observations = [], {}, [], [], []
    c = None
    outcome, error = 'blocked', None
    try:
        environment = preflight(platform, run)
        config = json.loads((LOCAL / '.runtime' / (platform + '.json')).read_text(encoding='utf-8-sig'))
        baseline = importlib.import_module('run_' + platform)
        selected = {(o['method'], o['path']) for o in manifest()['operations'] if o['platform'] == platform}
        plan = cases(platform)
        active_plan = []
        for case in plan:
            if not case.get('can_collect_http') or not case.get('http_visible') or not isinstance(case.get('value'), str):
                skipped.append({'case_id':case['case_id'],'base_case_id':case.get('base_case_id'),
                    'reason':'需要額外工作流程、瀏覽器／接收器或參數語境驗證','prerequisites':case.get('prerequisites',[])})
            else:
                active_plan.append(case)
        plan = active_plan
        workflow_count = 0
        cohort_count = math.ceil((max(int(case['pair_group'].rsplit('-',1)[1]) for case in plan)+1)/25)
        for cohort in range(cohort_count):
            batch = run + f'-session-{cohort}'
            source = HERE / 'evidence' / (batch + '.json')
            c = client(platform, source, config)
            if platform == 'bagisto':
                baseline.run(c)
            else:
                baseline.run(c, config)
            # 保留完整已驗證正常流程，不再用任意 30 筆上限漏掉 API／參數。
            for row in c.rows:
                if row.get('business_verified') and 200 <= row.get('status', 0) < 300 and (row['method'], row['operation_path']) in selected:
                    samples.append(sample(platform, source.relative_to(ROOT).as_posix(), c.redact(row), batch,
                        kind='pilot_live', reason='當次完整正常購物流程與業務斷言', versions=environment))
                    workflow_count += 1
            restore_login(c, platform)
            prototype = next(copy.deepcopy(r['request_body']) for r in c.rows if r['method'] == 'POST' and r['operation_path'] == ADDRESS[platform])
            enabled = search_gate(c, platform)
            target_gates.append({'session': batch, 'search_effect_verified': enabled,
                'unavailable_action': None if enabled else 'skip search：不改投地址，避免偷換反射／儲存或語法情境'})
            consecutive_5xx = 0
            for case in plan:
                ordinal = int(case['pair_group'].rsplit('-', 1)[1])
                if ordinal // 25 != cohort:
                    continue
                if shutil.disk_usage(ROOT).free < 4 * 1024**3:
                    raise RuntimeError('採集中磁碟低於 4 GiB，已停止')
                target = case['target']
                if target == 'search' and not enabled:
                    skipped.append({'case_id':case['case_id'],'base_case_id':case.get('base_case_id'),
                        'reason':'正常搜尋正負對照未證實參數有效；不改投不同情境'})
                    continue
                time.sleep(0.25)
                expected_rejection = case.get('normal_kind') == 'missing_required_value'
                positive_id = None
                if expected_rejection:
                    positive = c.request('POST', ADDRESS[platform], {**prototype, 'firstName': 'Alice'})
                    positive_row = len(c.rows) - 1
                    if not address_check(c, platform, positive, 'Alice'):
                        raise RuntimeError('非攻擊缺值測試的正常對照未通過')
                    c.verify(True, '非攻擊缺值情境的正常地址對照已讀回', positive_row)
                    positive_id = c.rows[positive_row]['request_id']
                if target == 'search':
                    response = search(c, platform, case['value'])
                else:
                    body = {**prototype, 'firstName': case['value']}
                    if platform == 'bagisto':
                        body['defaultAddress'] = False
                    response = c.request('POST', ADDRESS[platform], body, allowed_status=set(range(200, 600)))
                elapsed_ms = c.last_http_ms
                index = len(c.rows) - 1
                row = c.rows[index]
                http = row['status']
                if case.get('workflow_id'):
                    workflow_observations.append({'workflow_id':case['workflow_id'],'stage':case.get('workflow_stage'),
                        'role':case.get('role'),'request_id':row['request_id'],'http_status':http,'elapsed_ms':elapsed_ms,
                        'payload_sent':case['value'],'paired_success_verified':False,
                        'note':'僅 HTTP／解析時間，扣除證據寫檔；不是 SQL 執行或盲注成功證明'})
                normal = case['proposed_label'] == 'normal'
                verified = False
                if normal and expected_rejection:
                    verified = bool(positive_id) and http in (400, 422) and isinstance(response, dict)
                    if verified:
                        c.verify(True, '有效地址對照成功後，空白必填姓名受到預期驗證拒絕；屬非攻擊錯誤', index)
                        controls[case['pair_group']] = positive_id
                elif normal and 200 <= http < 300:
                    if target == 'address':
                        verified = isinstance(response, dict) and address_check(c, platform, response, case['value'])
                    else:
                        verified = valid_search_response(platform, response)
                    if verified:
                        c.verify(True, '正常目標請求：地址重新讀回，或已通過正負控制的搜尋回應', index)
                        controls[case['pair_group']] = row['request_id']
                eligible = verified if normal else bool(controls.get(case['pair_group'])) and (200 <= http < 300 or http in (400, 409, 422))
                item = sample(platform, source.relative_to(ROOT).as_posix(), c.redact(row), batch,
                    case['proposed_label'], case['family_id'], run + '-' + case['pair_group'],
                    kind='pilot_live', eligibility=eligible, versions=environment,
                    reason='已知候選模板與同位置正常控制；尚待人工審核，不由 HTTP 狀態推導類別' if not normal else '正常文字與實機目標效果核對')
                item['metadata'].update({'case_id': case['case_id'], 'effective_target': target,
                    'normal_kind': case.get('normal_kind'),
                    'matched_control_request_id': controls.get(case['pair_group']), 'source_template_version': 2,
                    'base_case_id':case.get('base_case_id'),'coverage_tags':case.get('coverage_tags'),
                    'input_context':case.get('input_context'),'lifecycle':case.get('lifecycle'),
                    'context_success_verified':False,'evaluation_role':'coverage_development_only'})
                item['metadata'].update({'workflow_id':case.get('workflow_id'),'workflow_stage':case.get('workflow_stage'),
                    'elapsed_ms_audit_only':elapsed_ms,'workflow_success_verified':False})
                samples.append(item)
                write_jsonl(output, samples)
                consecutive_5xx = consecutive_5xx + 1 if http >= 500 else 0
                if http in (401, 403, 429) or consecutive_5xx >= 3 or (normal and not verified):
                    raise RuntimeError('登入／限流／健康狀態或正常控制異常；保留證據並停止，不湊滿樣本')
            c.save('pilot_cohort_completed')
        outcome = 'pilot_collected_pending_review'
    except (RuntimeError, OSError, ValueError, KeyError, TypeError, StopIteration, subprocess.SubprocessError) as failure:
        error = str(failure) if isinstance(failure, RuntimeError) else '前置條件或實機斷言未通過；詳見本次資源與已遮蔽 HTTP 證據。沒有補造未送出的樣本。'
        if c is not None:
            c.save('pilot_stopped', error)
    for item in samples:
        evidence = ROOT / item['metadata']['source_evidence']
        if evidence.is_file():
            item['metadata']['source_evidence_sha256'] = sha(evidence.read_bytes())
    write_jsonl(output, samples)
    report = {'run_id': run, 'platform': platform, 'outcome': outcome, 'error': error,
        'sample_count': len(samples), 'proposed_class_counts': dict(collections.Counter(s['annotation']['proposed_label'] for s in samples)),
        'eligible_for_review': sum(s['annotation']['eligible_for_review'] for s in samples),
        'human_approved_training_samples': 0, 'target_gates': target_gates,
        'skipped_cases':skipped,
        'workflow_observations':workflow_observations,
        'manifest_sha256': sha((ROOT / 'sentinel/analysis/api-extension/active-api-manifest.json').read_bytes()),
        'collector_sha256': sha(Path(__file__).read_bytes()), 'scenario_source_sha256': sha((HERE / 'scenarios.py').read_bytes()),
        'code_sha256': {p.name: sha(p.read_bytes()) for p in
            [HERE / 'collect.py', HERE / 'core.py', HERE / 'scenarios.py', HERE / 'catalog_v2.py', LOCAL / 'http_evidence.py', LOCAL / ('run_' + platform + '.py')]},
        'training_started': False, 'medusa_used': False}
    status_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if outcome == 'pilot_collected_pending_review' else 2


if __name__ == '__main__':
    raise SystemExit(main())
