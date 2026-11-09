"""逐項對照原手寫77 API文件，復核此前非成功32項；不修改原文件。"""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import urllib.parse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
REPORTS = HERE / 'reports'
BASELINE = '6c2454f'
SNAPSHOT = ROOT / 'sentinel/analysis/history/2026-11-09/medusa-77-user-reference.md'


def parse_document(text):
    result = {}
    starts = list(re.finditer(r'^## .+$', text, re.M))
    for i, start in enumerate(starts):
        block = text[start.start():starts[i + 1].start() if i + 1 < len(starts) else len(text)]
        operation = re.search(r'`(GET|POST|DELETE|PATCH|PUT)\s+([^`\s]+)`', block)
        if not operation: continue
        parameters = []
        for line in block.splitlines():
            if not line.startswith('|'): continue
            cells = [x.strip() for x in line.strip('|').split('|')]
            if len(cells) >= 3 and '：' in cells[0]:
                location, name = cells[0].split('：', 1)
                if location in ('Header', 'Body', 'Path', 'Query', 'Cookie'):
                    parameters.append({'location': location, 'name': name, 'requirement': cells[1], 'meaning': cells[2]})
        result[operation[1], operation[2]] = {'heading': start.group().removeprefix('## '),
            'line': text[:start.start()].count('\n') + 1, 'parameters': parameters}
    return result


def present(row, parameter):
    loc = parameter['location']; name = parameter['name']
    if loc == 'Header': return name.lower() in {x.lower() for x in row.get('request_headers', {})}
    if loc == 'Cookie': return 'cookie' in {x.lower() for x in row.get('request_headers', {})}
    if loc == 'Query': return name in urllib.parse.parse_qs(row.get('raw_query', ''), keep_blank_values=True)
    if loc == 'Path': return '{' + name + '}' in row['operation_path']
    value = row.get('request_body')
    for part in name.split('.'):
        key = part.removesuffix('[]')
        if not isinstance(value, dict) or key not in value: return False
        value = value[key]
        if part.endswith('[]'):
            if not isinstance(value, list) or not value: return name.endswith('[]')
            value = value[0]
    return True


def explanation(path, env):
    if path == '/auth/session': return '手寫文件的JWT／connect.sid用法正確；HTTP不符production Secure Cookie。真正HTTPS、驗證憑證、CookieJar自動維持與刪除身分均已補測成功。'
    if path.endswith('/callback'): return '文件用途是第三方回呼；auth_provider欄位例emailpass不能當作該provider支援callback。現只配置emailpass，原生回應明確未實作callback。'
    if path.endswith('/reset-password'): return '文件此操作是要求產生token並發事件，不是寄信本身。已依identifier呼叫201；因回應故意不透露帳號是否存在、尚無事件獨立證據，列部分成功，不能說缺郵件就是參數錯。'
    if path.endswith('/update'): return '文件明確要求重設密碼token。上次僅password且用了普通登入JWT；本次補email＋password仍401。缺合法reset token是關鍵，不把登入JWT冒充重設JWT。'
    if path.startswith('/auth/mfa/'): return '依文件註冊先送provider=totp、已登入。原生400與安全設定均確認缺MFA encryption key，故無真實factor／challenge／recovery code。後續未填code的紀錄只是負向探查。'
    if path == '/auth/verification/confirm': return '文件必填code，實際沒有通知接收途徑取得原生code；先前省略code的400不是正向驗收。現只有feed通知、src/subscribers空，未配置email發送／取碼。'
    if path.endswith('/promotions'): return '文件用途是套用／移除優惠碼，空陣列只覆蓋清除分支。唯讀DB promotion=0，不能把任意字串當成真優惠碼；兩項保留部分成功。'
    if path in ('/store/collections/{id}', '/store/product-tags/{id}', '/store/product-types/{id}', '/store/return-reasons/{id}'):
        return '文件要求既有資源ID，唯讀資料庫對應表皆0筆；未發行ID只是負向探查。return-reasons甚至200空物件，不能當成功。'
    if path == '/store/locales': return '不是缺路由：原生標示自2.12.3存在、以translation feature flag控制；實際translation module disable=true。屬目前功能設定，不是必須升級或補locale參數。'
    if '/transfer/' in path: return '依文件送本次真實訂單ID與平台產生的token後已成功，接受／拒絕後查雙方訂單歸屬及confirmed／declined狀態。token唯讀取自己訂單資料列，沒有偽造；郵件送達未驗證。'
    if path == '/store/returns': return '文件必填order_id、items.id／quantity、return_shipping.option_id有送；實例fulfilled_quantity=0且沒有可用退貨配送選項。原生400證明業務前置不足，不是任填品項ID可解決。'
    if path.endswith('/calculate'): return '文件cart_id必填、data選填，先前已有真實cart／option ID。實際provider=manual_manual、price_type=flat；原生canCalculate=false且calculatePrice明確拋錯。500保留，改列需支援動態計價provider的前置不足。'
    return '文件列有不等於本機已實作。已比對原生2.21.0路由及HTTP404；缺必填值的探查不當正常成功，也未假造已發行禮卡／儲值碼。'


