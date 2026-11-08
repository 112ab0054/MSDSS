"""使用兩個平台訓練，將另一個平台保留為最終測試集。"""
import argparse
import csv
import hashlib
import json
import platform
import time
import importlib.metadata
from pathlib import Path

import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import GroupShuffleSplit
from xgboost import XGBClassifier

from features import LABELS, VERSION, features
from evaluate import save_evaluation


def groups(rows):
    """把有關聯的請求綁在一起，避免相似資料同時出現在練習與考試中。

    session_group：同一次使用流程；pair_group：攻擊與正常對照配對；
    fingerprint／near_fingerprint：來源標記的完全／近似重複。
    這裡沿用來源的近似判定，並非自動辨識所有換寫模板；仍須人工核查。
    空值不建立關聯，否則所有缺少分組資訊的資料可能被錯綁成一大群。
    """
    parent = list(range(len(rows)))
    seen = {}

    # 用合併群組的方式保留間接關聯：A 連到 B、B 連到 C，三者都同組。
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, row in enumerate(rows):
        meta = row["metadata"]
        # 刻意不以 family_id 綁定：此實驗允許跨平台出現相同攻擊家族。
        for field in ["session_group", "pair_group", "fingerprint", "near_fingerprint", "template_id"]:
            value = meta.get(field)
            if value:
                key = (field, value)
                if key in seen:
                    parent[root(i)] = root(seen[key])
                seen[key] = i
        # 即使來源沒有提供指紋，也用排序後的完整請求內容找完全重複。
        canonical = json.dumps(row["input"], sort_keys=True, ensure_ascii=False)
        key = ("request", hashlib.sha256(canonical.encode()).hexdigest())
        if key in seen:
            parent[root(i)] = root(seen[key])
        seen[key] = i
    return np.array([root(i) for i in range(len(rows))])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path, help="Exported CSV containing 完整紀錄JSON")
    parser.add_argument("--test-platform", default="sylius",
                        choices=["bagisto", "shopware", "sylius"])
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "artifacts")
    parser.add_argument("--allow-candidates", action="store_true", help="Exploratory run only")
    args = parser.parse_args()
    # 每次實驗使用新目錄，避免新的結果覆蓋先前的失敗或低分紀錄。
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        raise SystemExit("輸出目錄已有檔案；請用 --output 指定新的實驗目錄。")
    # utf-8-sig 同時相容一般 UTF-8 與含 BOM 的 CSV。
    if args.data.suffix.lower() == ".csv":
        with args.data.open(encoding="utf-8-sig", newline="") as f:
            rows = [json.loads(r["完整紀錄JSON"]) for r in csv.DictReader(f)]
    else:
        rows = [json.loads(line) for line in args.data.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    # 正式審核工具輸出的 JSONL 直接可訓練，不需要人工改候選標記。
    for row in rows:
        if "audit" in row and "label" in row:
            audit = row["audit"]
            row["metadata"] = dict(audit["metadata"])
            row["metadata"]["training_approved"] = audit.get("review_status") == "approved"
            row["annotation"] = {"label": row["label"]}
    # 正式模式只接受人工核准資料；候選模式僅用來檢查流程。
    # 採集計畫不是請求證據，即使候選試跑也不能混入未送出的模板。
    if any(r["metadata"].get("http_executed") is False for r in rows):
        raise SystemExit("包含未送出的採集計畫；請先實機採集與審核，不能直接訓練。")
    loaded_count = len(rows)
    if not args.allow_candidates:
        rows = [r for r in rows if r["metadata"].get("training_approved") is True]
    if not rows:
        raise SystemExit("沒有核准樣本；請先人工審核。試跑可加 --allow-candidates。")
    if not args.allow_candidates and any(r["metadata"].get("request_input_version") != 2 for r in rows):
        raise SystemExit("正式訓練要求完整請求輸入 v2；請先從原始證據重新匯出並審核。")
    # 沒有 session ID 就無法確認流程隔離，拒絕把它當獨立樣本。
    if any(not r["metadata"].get("session_group") for r in rows):
        raise SystemExit("部分樣本缺少 session_group，請先補齊分組資訊。")
    labels = [r["annotation"].get("label", r["annotation"].get("proposed_label")) for r in rows]
    if any(label not in LABELS for label in labels):
        raise SystemExit("標籤必須為 normal、sqli、xss。")
    # 特徵只來自請求；標籤順序固定為 normal、sqli、xss。
    x = np.array([features(r["input"]) for r in rows], dtype=np.float32)
    y = np.array([LABELS.index(label) for label in labels])
    group = groups(rows)
    test = np.array([i for i, r in enumerate(rows)
                     if r["metadata"]["platform"] == args.test_platform], dtype=int)
    # 測試平台整批保留；其他平台若與測試群組有關聯，就從訓練側排除。
    test_groups = set(group[test])
    pool = np.array([i for i, r in enumerate(rows)
                     if r["metadata"]["platform"] != args.test_platform
                     and group[i] not in test_groups], dtype=int)

    def counts(indices):
        return {label: int(sum(y[indices] == i)) for i, label in enumerate(LABELS)}

    def complete(indices):
        return set(y[indices]) == {0, 1, 2}

    print("training pool:", counts(pool), "test:", counts(test))
    if not complete(pool) or not complete(test) or len(set(group[pool])) < 2:
        raise SystemExit("獨立分組後缺少三類或足夠群組；請補採資料，不能隨機拆列。")
    # 僅從訓練平台找出含三類的分組驗證集；固定種子確保可重現。
    splitter = GroupShuffleSplit(n_splits=100, test_size=0.2, random_state=42)
    for a, b in splitter.split(x[pool], y[pool], group[pool]):
        train, valid = pool[a], pool[b]
        if complete(train) and complete(valid):
            break
    else:
        raise SystemExit("無法建立含三類的獨立 validation；請補採獨立 session。")
    print("train:", counts(train), "validation:", counts(valid))
    # 最多建立 300 棵樹；驗證損失連續 20 輪未改善即提早停止。
    model = XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.05,
                          objective="multi:softprob", num_class=3, eval_metric="mlogloss",
                          early_stopping_rounds=20, n_jobs=2, random_state=42)
    training_started = time.perf_counter()
    model.fit(x[train], y[train], eval_set=[(x[valid], y[valid])], verbose=False)
    training_seconds = time.perf_counter() - training_started
    # 先固定模型，再對保留平台評分；絕不使用測試結果選樹數或門檻。
    probabilities = model.predict_proba(x[test])
    # 最低比較基準：只從訓練集找出最多的類別，之後永遠猜該類。
    # 超過此基準只是基本要求，不足以證明比規則式或其他模型更好。
    baseline = DummyClassifier(strategy="most_frequent").fit(x[train], y[train])
    baseline_probabilities = baseline.predict_proba(x[test])
    output.mkdir(parents=True, exist_ok=True)
    # 模型 JSON 不保存訓練資料路徑；套件版本則另記錄，方便跨系統重建。
    model.save_model(output / "model.json")
    metadata = {"feature_version": VERSION, "labels": LABELS,
                "exploratory": args.allow_candidates, "test_platform": args.test_platform}
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    splits = {"train": train, "validation": valid, "test": test}
    # 明確驗證三個集合沒有群組交集，而不是只相信切分函式。
    for left, right in [(train, valid), (train, test), (valid, test)]:
        if set(group[left]) & set(group[right]):
            raise RuntimeError("偵測到跨集合群組重疊，停止評估。")
    # 即使請求指紋不同，簡化後的模型特徵仍可能一樣；如實揭露，不當成已隔離。
    feature_sets = {name: {tuple(v) for v in x[indices]} for name, indices in splits.items()}
    feature_overlap = {f"{a}/{b}": len(feature_sets[a] & feature_sets[b])
                       for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")]}
    # 預先暖機後逐筆計時，包含特徵擷取與預測；不含網路、檔案讀取與模型載入。
    # 這是本機量測，Windows 或 Linux 正式部署機器仍須另外測試。
    timings = []
    model.predict_proba([features(rows[test[0]]["input"])])
    for index in test:
        started = time.perf_counter()
        model.predict_proba([features(rows[index]["input"])])
        timings.append((time.perf_counter() - started) * 1000)
    audit = {
        **metadata, "loaded_rows": loaded_count, "eligible_rows": len(rows),
        "excluded_training_rows_linked_to_test": len(rows) - len(test) - len(pool),
        "counts": {name: counts(indices) for name, indices in splits.items()},
        "independent_groups": {name: len(set(group[indices])) for name, indices in splits.items()},
        "group_overlap": 0, "identical_feature_vectors_shared": feature_overlap,
        "seed": 42, "best_iteration": model.best_iteration,
        "training_seconds": training_seconds,
        "latency_ms": {"median": float(np.median(timings)), "p95": float(np.percentile(timings, 95))},
        "data_sha256": hashlib.sha256(args.data.read_bytes()).hexdigest(),
        "source_sha256": {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                          for name in ["features.py", "train.py", "evaluate.py"]},
        "python": platform.python_version(),
        "packages": {name: importlib.metadata.version(name) for name in ["numpy", "scikit-learn", "xgboost"]},
        "model_parameters": model.get_params(),
    }
    # 記錄每筆資料被分到哪裡，之後可查核，不能偷偷換一份較好看的測試集。
    assignment = {int(index): name for name, indices in splits.items() for index in indices}
    with (output / "split.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["row_index", "sample_id", "platform", "group", "split"])
        for i, row in enumerate(rows):
            writer.writerow([i, row.get("sample_id", ""), row["metadata"]["platform"],
                             int(group[i]), assignment.get(i, "excluded_linked_to_test")])
    report = save_evaluation(output, y[test], probabilities, baseline_probabilities,
                             [rows[i] for i in test], group[test], audit)
    print("test accuracy:", round(report["accuracy"], 4))
    print("test Macro-F1:", round(report["macro_f1"], 4))
    print("saved:", output)


if __name__ == "__main__":
    main()
