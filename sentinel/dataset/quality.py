"""Inspect candidates and propose leakage-safe groups; never approve labels or train."""
import argparse
import collections
import csv
import json
from pathlib import Path
from core import ROOT, grouped, read_jsonl, sha, verify_evidence


def inspect(rows):
    groups = grouped(rows)
    counts = collections.Counter(groups)
    largest = max(counts.values(), default=0)
    review = [r for r in rows if r['annotation']['eligible_for_review']]
    conflicts = collections.defaultdict(set)
    for r in rows:
        conflicts[r['metadata']['fingerprint']].add(r['annotation']['proposed_label'])
    collisions = [fp for fp, labels in conflicts.items() if len(labels) > 1]
    folds = []
    for heldout in ('bagisto', 'shopware', 'sylius'):
        test_groups = {g for r, g in zip(rows, groups) if r['metadata']['platform'] == heldout}
        train = [r['sample_id'] for r, g in zip(rows, groups) if r['metadata']['platform'] != heldout and g not in test_groups]
        test = [r['sample_id'] for r in rows if r['metadata']['platform'] == heldout]
        purged = [r['sample_id'] for r, g in zip(rows, groups) if r['metadata']['platform'] != heldout and g in test_groups]
        folds.append({'test_platform': heldout, 'outer_train_candidate_ids': train, 'outer_test_candidate_ids': test,
            'purged_cross_platform_overlap_ids': purged,
            'note': '僅候選外層分組；未核准標籤、未建立可訓練的內層切分。'})
    return {'candidate_count': len(rows), 'eligible_for_review': len(review),
        'proposed_class_counts': dict(collections.Counter(r['annotation']['proposed_label'] for r in rows)),
        'platform_counts': dict(collections.Counter(r['metadata']['platform'] for r in rows)),
        'unique_exact_requests': len({r['metadata']['fingerprint'] for r in rows}),
        'unique_near_forms': len({r['metadata']['near_fingerprint'] for r in rows}),
        'unique_attack_families': sorted({r['metadata']['family_id'] for r in rows if r['metadata'].get('family_id')}),
        'group_count': len(counts), 'largest_group': largest,
        'group_warning': '重複、家族與 session 連結可能造成大群組；不拆散來湊切分比例' if largest > len(rows) / 3 else None,
        'conflicting_label_fingerprints': collisions, 'training_ready': False,
        'dedup_limitation': '近似形式只處理大小寫、空白與整數變化；語意相近案例仍需人工來源家族審查。',
        'groups': [{'sample_id': r['sample_id'], 'group_id': g} for r, g in zip(rows, groups)], 'proposed_outer_folds': folds}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    review_path = args.output.with_suffix('.review.csv')
    if args.output.exists() or review_path.exists():
        raise RuntimeError('輸出或審核表已存在，請另選檔名，不覆寫人工決定')
    rows = read_jsonl(args.input)
    report = inspect(rows)
    report['input_sha256'] = sha(args.input.read_bytes())
    report['source_evidence_validated_count'] = sum(verify_evidence(r) for r in rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with review_path.open('w', newline='', encoding='utf-8-sig') as f:
        fields = ['sample_id', 'candidate_sha256', 'proposed_label', 'eligible_for_review', 'decision', 'final_label', 'reviewer', 'reason']
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({'sample_id': row['sample_id'], 'candidate_sha256': sha(row),
                'proposed_label': row['annotation']['proposed_label'],
                'eligible_for_review': row['annotation']['eligible_for_review']})
    print(json.dumps({k: v for k, v in report.items() if k not in ('groups', 'proposed_outer_folds', 'conflicting_label_fingerprints')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
