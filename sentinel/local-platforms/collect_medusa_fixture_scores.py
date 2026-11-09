"""只從本輪gateway真實日誌按UUID擷取分數，不以離線預測補造。"""
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def main():
    reports = HERE / 'reports'
    names = ['medusa-demo-v9-fixture-checks.json', 'medusa-demo-v9-verification-fixture-checks.json']
    wanted = {r['request_id'] for name in names for r in json.loads((reports / name).read_text(encoding='utf-8'))['requests']}
    scores = {}
    pattern = re.compile(r'prediction label=(\w+) mode=(\w+) exploratory=(True|False) request_id=([\w-]+) probabilities=(\{.*\})')
    for line in (HERE / '.runtime/fixture-gateway.log').read_text(encoding='utf-8').splitlines():
        match = pattern.search(line)
        if match and match[4] in wanted:
            if match[4] in scores: raise RuntimeError('同一UUID有重複分數，須先釐清')
            scores[match[4]] = {'label': match[1], 'mode': match[2], 'exploratory': match[3] == 'True',
                              'request_id': match[4], 'probabilities': json.loads(match[5])}
    if scores.keys() != wanted: raise RuntimeError('缺少本輪真實gateway分數，不產生替代分數')
    output = {'source': 'actual isolated local HTTPS gateway log; UUID matched; not offline recomputation',
              'scores': list(scores.values())}
    (reports / 'medusa-demo-v9-fixture-gateway-scores.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
    print(json.dumps({'http_requests': len(wanted), 'actual_prediction_matches': len(scores)}))


if __name__ == '__main__': main()
