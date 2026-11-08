"""Lossless, UTF-8-BOM CSV reading views. Original training/evidence files stay intact.

CSV is a flat-text export (no workbook/formulas). Nested values remain JSON in
cells so quotes, newlines, null, booleans and types can be reconstructed exactly.
"""
import csv
import json
from pathlib import Path
from core import read_jsonl, sha

HERE = Path(__file__).resolve().parent


def j(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def write_csv(path, rows, headers):
    if path.exists():
        raise RuntimeError('輸出已存在，不覆寫已編輯的 CSV：' + path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)
    with path.open(encoding='utf-8-sig', newline='') as stream:
        result = list(csv.DictReader(stream))
    assert result == [{key: str(row[key]) for key in headers} for row in rows], 'CSV 欄位往返不一致'
    return result


def parameters(value, path=''):
    if isinstance(value, dict) and value:
        for key, item in value.items():
            yield from parameters(item, path + '.' + key if path else key)
    elif isinstance(value, list) and value:
        for index, item in enumerate(value):
            yield from parameters(item, f'{path}[{index}]')
    else:
        yield path or '(整體)', value


def main():
    normal_path = HERE / 'reference/normal-candidates.jsonl'
    scenario_path = HERE / 'scenario-catalog.json'
    source_hashes = {str(p.relative_to(HERE)): sha(p.read_bytes()) for p in (normal_path, scenario_path)}
    normals = read_jsonl(normal_path)
    catalog = json.loads(scenario_path.read_text(encoding='utf-8'))
    paths = [HERE / 'reference/normal-candidates.csv', HERE / 'reference/normal-parameters.csv', HERE / 'scenario-catalog.csv']
    if any(path.exists() for path in paths):
        raise RuntimeError('至少一份 CSV 已存在；請先保留人工變更，不自動覆寫。')
    normal_rows, detail_rows = [], []
    for index, row in enumerate(normals, 1):
        req, meta, annotation = row['input'], row['metadata'], row['annotation']
        normal_rows.append({'序號': index, '平台': meta['platform'], 'HTTP方法': req['method'], 'API路徑': req['path'],
            '候選類別': annotation['proposed_label'], 'HTTP狀態碼': meta['http_status'],
            '審核狀態': annotation['review_status'], '來源類型': meta['origin'],
            'query參數': j(req['query']), 'body參數': j(req['body']), 'headers': j(req['headers']),
            '樣本ID': row['sample_id'], '分組批次': meta['session_group'],
            '來源證據': meta['source_evidence'], '原請求ID': meta['request_id'], '完整紀錄JSON': j(row)})
        for location in ('query', 'body', 'headers'):
            for field, value in parameters(req[location]):
                detail_rows.append({'請求序號': index, '平台': meta['platform'], 'HTTP方法': req['method'],
                    'API路徑': req['path'], '位置': location, '參數名稱': field,
                    '參數值JSON': j(value), '候選類別': annotation['proposed_label'], '樣本ID': row['sample_id']})
    scenario_rows = []
    for platform, cases in catalog['platforms'].items():
        for case in cases:
            scenario_rows.append({'序號': len(scenario_rows) + 1, '平台': platform,
                '候選類別': case['proposed_label'], '目標': case['target'], '輸入內容JSON': j(case['value']),
                '家族': case['family_id'] or '', '正常子情境': case.get('normal_kind') or '',
                '審核狀態': case['review_status'], '是否實際送出': 'false',
                '情境ID': case['case_id'], '對照組': case['pair_group'], '來源': case['source'], '完整情境JSON': j(case)})
    normal_read = write_csv(paths[0], normal_rows, list(normal_rows[0]))
    detail_read = write_csv(paths[1], detail_rows, list(detail_rows[0]))
    scenario_read = write_csv(paths[2], scenario_rows, list(scenario_rows[0]))
    assert [json.loads(row['完整紀錄JSON']) for row in normal_read] == normals
    for row, original in zip(normal_read, normals):
        assert json.loads(row['query參數']) == original['input']['query']
        assert json.loads(row['body參數']) == original['input']['body']
        assert json.loads(row['headers']) == original['input']['headers']
    recovered = {platform: [] for platform in catalog['platforms']}
    for row in scenario_read:
        case = json.loads(row['完整情境JSON'])
        assert json.loads(row['輸入內容JSON']) == case['value']
        recovered[row['平台']].append(case)
    assert recovered == catalog['platforms']
    for path, before in source_hashes.items():
        assert sha((HERE / path).read_bytes()) == before, '原始檔案被修改'
    result = {'format': 'CSV UTF-8 BOM; quoted fields; embedded JSON for typed nested values',
        'normal_request_rows': len(normal_read), 'normal_parameter_rows': len(detail_read),
        'unexecuted_scenario_rows': len(scenario_read), 'full_record_roundtrip_equal': True,
        'nested_input_roundtrip_equal': True, 'source_files_unchanged': True, 'source_sha256': source_hashes,
        'outputs': {str(p.relative_to(HERE)): sha(p.read_bytes()) for p in paths},
        'training_started': False, 'deduplication_changed': False}
    (HERE / 'reports/csv-conversion.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
