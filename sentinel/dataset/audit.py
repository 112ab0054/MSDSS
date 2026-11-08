"""Audit new dataset artifacts against real local secrets and source evidence."""
import json
import os
from pathlib import Path
import sys
from core import ROOT, read_jsonl, verify_evidence, sha

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'sentinel/local-platforms'))
from privacy_audit import local_secrets


def main():
    secrets = local_secrets()
    failures = []
    for directory, folders, files in os.walk(HERE):
        folders[:] = [f for f in folders if f not in ('.runtime', '__pycache__')]
        for name in files:
            p = Path(directory) / name
            if p.suffix not in ('.py', '.json', '.jsonl', '.csv', '.md', '.ps1'):
                continue
            raw = p.read_text(encoding='utf-8-sig')
            if any(value in raw for value in secrets):
                failures.append(p.relative_to(HERE).as_posix())
    source = HERE / 'reference/normal-candidates.jsonl'
    rows = read_jsonl(source)
    good = sum(verify_evidence(r) for r in rows)
    pending = all(r['annotation']['review_status'] == 'pending_human_review' and not r['metadata']['training_approved'] for r in rows)
    scenario = json.loads((HERE / 'scenario-catalog.json').read_text(encoding='utf-8'))
    scenarios_pending = scenario['executed'] is False and scenario['human_reviewed'] is False
    report = {'passed': not failures and good == len(rows) and pending and scenarios_pending,
        'credential_scan_passed': not failures, 'violating_files': failures,
        'reference_rows': len(rows), 'source_evidence_verified_rows': good,
        'reference_sha256': sha(source.read_bytes()), 'all_reference_rows_pending_human_review': pending,
        'scenario_catalog_is_unexecuted_proposals': scenarios_pending, 'training_started': False}
    (HERE / 'reports').mkdir(exist_ok=True)
    (HERE / 'reports/audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
