"""Export only explicit, traceable human approvals. No approval defaults, no training."""
import argparse
import csv
import json
from pathlib import Path
from core import LABELS, numeric_features, read_jsonl, sha, write_jsonl, verify_evidence


def approved(rows, decisions):
    by_id = {r['sample_id']: r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError('候選 sample ID 重複')
    seen = set()
    output = []
    for decision in decisions:
        sid = decision['sample_id']
        if sid in seen or sid not in by_id:
            raise ValueError('審核 ID 重複或找不到來源')
        seen.add(sid)
        if decision.get('decision', '').strip() != 'approve':
            continue
        row = by_id[sid]
        label = decision.get('final_label', '').strip()
        if (not row['annotation']['eligible_for_review'] or decision.get('candidate_sha256') != sha(row)
                or label not in LABELS or not decision.get('reviewer', '').strip() or not decision.get('reason', '').strip()):
            raise ValueError('核准缺乏有效來源、標籤或人工審核依據')
        output.append({'sample_id': sid, 'input': row['input'], 'label': label,
            'numeric_features': numeric_features(row['input']),
            'audit': {'candidate_sha256': sha(row), 'review_status': 'approved', 'reviewer': decision['reviewer'], 'reason': decision['reason'],
                      'metadata': row['metadata']}})
    return output


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--review', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise SystemExit('輸出已存在；請另選新檔名，不覆寫已審核資料。')
    rows = read_jsonl(args.input)
    with args.review.open(encoding='utf-8-sig', newline='') as f:
        decisions = list(csv.DictReader(f))
    approval_ids = {d['sample_id'] for d in decisions if d.get('decision', '').strip() == 'approve'}
    if any(not verify_evidence(r) for r in rows if r['sample_id'] in approval_ids):
        raise SystemExit('來源 HTTP 證據、request ID、回應狀態、請求內容或 SHA 不一致；拒絕匯出。')
    result = approved(rows, decisions)
    if not result:
        raise SystemExit('沒有明確人工核准的資料；未輸出訓練集。')
    write_jsonl(args.output, result)
    print(json.dumps({'approved_count': len(result), 'training_started': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
