"""逐筆在正常流程的對應階段執行 v2 候選；不重播舊 Token，不自動核准。"""
import argparse
import copy
import importlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.parse import parse_qs, quote, urlencode, urlsplit
import uuid

from core import ROOT, sample, sha, write_jsonl
from build_small_dataset import finalize
sys.path.insert(0, str(ROOT / 'sentinel/model'))
from real_requests import read_rows
from request_input import SENSITIVE
sys.path.insert(0, str(ROOT / 'sentinel/local-platforms'))
from http_evidence import EvidenceClient

LOCAL = ROOT / 'sentinel/local-platforms'
PORTS = {'bagisto': 18081, 'shopware': 18082, 'sylius': 18083}
DYNAMIC = re.compile(r'(^id$|^ids$|Id$|_id$|^email$|^username$|password|token|secret|session)', re.I)


class Captured(Exception):
    """中止該次正常流程，避免目標操作執行後再繼續消耗購物車狀態。"""


def bind_body(planned, live, target=None, prefix=''):
    """只從當次正常請求取得動態值；找不到就拒絕，不猜測有效 ID。

    攻擊目標欄位保留候選值，其餘動態欄位重新綁定。這不會替複合商品
    建立種子；缺種子情境應記錄 blocked，不能當成已執行樣本。
    """
    if isinstance(planned, dict):
        result = {}
        for name, value in planned.items():
            path = prefix + '.' + name if prefix else name
            available = live.get(name) if isinstance(live, dict) else None
            if path == target:
                result[name] = value
            elif DYNAMIC.search(name) or (name == 'value' and DYNAMIC.search(str(planned.get('field', '')))):
                if available is None:
                    raise ValueError('缺少當次動態欄位：' + path)
                result[name] = available
            else:
                result[name] = bind_body(value, available, target, path)
        return result
    if isinstance(planned, list):
        return [bind_body(v, live[i] if isinstance(live, list) and i < len(live) else None,
                          target, prefix + '[]') for i, v in enumerate(planned)]
    if planned == '[REDACTED]':
        if live is None:
            raise ValueError('缺少當次憑證')
        return live
    return planned


