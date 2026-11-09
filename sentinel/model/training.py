"""固定 train/test/獨立 validation 的 XGBoost 訓練與可搬移模型輸出。"""
import argparse
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import time
import zipfile
import itertools
import numpy as np
from sklearn.dummy import DummyClassifier
from xgboost import XGBClassifier
from preflight import inspect_dataset
from evaluate import save_evaluation
from features import features, LABELS, VERSION, layout
from request_input import INPUT_VERSION


HERE = Path(__file__).resolve().parent


def run(group_function):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=HERE.parent / 'dataset/small-api-v3', help='預設 small-api-v3；Colab 請指定解壓縮後的 data 目錄')
    parser.add_argument('--output', type=Path, help='訓練輸出新目錄；--check-only 不需要')
    parser.add_argument('--check-only', action='store_true', help='只列出資料資格與分組問題，不訓練、不產生成績')
    parser.add_argument('--evidence-root', type=Path)
    parser.add_argument('--header-config', type=Path, default=HERE / 'header-schema.json')
    parser.add_argument('--allow-candidates', action='store_true', help='只供原文／來源證據不完整的流程試跑；仍拒絕未送出計畫，與人工審核無關')
    parser.add_argument('--mode', choices=['live', 'offline'], default='live', help='offline 可使用生成請求；結果明確標為未實機驗證')
    parser.add_argument('--trees', type=int, default=150, help='事先固定樹數；不使用 test/validation 選樹數')
    args = parser.parse_args()
    if not args.check_only and args.output is None:
        parser.error('訓練需要 --output；只檢查請加 --check-only')
    output = args.output.resolve() if args.output else None
    if output and output.exists() and any(output.iterdir()):
        raise ValueError('輸出已有檔案；請使用新實驗目錄')
    if not 1 <= args.trees <= 1000:
        raise ValueError('trees 必須介於 1 與 1000')
    paths = {s: args.data_dir / (s + '.csv') for s in ('train', 'test', 'validation')}
    if (args.data_dir/'challenge.csv').is_file():paths['challenge']=args.data_dir/'challenge.csv'
    schema = json.loads(args.header_config.read_text(encoding='utf-8-sig'))
    # 固定三份 CSV：不重新切分，也不偷偷把獨立驗證資料加回訓練。
    sets, all_rows, indices, group, readiness = inspect_dataset(
        args.data_dir, group_function, args.allow_candidates, args.evidence_root, schema, offline=args.mode == 'offline')
    if args.check_only:
        print(json.dumps(readiness, ensure_ascii=False, indent=2))
        if not readiness['ready']:
            raise SystemExit(2)
        return
    if not readiness['ready']:
        raise SystemExit('訓練前檢查未通過：\n- ' + '\n- '.join(readiness['errors']))
    names = schema['header_names']
    if names != sorted(set(names)) or any(n != n.lower() for n in names):
        raise ValueError('header schema 順序或名稱不合法')
    x, y = {}, {}
    for s, rows in sets.items():
        labels = [r['annotation'].get('label', r['annotation'].get('proposed_label')) for r in rows]
        if set(labels) != set(LABELS):
            raise ValueError(f'{s} 必須包含 normal/sqli/xss 三類')
        x[s] = np.asarray([features(r['input'], names) for r in rows], dtype=np.float32)
        y[s] = np.asarray([LABELS.index(label) for label in labels])
    # 事先固定 CPU 參數；test 與獨立 validation 都不參與選樹數或門檻。
    model = XGBClassifier(n_estimators=args.trees, max_depth=3, learning_rate=0.05,
                          objective='multi:softprob', num_class=3, eval_metric='mlogloss',
                          tree_method='hist', device='cpu', n_jobs=2, random_state=42)
    started = time.perf_counter()
    model.fit(x['train'], y['train'], verbose=False)
    seconds = time.perf_counter() - started
    baseline = DummyClassifier(strategy='most_frequent').fit(x['train'], y['train'])
    output.mkdir(parents=True, exist_ok=True)
    bundle = output / 'inference'
    bundle.mkdir()
    model.save_model(bundle / 'model.json')
    packages = {n: importlib.metadata.version(n) for n in ('numpy', 'scikit-learn', 'xgboost')}
    meta = {'bundle_version': 1, 'feature_version': VERSION, 'request_input_version': INPUT_VERSION,
            'labels': LABELS, 'header_names': names, 'feature_count': int(x['train'].shape[1]), 'feature_layout': layout(),
            'header_document_sha256': schema['document_sha256'], 'exploratory': bool(args.allow_candidates or args.mode == 'offline'),
            'mode': args.mode, 'platform_http_verified': args.mode == 'live' and not args.allow_candidates,
            'python': platform.python_version(), 'packages': packages, 'parameters': model.get_params(),
            'training_seconds': seconds, 'trees_selection': 'predeclared_not_selected_by_holdout'}
    (bundle / 'metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    for name in ('features.py', 'request_input.py', 'predict.py'):
        shutil.copyfile(HERE / name, bundle / name)
    # 記錄訓練時套件版本；到 Windows／Ubuntu 重新安裝，不複製 Colab 虛擬環境。
    (bundle / 'requirements-inference.txt').write_text('\n'.join(
        f'{name}=={packages[name]}' for name in ('numpy', 'scikit-learn', 'xgboost')) + '\n', encoding='utf-8')
    # 可搬移性自測只取訓練樣本，避免將測試資料打包到部署端。
    probes = []
    for label in LABELS:
        row = next(r for r in sets['train'] if r['annotation'].get('label', r['annotation'].get('proposed_label')) == label)
        req = row['input']
        from request_input import prepare_request
        sanitized = prepare_request(req)
        probabilities = model.predict_proba([features(sanitized, names)])[0]
        probes.append({'request': sanitized, 'probabilities': list(map(float, probabilities))})
    (bundle / 'self-test.json').write_text(json.dumps(probes, ensure_ascii=False, indent=2), encoding='utf-8')
    (bundle / 'README.md').write_text('# 可搬移推論套件\n\n安裝 requirements-inference.txt，執行 '
        '`python predict.py --self-test --model .`。此路徑由命令明確提供；預設也會在 predict.py 旁尋找模型。'
        '模型以 XGBoost JSON 儲存，沒有 pickle 或訓練資料的絕對路徑。'
        '跨系統需實際執行 self-test；未經校準的機率不是正確率保證。\n', encoding='utf-8')
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in bundle.iterdir() if p.is_file()}
    (bundle / 'bundle-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    with zipfile.ZipFile(output / 'inference.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for file in sorted(bundle.iterdir()):
            z.write(file, file.name)
    counts = {s: {label: int(sum(y[s] == i)) for i, label in enumerate(LABELS)} for s in sets}
    feature_sets = {s: {tuple(v) for v in x[s]} for s in sets}
    overlap = {a + '/' + b: len(feature_sets[a] & feature_sets[b])
               for a, b in itertools.combinations(sets,2)}
    audit = {**meta, 'counts': counts, 'group_overlap': 0,
             'independent_groups': {s: len(set(group[indices[s]])) for s in sets},
             'identical_feature_vectors_shared': overlap,
             'data_sha256': {s: hashlib.sha256(p.read_bytes()).hexdigest() for s, p in paths.items()},
             'source_sha256': {n: hashlib.sha256((HERE / n).read_bytes()).hexdigest()
                               for n in ('train.py', 'training.py', 'preflight.py', 'data_io.py', 'evaluate.py', 'features.py', 'request_input.py')},
             'seed': 42, 'platform': platform.system(), 'readiness': readiness}
    (output / 'experiment.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
    with (output / 'split.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['sample_id', 'platform', 'group', 'split'])
        for s, rows in sets.items():
            for row, g in zip(rows, group[indices[s]]):
                writer.writerow([row['sample_id'], row['metadata']['platform'], int(g), s])
    reports = {}
    for s in [s for s in sets if s!='train']:
        folder = output / s
        folder.mkdir()
        timings = []
        model.predict_proba(x[s][:1])
        for row in sets[s]:
            t = time.perf_counter()
            model.predict_proba([features(row['input'], names)])
            timings.append((time.perf_counter() - t) * 1000)
        report_audit = {**audit, 'evaluated_split': s,
                        'latency_ms': {'median': float(np.median(timings)), 'p95': float(np.percentile(timings, 95))}}
        reports[s] = save_evaluation(folder, y[s], model.predict_proba(x[s]),
                baseline.predict_proba(x[s]), sets[s], group[indices[s]], report_audit)
    (output / 'summary.md').write_text('# 分開保留的評估結果\n\n'
        f'模式：{args.mode}；探索性實驗：{meta["exploratory"]}。離線分類成績不代表平台 HTTP 實測或漏洞成功。\n\n'
        '| 集合 | Accuracy | Macro-F1 |\n|---|---:|---:|\n' + '\n'.join(
        f'| {s} | {r["accuracy"]:.6f} | {r["macro_f1"]:.6f} |' for s, r in reports.items()) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(output), 'mode': args.mode, 'exploratory': meta['exploratory'],
                      'metrics': {s: {'accuracy': r['accuracy'], 'macro_f1': r['macro_f1']} for s, r in reports.items()}}, ensure_ascii=False))
