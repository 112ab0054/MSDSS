"""Import only genuine, already-passed normal evidence into a review-only reference set."""
import collections
import csv
import json
from pathlib import Path
from core import ROOT, manifest, sample, sha, write_jsonl

HERE = Path(__file__).resolve().parent


def main():
    selected = {(o['platform'], o['method'], o['path']) for o in manifest()['operations']}
    output = []
    for platform in ('bagisto', 'shopware', 'sylius'):
        environment = json.loads((ROOT / f'sentinel/local-platforms/reports/{platform}-environment.json').read_text(encoding='utf-8'))
        versions = {k: v for k, v in environment.items() if 'version' in k and isinstance(v, (str, int, float))}
        for path in sorted((ROOT / 'sentinel/local-platforms/reports').glob(platform + '-*.json')):
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            if not isinstance(data, dict) or data.get('outcome') != 'passed':
                continue
            batch = 'historical-' + path.stem
            for row in data.get('requests', []):
                if ((platform, row['method'], row['operation_path']) not in selected or not row.get('business_verified')
                        or not 200 <= row.get('status', 0) < 300):
                    continue
                item = sample(platform, path.relative_to(ROOT).as_posix(), row, batch, versions=versions)
                item['metadata']['source_evidence_sha256'] = sha(path.read_bytes())
                output.append(item)
    write_jsonl(HERE / 'reference/normal-candidates.jsonl', output)
    counts = collections.Counter(r['metadata']['platform'] for r in output)
    ops = {(r['metadata']['platform'], r['input']['method'], r['metadata']['operation_path']) for r in output}
    report = {'origin': 'historical_real_http_evidence', 'new_http_requests': 0, 'pilot_live_collected': 0,
        'candidate_count': len(output), 'platform_counts': dict(counts), 'covered_selected_operations': len(ops),
        'exact_unique_inputs': len({r['metadata']['fingerprint'] for r in output}),
        'attack_samples': 0, 'human_approved_training_samples': 0,
        'excluded_selected_operations': sorted(selected - ops)}
    (HERE / 'reference/summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    # Only actually observed inputs are marked as observed; this is not a declaration of full parameter correctness.
    whitelist = []
    def visit(value, prefix, found):
        if isinstance(value, dict):
            for k, v in value.items():
                field = prefix + '.' + k if prefix else k
                found.add(field)
                visit(v, field, found)
        elif isinstance(value, list):
            for v in value:
                visit(v, prefix + '[]', found)
    for platform, method, path in sorted(selected):
        fields = set()
        relevant = [r for r in output if (r['metadata']['platform'], r['input']['method'], r['metadata']['operation_path']) == (platform, method, path)]
        for r in relevant:
            visit(r['input']['query'], 'query', fields)
            visit(r['input']['body'], 'body', fields)
        whitelist.append({'platform': platform, 'method': method, 'path': path, 'observed_fields': sorted(fields),
            'evidence_sample_ids': [r['sample_id'] for r in relevant], 'collection_ready': False,
            'note': '僅成功情境曾送出的欄位，不代表每個參數效果已單獨證明。'})
    (HERE / 'parameter-scope.json').write_text(json.dumps({'operations': whitelist}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