class StageClient(EvidenceClient):
    def __init__(self, platform, output, config, candidate):
        base = { 'bagisto': '/api/shop', 'shopware': '/store-api', 'sylius': '' }[platform]
        headers = {'bagisto': {'X-STOREFRONT-KEY': config.get('storefront_key'),
                              'X-Locale': config.get('locale'), 'X-Channel': config.get('channel'),
                              'X-Currency': config.get('currency')},
                   'shopware': {'sw-access-key': config.get('access_key')},
                   'sylius': {'Accept': 'application/ld+json'}}[platform]
        super().__init__(platform, f'http://127.0.0.1:{PORTS[platform]}' + base, output, headers)
        self.config = config
        self.candidate = candidate
        self.captured_row = None
        self.last_request_at = 0

    def request(self, method, path, body=None, template=None, content_type='application/json', allowed_status=None):
        # 此測試 key 每分鐘最多 100 次；每個 HTTP 都限速，不只限候選迴圈。
        wait = 0.8 - (time.monotonic() - self.last_request_at)
        if wait > 0:
            time.sleep(wait)
        self.last_request_at = time.monotonic()
        meta, planned = self.candidate['metadata'], self.candidate['input']
        operation = (method, template or urlsplit(path).path)
        if operation != (planned['method'], meta['operation_path']):
            return super().request(method, path, body, template, content_type, allowed_status)
        target = meta.get('target_parameter')
        location = meta.get('target_location')
        # 商品型別種子仍待建立的資料不能透過重播假裝有效。
        if meta['operation_path'] == '/add-product-in-cart' and any(
                k in (planned.get('body') or {}) for k in ['superAttribute', 'bundleOptions', 'booking']):
            raise ValueError('複合商品候選需要對應商品種子，尚未綁定')
        live_body = copy.deepcopy(body)
        # Shopware 清單的正常基底只有 limit；filter.id 必須取當次剛建立的地址。
        # 不能沿用 CSV 的舊 UUID，也不能拿另一種實體的 id 湊值。
        if self.platform == 'shopware' and meta['operation_path'] == '/account/list-address':
            address = next((r for r in reversed(self.rows) if r['operation_path'] == '/account/address'
                            and isinstance(r.get('response_body'), dict) and r['response_body'].get('id')), None)
            if address:
                identifier = address['response_body']['id']
                live_body = {**(live_body or {}),
                             'filter': [{'field': 'id', 'value': identifier}],
                             'post-filter': [{'field': 'id', 'value': identifier}], 'ids': [identifier]}
        effective_body = bind_body(planned.get('body'), live_body, target if location == 'body' else None)
        query = copy.deepcopy(planned.get('query', {}))
        live_query = parse_qs(urlsplit(path).query, keep_blank_values=True)
        if self.platform == 'bagisto' and self.config.get('category_id') is not None:
            live_query['category_id'] = self.config['category_id']
        query = bind_body(query, live_query, target if location == 'query' else None)
        effective_path = urlsplit(path).path
        if location == 'path':
            names = re.findall(r'\{([^}]+)\}', meta['operation_path'])
            pattern = '^' + re.sub(r'\\\{[^}]+\\\}', '([^/]+)', re.escape(meta['operation_path'])) + '$'
            match = re.match(pattern, effective_path)
            if not match or target not in names:
                raise ValueError('無法對應當次 path 參數')
            values = dict(zip(names, match.groups()))
            values[target] = quote(str(planned.get('path_parameters', {}).get(target, '')), safe='')
            effective_path = re.sub(r'\{([^}]+)\}', lambda m: values[m[1]], meta['operation_path'])
        if query:
            wire = {'path_parameters': {}, 'query': query, 'body': effective_body}
            finalize(wire, effective_path)
            effective_path += '?' + wire['raw_query']
        # 這次候選的 header 覆蓋當次 client；憑證從當次 client 取得，不寫入候選。
        if self.platform == 'shopware' and any(k.lower() == 'sw-context-token' and v == '[REDACTED]'
                for k, v in planned.get('headers', {}).items()) and not self.headers.get('sw-context-token'):
            # 首次 /context 之前沒有 token；先走一次真正的建立情境請求。
            super().request('GET', '/context')
        if self.platform == 'shopware' and any(k.lower() == 'sw-language-id' for k in planned.get('headers', {})):
            context = next((r.get('response_body') for r in self.rows if r['operation_path'] == '/context'
                            and isinstance(r.get('response_body'), dict)), None)
            if context is None:
                context = super().request('GET', '/context')
        else:
            context = None
        actual = {k.lower(): v for k, v in self.headers.items()}
        # 文件表未逐項重列的認證仍屬當次流程必要條件，保留有效憑證。
        headers = {name: value for name, value in self.headers.items() if SENSITIVE.search(name)}
        for name, value in planned.get('headers', {}).items():
            if name.lower() == 'sw-language-id' and context and not (location == 'header' and str(target).lower() == 'sw-language-id'):
                chain = context.get('context', {}).get('languageIdChain', [])
                if not chain:
                    raise ValueError('缺少當次有效語言 ID')
                value = chain[0]
            if value == '[REDACTED]':
                if name.lower() == 'cookie' and name.lower() not in actual:
                    continue  # 只交給 CookieJar 送當次真實 cookie，不捏造舊 Cookie。
                if name.lower() not in actual:
                    raise ValueError('缺少當次 header 憑證：' + name)
                value = actual[name.lower()]
            headers[name] = value
        self.headers = headers
        super().request(method, effective_path, effective_body, meta['operation_path'], content_type,
                        set(range(200, 600)))
        self.captured_row = self.rows[-1]
        raise Captured()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--platform', choices=PORTS, required=True)
    parser.add_argument('--split', choices=['train', 'test', 'validation'], required=True)
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).parent / 'small-api-v2')
    parser.add_argument('--limit', type=int, default=0, help='0 表示全部；先以 1 筆確認流程')
    parser.add_argument('--path', help='只測指定 API 路由模板，供小批次修正前置條件')
    parser.add_argument('--label', choices=['normal', 'sqli', 'xss'], help='小批次檢查指定類別')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.execute:
        parser.error('實機操作必須指定 --execute')
    name = 'msdss-phase1-' + args.platform
    running = subprocess.check_output(['docker', 'ps', '--format', '{{.Label "com.docker.compose.project"}}'], text=True)
    if any(p.startswith('msdss-phase1-') and p != name for p in running.splitlines()):
        raise SystemExit('只允許單平台執行；未停止其他平台')
    port = PORTS[args.platform]
    app = subprocess.check_output(['docker', 'compose', '-f', str(LOCAL / args.platform / 'compose.yaml'),
                                   'ps', '-q', 'shopware' if args.platform == 'shopware' else 'app'], text=True).strip()
    if not app:
        raise SystemExit('獨立測試平台尚未啟動')
    info = json.loads(subprocess.check_output(['docker', 'inspect', app]))[0]
    bindings = [b for values in info['NetworkSettings']['Ports'].values() if values for b in values]
    if (info['Config']['Labels'].get('com.docker.compose.project') != name or
            not bindings or any(b['HostIp'] != '127.0.0.1' for b in bindings) or
            not any(b['HostPort'] == str(port) for b in bindings)):
        raise SystemExit('不是預期的隔離容器或 loopback 埠')
    config = json.loads((LOCAL / '.runtime' / (args.platform + '.json')).read_text(encoding='utf-8-sig'))
    planned = [r for r in read_rows(args.data_dir / (args.split + '.csv')) if r['metadata']['platform'] == args.platform]
    if args.path:
        planned = [r for r in planned if r['metadata']['operation_path'] == args.path]
    if args.label:
        planned = [r for r in planned if r['annotation']['proposed_label'] == args.label]
    if args.limit:
        planned = planned[:args.limit]
    run = args.platform + '-' + uuid.uuid4().hex
    folder = ROOT / 'sentinel/dataset/live-small-api-v2' / run
    folder.mkdir(parents=True)
    records, outcomes = [], []
    workflow = importlib.import_module('run_' + args.platform)
    for index, candidate in enumerate(planned):
        evidence = ROOT / 'sentinel/dataset/evidence' / f'{run}-{index}.json'
        client = StageClient(args.platform, evidence, config, candidate)
        outcome = {'planned_sample_id': candidate['sample_id'], 'http_executed': False}
        try:
            workflow.run(client) if args.platform == 'bagisto' else workflow.run(client, config)
            outcome['reason'] = '正常流程未走到此操作，需補充對應工作流程'
        except Captured:
            client.save('candidate_http_captured')
            status = client.captured_row['status']
            label = candidate['annotation']['proposed_label']
            eligible = 200 <= status < 300 if label == 'normal' else status not in (401, 403, 429) and status < 500
            row = sample(args.platform, evidence.relative_to(ROOT).as_posix(), client.redact(client.captured_row),
                         run + '-' + str(index), candidate['annotation']['proposed_label'],
                         kind='small_api_v2_live', eligibility=eligible,
                         versions={'image_id': info['Image'], 'fixed_source': json.loads((LOCAL / 'versions.json').read_text())[args.platform]},
                         reason='候選意圖與實際 HTTP；尚未人工審核或證實業務／攻擊成功')
            row['metadata'].update(split=args.split, source_evidence_sha256=sha(evidence.read_bytes()),
                                   planned_sample_id=candidate['sample_id'], http_executed=True,
                                   pair_group=candidate['metadata'].get('pair_group'),
                                   family_id=(candidate['metadata'].get('payload') or {}).get('family'),
                                   historical_source_report=candidate['metadata'].get('historical_source_report'),
                                   payload=copy.deepcopy(candidate['metadata'].get('payload')),
                                   target_location=candidate['metadata'].get('target_location'),
                                   target_parameter=candidate['metadata'].get('target_parameter'),
                                   binding_policy='fresh_workflow_ids_and_credentials; missing_bindings_blocked')
            records.append(row)
            outcome.update(http_executed=True, http_status=client.captured_row['status'])
            if client.captured_row['status'] in (401, 403, 429) or client.captured_row['status'] >= 500:
                outcome['stop_platform'] = True
        except (ValueError, RuntimeError, KeyError, TypeError) as error:
            # 原始錯誤可能含資料值；只保存固定摘要，詳細請求在遮蔽證據中。
            client.save('candidate_blocked', '動態綁定／種子／正常前置流程未通過；不得當成成功')
            safe = str(error) if isinstance(error, ValueError) and str(error).startswith(
                ('缺少當次', '複合商品', '無法對應')) else '正常前置流程未通過'
            outcome['reason'] = safe
            if client.rows and client.rows[-1].get('status') in (401, 403, 429):
                outcome['stop_platform'] = True
        outcomes.append(outcome)
        write_jsonl(folder / 'candidates.jsonl', records)
        (folder / 'outcomes.json').write_text(json.dumps(outcomes, ensure_ascii=False, indent=2))
        print(json.dumps(outcome, ensure_ascii=False), flush=True)
        if outcome.get('stop_platform'):
            break
        time.sleep(0.8)
    print('證據與執行結果：', folder)
    return 0 if outcomes and all(r['http_executed'] and not r.get('stop_platform') for r in outcomes) else 2


if __name__ == '__main__':
    raise SystemExit(main())
