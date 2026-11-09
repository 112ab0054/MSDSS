"""從真實uvicorn日誌依UUID匯入模型分數；缺少時拒絕，不重算或補值。"""
import argparse
import json
from pathlib import Path
import re

PATTERN = re.compile(r'prediction label=(normal|sqli|xss) mode=(\w+) exploratory=(True|False) request_id=([0-9a-fA-F-]{36}) probabilities=(\{[^\r\n]+\})')


def collect(log, evidence):
    expected = {r['request_id'] for r in evidence['requests']}; scores = {}
    for match in PATTERN.finditer(log):
        request_id = match[4]
        if request_id not in expected: continue
        probabilities = json.loads(match[5])
        if set(probabilities) != {'normal', 'sqli', 'xss'} or not all(isinstance(x, (int, float)) and 0 <= x <= 1 for x in probabilities.values()):
            raise ValueError('分數結構不合法')
        if abs(sum(probabilities.values()) - 1) > 1e-5: raise ValueError('分數總和不符')
        row = {'request_id': request_id, 'label': match[1], 'mode': match[2], 'exploratory': match[3] == 'True', 'probabilities': probabilities}
        if request_id in scores and scores[request_id] != row: raise ValueError('同一UUID有不同分數')
        scores[request_id] = row
    missing = expected - set(scores)
    if missing: raise ValueError(f'缺少{len(missing)}筆實際gateway日誌，不以離線推論替代')
    return {'source': 'actual gateway log UUID import; not offline recalculation', 'scores': [scores[r['request_id']] for r in evidence['requests']]}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--log', type=Path, required=True)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    # PowerShell重導向可能寫UTF-16，依BOM明確選解碼方式。
    raw = args.log.read_bytes(); encoding = 'utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig'
    result = collect(raw.decode(encoding), json.loads(args.evidence.read_text(encoding='utf-8-sig')))
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Imported actual gateway scores:', len(result['scores']))
