"""固定集合的 XGBoost 訓練與評估：支援 live/offline，保留 test、validation 與可選 challenge。"""
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
    """輸入 group_function：接受所有樣本並回傳群組編號的函式（目前為 train.groups）。
    其他輸入從命令列讀取；正常完成時印出摘要並把結果寫到 --output。
    本函式沒有回傳模型物件；部署要使用輸出的 inference/ 或 inference.zip。

    命令列參數如何用：
    --data-dir：放 train.csv、test.csv、validation.csv 的資料夾，不是某一份 CSV 路徑。
    --evidence-root：來源證據的根資料夾；再接 metadata 內相對路徑才能找到證據檔。
    --header-config：具名 header 的固定順序與文件 SHA，預設讀程式旁的 header-schema.json。
    --output：新的實驗輸出資料夾，不能是已裝有舊結果的目錄。
    --trees：樹的數量，預設 150；須事先固定，不使用保留集合反覆試到最高分。
    --check-only：完成資料檢查就退出，不建立模型、不產生成績。
    --allow-candidates：證據條件較寬的流程試跑，輸出會標 exploratory；仍拒絕已知未送出的計畫。

    主要變數：
    sets['train'] 等保存完整樣本；x 保存特徵矩陣；y 保存標籤編號。
    例如 450 筆、2402 特徵時，x['train'].shape 為 (450, 2402)，y['train'].shape 為 (450,)。
    indices 保存各集合在 all_rows 中的位置，group 保存每列的關聯群編號。
    schema/names 保存 header 規格；model 是唯一的 XGBoost 分類器。
    baseline 是永遠猜 train 最大類的比較對象，不會取代 model 或參與其學習。

    執行順序：
    1. 解析路徑與參數，防止覆寫先前實驗。
    2. 檢查三份固定 CSV 與存在時的 challenge.csv 的標籤、HTTP 證據、平台與跨集合群組交集。
    3. 只把每筆 input 轉成數值向量，再把類別轉成 0/1/2。
    4. 呼叫一次 fit，且只傳 train。
    5. 寫出模型、同版推論程式、版本資訊與跨環境自測探針。
    6. 用同一模型分別評估 test、validation 與存在時的 challenge，各自保存數據。

    輸出如何閱讀：
    experiment.json 核對資料／程式版本；split.csv 核對樣本落在哪一集合。
    test/report.md 與 validation/report.md 是可讀報告，各自的 report.json 保留完整數值。
    predictions.csv 用樣本 ID 找誤判；confusion_matrix.csv 看各類被錯認成哪一類。
    inference.zip 是部署套件，不包含整份測試資料；自測只帶 train 的三類探針。

    檢查通過不是 normal 內容正確或模型有效的保證。沒有重新切分、沒有用 HTTP 狀態碼當特徵，
    也沒有依 test/validation 分數修改樹數、機率門檻或挑掉難題。

    新版模式與資料：預設 data-dir 改為 small-api-v6，增加 --mode live/offline。
    live 是預設模式，要求實測證據；offline 允許生成請求，但保留配對與原文格式檢查。
    offline 的輸出一律 exploratory=True、platform_http_verified=False，不能用其分數冒充 HTTP 實測。
    --allow-candidates 是原本的較寬條件試跑開關，與 --mode 不同，不能把兩者當成同一選項。
    challenge.csv 若存在，就納入來源／群組檢查和評估，不加入 fit 或早停。

    v5 特徵布局寫入 feature_layout；當 header 數為 12 時，完整向量已是 2402 維，不是舊版 278。
    模型仍只有一個；每份保留集合是同一模型的不同考題，不能依它們的分數反覆修到滿意。
    此處的 platform_http_verified 依執行模式設定；不是漏洞成功、normal 業務有效或泛化能力證明。
    """
    # 路徑交給 pathlib；資料、輸出與證據根目錄分開設定，搬到其他 OS 不依賴原電腦磁碟機。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=HERE.parent / 'dataset/small-api-v6', help='預設 small-api-v6；Colab 請指定解壓縮後的 data 目錄')
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
    # challenge 是可選保留題，存在才加進來源記錄；不會因此變成訓練資料。
    if (args.data_dir/'challenge.csv').is_file():paths['challenge']=args.data_dir/'challenge.csv'
    schema = json.loads(args.header_config.read_text(encoding='utf-8-sig'))
    # 固定三份 CSV：不重新切分，也不偷偷把獨立驗證資料加回訓練。
    # 檢查資料與實驗協議；offline 是明確來源模式，不是把未送出的資料偽裝成已實測。
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
    # x[集合] 每列是一筆特徵，y[集合] 是 normal/sqli/xss 對應的 0/1/2。
    # annotation、HTTP 回應和來源 metadata 不會被 features 當成輸入。
    x, y = {}, {}
    for s, rows in sets.items():
        labels = [r['annotation'].get('label', r['annotation'].get('proposed_label')) for r in rows]
        if set(labels) != set(LABELS):
            raise ValueError(f'{s} 必須包含 normal/sqli/xss 三類')
        x[s] = np.asarray([features(r['input'], names) for r in rows], dtype=np.float32)
        y[s] = np.asarray([LABELS.index(label) for label in labels])
    # 事先固定 CPU 參數；test 與獨立 validation 都不參與選樹數或門檻。
    # 150 棵樹是事先設定值；max_depth=3 限制每棵深度，learning_rate=.05 控制修正幅度。
    # multi:softprob 回三類分數；CPU/hist 不要求 GPU；seed 固定便於重現。
    # 未傳 eval_set，也未做 early stopping，保留集合不參與訓練參數選擇。
    model = XGBClassifier(n_estimators=args.trees, max_depth=3, learning_rate=0.05,
                          objective='multi:softprob', num_class=3, eval_metric='mlogloss',
                          tree_method='hist', device='cpu', n_jobs=2, random_state=42)
    started = time.perf_counter()
    # 唯一讓模型學習的呼叫，只傳 train；同一模型稍後分別考不同保留集合。
    model.fit(x['train'], y['train'], verbose=False)
    seconds = time.perf_counter() - started
    # 基準只學 train 最常見類別，讓報告能與永遠猜最大類的策略比較。
    baseline = DummyClassifier(strategy='most_frequent').fit(x['train'], y['train'])
    output.mkdir(parents=True, exist_ok=True)
    bundle = output / 'inference'
    bundle.mkdir()
    # JSON 保存樹模型，不 pickle 本機 Python 物件；版本與特徵布局另放 metadata。
    model.save_model(bundle / 'model.json')
    packages = {n: importlib.metadata.version(n) for n in ('numpy', 'scikit-learn', 'xgboost')}
    # exploratory 同時涵蓋 offline 與 allow-candidates；平台驗證標記不能當漏洞成功證明。
    meta = {'bundle_version': 1, 'feature_version': VERSION, 'request_input_version': INPUT_VERSION,
            'labels': LABELS, 'header_names': names, 'feature_count': int(x['train'].shape[1]), 'feature_layout': layout(),
            'header_document_sha256': schema['document_sha256'], 'exploratory': bool(args.allow_candidates or args.mode == 'offline'),
            'mode': args.mode, 'platform_http_verified': args.mode == 'live' and not args.allow_candidates,
            'python': platform.python_version(), 'packages': packages, 'parameters': model.get_params(),
            'training_seconds': seconds, 'trees_selection': 'predeclared_not_selected_by_holdout'}
    (bundle / 'metadata.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    for name in ('features.py', 'request_input.py', 'predict.py'):
        shutil.copyfile(HERE / name, bundle / name)
    # 記錄訓練時套件版本；到 Windows／Ubuntu 重新安裝，不複製 Colab 虛擬環境。
    (bundle / 'requirements-inference.txt').write_text('\n'.join(
        f'{name}=={packages[name]}' for name in ('numpy', 'scikit-learn', 'xgboost')) + '\n', encoding='utf-8', newline='\n')
    # 可搬移性自測只取訓練樣本，避免將測試資料打包到部署端。
    probes = []
    for label in LABELS:
        row = next(r for r in sets['train'] if r['annotation'].get('label', r['annotation'].get('proposed_label')) == label)
        req = row['input']
        from request_input import prepare_request
        sanitized = prepare_request(req)
        probabilities = model.predict_proba([features(sanitized, names)])[0]
        probes.append({'request': sanitized, 'probabilities': list(map(float, probabilities))})
    (bundle / 'self-test.json').write_text(json.dumps(probes, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    (bundle / 'README.md').write_text('# 可搬移推論套件\n\n安裝 requirements-inference.txt，執行 '
        '`python predict.py --self-test --model .`。此路徑由命令明確提供；預設也會在 predict.py 旁尋找模型。'
        '模型以 XGBoost JSON 儲存，沒有 pickle 或訓練資料的絕對路徑。'
        '跨系統需實際執行 self-test；未經校準的機率不是正確率保證。\n', encoding='utf-8', newline='\n')
    # SHA 包含註解及空白；新程式必須與新清單一起打包，不能單換 .py 配舊模型套件。
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in bundle.iterdir() if p.is_file()}
    (bundle / 'bundle-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8', newline='\n')
    with zipfile.ZipFile(output / 'inference.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for file in sorted(bundle.iterdir()):
            z.write(file, file.name)
    counts = {s: {label: int(sum(y[s] == i)) for i, label in enumerate(LABELS)} for s in sets}
    # 原請求不同也可能映成同向量，另報所有集合配對的交集供查核，不靠刪資料提高成績。
    feature_sets = {s: {tuple(v) for v in x[s]} for s in sets}
    overlap = {a + '/' + b: len(feature_sets[a] & feature_sets[b])
               for a, b in itertools.combinations(sets,2)}
    audit = {**meta, 'counts': counts, 'group_overlap': 0,
             'independent_groups': {s: len(set(group[indices[s]])) for s in sets},
             'attack_skeleton_groups': {s:readiness['splits'][s]['attack_skeleton_groups'] for s in sets},
             'evaluation_protocols': sorted({r['metadata'].get('evaluation_protocol','legacy') for r in all_rows}),
             'identical_feature_vectors_shared': overlap,
             'data_sha256': {s: hashlib.sha256(p.read_bytes()).hexdigest() for s, p in paths.items()},
             'source_sha256': {n: hashlib.sha256((HERE / n).read_bytes()).hexdigest()
                               for n in ('train.py', 'training.py', 'preflight.py', 'data_io.py', 'evaluate.py', 'features.py', 'request_input.py', 'skeletons.py')},
             'seed': 42, 'platform': platform.system(), 'readiness': readiness}
    (output / 'experiment.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    with (output / 'split.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['sample_id', 'platform', 'group', 'split'])
        for s, rows in sets.items():
            for row, g in zip(rows, group[indices[s]]):
                writer.writerow([row['sample_id'], row['metadata']['platform'], int(g), s])
    reports = {}
    # 對 test、validation、存在時的 challenge 各寫獨立報告，不能平均成一個跨情境成功率。
    for s in [s for s in sets if s!='train']:
        folder = output / s
        folder.mkdir()
        timings = []
        # 先暖機。後續延遲只含 features＋predict_proba，不含 gateway 等待或後端 HTTP。
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
        f'| {s} | {r["accuracy"]:.6f} | {r["macro_f1"]:.6f} |' for s, r in reports.items()) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'output': str(output), 'mode': args.mode, 'exploratory': meta['exploratory'],
                      'metrics': {s: {'accuracy': r['accuracy'], 'macro_f1': r['macro_f1']} for s, r in reports.items()}}, ensure_ascii=False))
