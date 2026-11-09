"""以當前 Store API 已驗證語言更新配對資料；不新增攻擊、不改切分。"""
import argparse
import copy
import json
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'sentinel/model'))
from data_io import read_rows
from build_small_dataset import sha, write_csv
from build_train_v5 import flat
from build_xss_v3 import set_field
from annotate_attack_facets import attack_facets, COLUMN

SPLITS = ('train', 'test', 'validation', 'challenge')


def build(source, output, inventory):
    evidence = json.loads(inventory.read_text(encoding='utf-8'))
    if not evidence.get('verified') or not evidence.get('read_only'):
        raise ValueError('語言清單尚未完成實機查詢')
    languages = sorted({x['id'] for x in evidence['languages'] if x.get('accepted') is True})
    if len(languages) < 2:
        raise ValueError('目前尚未實證至少兩個可用語言；不捏造 ID')
    if output.exists():
        raise ValueError('輸出已存在，不能覆寫舊版')
    sets = {}; mapping = []; counts = {}; changes = []
    for split in SPLITS:
        rows = read_rows(source / (split + '.csv'))
        groups = defaultdict(list)
        for row in rows:
            groups[row['metadata']['pair_group']].append(row)
        rebuilt = {}; index = 0; count = Counter()
        for pair, triple in groups.items():
            normal = next(r for r in triple if r['annotation']['proposed_label'] == 'normal')
            header = normal['input']['headers']
            if normal['metadata']['platform'] != 'shopware' or 'sw-language-id' not in header:
                for row in triple:
                    rebuilt[row['sample_id']] = copy.deepcopy(row)
                continue
            language = languages[index % len(languages)]; index += 1; count[language] += 1
            new_pair = sha(['live-language-v8', pair, language])
            new_ids = {r['sample_id']: sha(['live-language-v8', r['sample_id'], language]) for r in triple}
            for row in triple:
                new = copy.deepcopy(row)
                new['input']['headers']['sw-language-id'] = language
                # 若攻擊目標本身就是語言 header，必須保留原攻擊文字。
                meta = row['metadata']
                if row['annotation']['proposed_label'] != 'normal':
                    set_field(new['input'], meta['target_location'], meta['target_parameter'], meta['payload']['value'])
                new['sample_id'] = new_ids[row['sample_id']]
                new['metadata'].update(pair_group=new_pair, language_source_sample_id=row['sample_id'],
                                       language_inventory_sha256=sha(inventory.read_bytes()))
                if row['annotation']['proposed_label'] != 'normal':
                    new['metadata']['control_sample_id'] = new_ids[normal['sample_id']]
                rebuilt[row['sample_id']] = new
                if new['input'] != row['input']:
                    changes.append({'split': split, 'old_sample_id': row['sample_id'],
                                    'new_sample_id': new['sample_id'], 'label': row['annotation']['proposed_label'],
                                    'old_language_id': header['sw-language-id'], 'new_language_id': language})
        sets[split] = [rebuilt[r['sample_id']] for r in rows]
        for old, new in zip(rows, sets[split]):
            mapping.append({'split': split, 'old_sample_id': old['sample_id'], 'new_sample_id': new['sample_id'],
                            'input_changed': old['input'] != new['input']})
        counts[split] = dict(count)
    fingerprints = [sha(r['input']) for rows in sets.values() for r in rows]
    if len(set(fingerprints)) != len(fingerprints):
        raise ValueError('出現重複請求，停止產生')
    output.mkdir(parents=True)
    # 僅攜帶靜態資料說明；不複製舊模型評估或舊 verification 結果。
    for name in ('skeleton-catalog.csv', 'external-payloads.csv', 'HTTPPARAMS-LICENSE.txt',
                 'attack-facets-rules.json', 'document-value-rules.json', 'document-field-status.csv',
                 'historical-public-values.json'):
        if (source / name).is_file():
            shutil.copy2(source / name, output / name)
    shutil.copy2(inventory, output / 'shopware-language-inventory.json')
    for split, rows in sets.items():
        values = []
        for row in rows:
            value = flat(row); value[COLUMN] = '；'.join(attack_facets(row)); values.append(value)
        write_csv(output / (split + '.csv'), values)
    write_csv(output / 'language-value-changes.csv', changes)
    write_csv(output / 'language-source-sample-map.csv', mapping)
    saved = json.loads((source / 'provenance.json').read_text(encoding='utf-8'))
    saved.update(dataset_revision='v8-live-languages',
                 parent_dataset=source.name,
                 parent_csv_sha256={s: sha((source / (s + '.csv')).read_bytes()) for s in SPLITS},
                 frozen_holdout_sha256={s: sha((output / (s + '.csv')).read_bytes()) for s in SPLITS if s != 'train'},
                 holdout_change_reason='User requested real language diversity; headers changed symmetrically per pair, not metric-selected',
                 language_correction={'inventory_sha256': sha(inventory.read_bytes()),
                     'accepted_ids': languages, 'normal_header_counts': counts,
                     'changed_request_rows': len(changes), 'allocation': 'round-robin within split, same language per normal/sqli/xss triple; attack on language preserved',
                     'only_language_requests_http_verified': True,
                     'dataset_requests_http_verified': False})
    (output / 'provenance.json').write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding='utf-8')
    (output / 'README.md').write_text('# v8：實機語言 ID 多樣性\n\n依目前本機 Shopware 語言清單與 context 語言鏈驗證，平均分配有效 ID。每組 normal／SQLi／XSS 使用相同背景語言，保留原攻擊文字、標籤、集合與骨架。原 v7 保留；新舊 sample ID 有映射。\n\n語言 API 成功不代表 1098 筆資料已全部送出；資料仍是 offline。舊模型未自動換成新模型，需用新版 dataset.zip 重新訓練。\n\n' + json.dumps(saved['language_correction'], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return saved['language_correction']


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT / 'sentinel/dataset/small-api-v7')
    p.add_argument('--output', type=Path, default=ROOT / 'sentinel/dataset/small-api-v8')
    p.add_argument('--inventory', type=Path, default=ROOT / 'sentinel/local-platforms/reports/shopware-language-inventory.json')
    args = p.parse_args()
    print(json.dumps(build(args.source, args.output, args.inventory), ensure_ascii=False, indent=2))
