"""Local-only pilot candidates. Labels remain proposals until human review.

SQL probes contain constants/NULL only; XSS probes use void(0), no external URL,
cookie access, exfiltration, file operations, delays or destructive statements.
"""
import json
from pathlib import Path
from core import sha

ASSIGNMENT = {
    'bagisto': ('sql.boolean', 'xss.script-element'),
    'shopware': ('sql.union-null', 'xss.event-handler'),
    'sylius': ('sql.stacked-constant', 'xss.javascript-link'),
}
NAMES = ['Alice', '王小明', "O'Connor", '陳美玲', 'Jean-Luc', 'Anna María', '林志明',
         '李佳慧', 'Mary Jane', '張雅婷', 'José', 'Anne-Marie', '吳家豪', 'Zoë', '黃怡君']
SEARCH = ['shirt', 'cotton', 'blue', 'red', '中文商品', 'A&B', "O'Connor", '100% cotton',
          'C++ guide', '(small)', 'https://example.test/catalog', 'select a size', 'script tutorial',
          '兒童衣服', '正常搜尋']


def cases(platform):
    sql_family, xss_family = ASSIGNMENT[platform]
    result = []
    for label in ('normal', 'sqli', 'xss'):
        count = 120 if label == 'normal' else 50
        for i in range(count):
            target = 'search' if i % 2 == 0 else 'address'
            # Pair two attack variants with a normal control without putting markers in HTTP values.
            pair = f'{platform}-pair-{i:03d}'
            if label == 'normal':
                value = (SEARCH if target == 'search' else NAMES)[(i // 2) % 15] + ' ' + str(i // 30 + 1)
                family = None
                if i >= 110:
                    target, value = 'address', ''
            elif label == 'sqli':
                n = i + 1
                if sql_family == 'sql.boolean': value = f"' OR {n}={n} -- "
                elif sql_family == 'sql.union-null': value = "' UNION SELECT " + ','.join(['NULL'] * (i % 5 + 1)) + f' /*{n}*/ -- '
                else: value = f"'; SELECT {n}; -- "
                family = sql_family
            else:
                if xss_family == 'xss.script-element': value = f'<script>void({i + 1})</script>'
                elif xss_family == 'xss.event-handler': value = f'<svg onload="void({i + 1})"></svg>'
                else: value = f'<a href="javascript:void({i + 1})">View item</a>'
                family = xss_family
            result.append({'case_id': sha([platform, label, i])[:24], 'proposed_label': label,
                'family_id': family, 'pair_group': pair, 'target': target, 'value': value,
                'normal_kind': 'missing_required_value' if label == 'normal' and i >= 110 else 'ordinary_or_special_text' if label == 'normal' else None,
                'review_status': 'pending_human_review', 'source': 'local hand-authored pilot templates v1'})
    # Interleave labels: avoid collecting all attacks only after the normal session has expired.
    return sorted(result, key=lambda c: (int(c['pair_group'].rsplit('-', 1)[1]), c['proposed_label']))


def main():
    here = Path(__file__).resolve().parent
    output = {p: cases(p) for p in ASSIGNMENT}
    report = {'version': 1, 'executed': False, 'human_reviewed': False,
        'assignment_note': '每平台僅一個 SQLi／XSS 家族，跨平台不共用家族；僅供工具試產，不能據此宣稱廣泛泛化。',
        'normal_target_count_per_platform': 120, 'normal_workflow_goal_per_platform': 30,
        'attack_target_count_per_class_per_platform': 50, 'platforms': output}
    (here / 'scenario-catalog.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('候選情境已建立；沒有發送 HTTP，也沒有產生實測攻擊資料。')


if __name__ == '__main__':
    main()