def main():
    old = json.loads(subprocess.check_output(['git', 'show', BASELINE + ':sentinel/analysis/api-extension/medusa-holdout-inventory.json'], cwd=ROOT))
    targets = [o for o in old['operations'] if o['runtime_status'] != 'passed']
    assert len(targets) == 32
    current = json.loads((REPORTS / 'medusa-demo-v9-runtime-status.json').read_text(encoding='utf-8'))
    now = {(o['method'], o['path']): o for o in current['operations']}
    docs = parse_document(SNAPSHOT.read_text(encoding='utf-8'))
    env = json.loads((REPORTS / 'medusa-demo-v9-document-environment-proof.json').read_text(encoding='utf-8'))
    requests = []
    for name in current['runtime_verification']['source_sha256']:
        for r in json.loads((REPORTS / name).read_text(encoding='utf-8'))['requests']:
            requests.append(dict(r, evidence_file='sentinel/local-platforms/reports/' + name))
    operations = []; table = []
    for before in targets:
        key = before['method'], before['path']; op = now[key]; doc = docs.get(key)
        matches = [r for r in requests if (r['method'], r['operation_path']) == key]
        positive = [r for r in matches if r.get('business_verified') and 200 <= r['status'] < 300 and not r.get('route_probe_only')]
        sample = (positive or matches)[-1]
        params = [dict(p, present_in_selected_sample=present(sample, p)) for p in doc['parameters']] if doc else []
        note = explanation(before['path'], env)
        item = {'method': key[0], 'path': key[1], 'prior_runtime_status': before['runtime_status'],
            'runtime_status': op['runtime_status'], 'user_document': {'snapshot': SNAPSHOT.relative_to(ROOT).as_posix(),
                'line': doc['line'] if doc else None, 'heading': doc['heading'] if doc else None,
                'in_original_77': doc is not None}, 'parameter_checks': params,
            'selected_request_id': sample['request_id'], 'selected_evidence_file': sample['evidence_file'],
            'selected_case_is_negative_probe': bool(sample.get('route_probe_only') or sample.get('negative_control')),
            'parameter_presence_is_not_business_success': True,
            'confirmed_explanation': note, 'runtime_reason': op['runtime_reason']}
        if doc is None: item['document_difference'] = '不在原77文件；只在新79操作清單／bundled2.22.3規格。不可假稱已按舊文件驗證此操作。'
        operations.append(item)
        table.append({'method': key[0], 'api': key[1], 'prior_status': before['runtime_status'], 'runtime_status': op['runtime_status'],
            'document_heading': doc['heading'] if doc else '原77文件未列', 'document_line': doc['line'] if doc else '',
            'selected_sample_is_negative_probe': item['selected_case_is_negative_probe'], 'confirmed_explanation': note})
    output = {'baseline_commit': BASELINE, 'reviewed_operations': len(operations), 'parsed_user_document_operations': len(docs),
        'user_document_sha256': hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(), 'original_document_modified': False,
        'source_note': '原件在Downloads/MSDSS；GitHub工作副本缺檔，獨立快照逐位元相同；不修改原API文件', 'operations': operations}
    (REPORTS / 'medusa-demo-v9-user-document-audit.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with (REPORTS / 'medusa-demo-v9-user-document-audit.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(table[0])); writer.writeheader(); writer.writerows(table)
    print(json.dumps({'reviewed': len(operations), 'manual_operations': len(docs), 'not_in_old_document': [x['path'] for x in operations if not x['user_document']['in_original_77']]}, ensure_ascii=False))


if __name__ == '__main__': main()
