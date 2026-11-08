"""產生可核對的評估證據；高分只適用於這次資料與切分條件。"""
import csv
import json

import numpy as np
from sklearn.metrics import (accuracy_score, average_precision_score, balanced_accuracy_score,
                             classification_report, confusion_matrix, f1_score, roc_auc_score,
                             precision_score, recall_score, matthews_corrcoef, cohen_kappa_score,
                             log_loss, roc_curve, precision_recall_curve)

from features import LABELS


def metrics(y, probabilities):
    """同時計算三類分類與『正常／攻擊』指標，避免只看總準確率。"""
    predicted = probabilities.argmax(axis=1)
    matrix = confusion_matrix(y, predicted, labels=[0, 1, 2])
    normal = y == 0
    attack = ~normal
    result = {
        "accuracy": float(accuracy_score(y, predicted)),
        "balanced_accuracy": float(balanced_accuracy_score(y, predicted)),
        "macro_f1": float(f1_score(y, predicted, labels=[0, 1, 2], average="macro", zero_division=0)),
        'weighted_f1': float(f1_score(y, predicted, labels=[0, 1, 2], average='weighted', zero_division=0)),
        'micro_f1': float(f1_score(y, predicted, labels=[0, 1, 2], average='micro', zero_division=0)),
        'macro_precision': float(precision_score(y, predicted, labels=[0, 1, 2], average='macro', zero_division=0)),
        'macro_recall': float(recall_score(y, predicted, labels=[0, 1, 2], average='macro', zero_division=0)),
        'mcc': float(matthews_corrcoef(y, predicted)),
        'cohen_kappa': float(cohen_kappa_score(y, predicted)) if len(set(y) | set(predicted)) > 1 else None,
        'log_loss': float(log_loss(y, probabilities, labels=[0, 1, 2])),
        'multiclass_brier_score': float(np.mean(np.sum((probabilities - np.eye(3)[y]) ** 2, axis=1))),
        "per_class": classification_report(y, predicted, labels=[0, 1, 2],
                                            target_names=LABELS, output_dict=True, zero_division=0),
        # 列是真實類別、欄是預測類別，順序皆為 normal、sqli、xss。
        "confusion_matrix": matrix.tolist(),
        "normal_false_positive_rate": float(np.mean(predicted[normal] != 0)) if normal.any() else None,
        "attack_detection_recall": float(np.mean(predicted[attack] != 0)) if attack.any() else None,
        "attack_miss_rate": float(np.mean(predicted[attack] == 0)) if attack.any() else None,
    }
    # 分類召回率要求攻擊種類也正確；攻擊偵測召回率只問是否抓到攻擊。
    # 逐類以「該類對其他類」計算曲線面積，不需要挑選測試集門檻。
    result["one_vs_rest"] = {}
    for i, label in enumerate(LABELS):
        tp = int(matrix[i, i]); fn = int(matrix[i].sum() - tp)
        fp = int(matrix[:, i].sum() - tp); tn = int(matrix.sum() - tp - fn - fp)
        result['per_class'][label].update(specificity=tn/(tn+fp) if tn+fp else None,
                                         false_positive_rate=fp/(tn+fp) if tn+fp else None,
                                         false_negative_rate=fn/(tp+fn) if tp+fn else None)
        binary = y == i
        result["one_vs_rest"][label] = {
            "roc_auc": float(roc_auc_score(binary, probabilities[:, i])) if 0 < binary.sum() < len(y) else None,
            "average_precision": float(average_precision_score(binary, probabilities[:, i])) if binary.any() else None,
            "prevalence": float(binary.mean()),
        }
    result['attack_binary_roc_auc'] = float(roc_auc_score(attack, 1-probabilities[:, 0])) if normal.any() and attack.any() else None
    result['attack_binary_average_precision'] = float(average_precision_score(attack, 1-probabilities[:, 0])) if attack.any() else None
    return result


def cluster_interval(y, probabilities, groups, repetitions=1000):
    """以獨立群組重抽樣，避免把同 session 的請求當成互相獨立的證據。

    每次抽取同樣數量的群組（可重複），群組內所有請求一起加入。
    群組太少時不提供看似精確的區間；20 組只是保守的報告門檻，
    不是樣本充足或統計有效性的保證。百分位區間也不是跨平台保證。
    """
    unique = np.unique(groups)
    if len(unique) < 20:
        return {"available": False, "reason": "測試獨立群組少於 20，暫不報信賴區間。",
                "independent_groups": len(unique)}
    rng = np.random.default_rng(42)
    values = []
    predicted = probabilities.argmax(axis=1)
    for _ in range(repetitions):
        indices = np.concatenate([np.flatnonzero(groups == g)
                                  for g in rng.choice(unique, len(unique), replace=True)])
        # 未抽到三類的輪次不拿來估計三類 Macro-F1，並記錄有效輪次。
        if len(set(y[indices])) == 3:
            values.append([accuracy_score(y[indices], predicted[indices]),
                           f1_score(y[indices], predicted[indices], average="macro")])
    if len(values) < repetitions * 0.9:
        return {"available": False, "reason": "太多重抽樣輪次缺少類別，區間不穩定。",
                "valid_repetitions": len(values)}
    low, high = np.percentile(values, [2.5, 97.5], axis=0)
    return {"available": True, "method": "group bootstrap percentile 95%",
            "independent_groups": len(unique), "valid_repetitions": len(values),
            "accuracy": [float(low[0]), float(high[0])],
            "macro_f1": [float(low[1]), float(high[1])]}


def save_evaluation(output, y, probabilities, baseline_probabilities, rows, test_groups, audit):
    """同時保存原始數值、逐筆預測及易讀報告，方便重新計算與檢查錯誤。"""
    report = metrics(y, probabilities)
    report["majority_baseline"] = metrics(y, baseline_probabilities)
    report["confidence_interval"] = cluster_interval(y, probabilities, test_groups)
    report["audit"] = audit
    report['by_platform'] = {}
    for platform in sorted({r['metadata']['platform'] for r in rows}):
        index = np.array([i for i, r in enumerate(rows) if r['metadata']['platform'] == platform])
        report['by_platform'][platform] = metrics(y[index], probabilities[index])
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for normalized in (False, True):
        matrix = np.asarray(report['confusion_matrix'], dtype=float)
        if normalized:
            matrix = np.divide(matrix, matrix.sum(axis=1, keepdims=True), out=np.zeros_like(matrix), where=matrix.sum(axis=1, keepdims=True)!=0)
        name = 'confusion_matrix_normalized.csv' if normalized else 'confusion_matrix.csv'
        with (output / name).open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f); writer.writerow(['actual/predicted', *LABELS])
            for label, counts in zip(LABELS, matrix):
                writer.writerow([label, *map(float if normalized else int, counts)])
    with (output / 'metrics.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f); writer.writerow(['metric', 'value'])
        writer.writerows((key, value) for key, value in report.items() if isinstance(value, (int, float)))
    with (output / 'per-class.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        fields = ['precision', 'recall', 'f1-score', 'support', 'specificity', 'false_positive_rate', 'false_negative_rate']
        writer.writerow(['class', *fields])
        for label in LABELS:
            writer.writerow([label, *[report['per_class'][label][key] for key in fields]])
    with (output / 'curves.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f); writer.writerow(['curve', 'class', 'x', 'y', 'threshold'])
        for i, label in enumerate(LABELS):
            binary = y == i
            if not binary.any() or binary.all():
                continue
            fpr, tpr, thresholds = roc_curve(binary, probabilities[:, i])
            writer.writerows(('ROC', label, float(a), float(b), float(t) if np.isfinite(t) else '') for a,b,t in zip(fpr,tpr,thresholds))
            precision, recall, thresholds = precision_recall_curve(binary, probabilities[:, i])
            writer.writerows(('PR', label, float(r), float(p), float(thresholds[j]) if j<len(thresholds) else '')
                             for j,(r,p) in enumerate(zip(recall,precision)))
    # 不輸出原始請求或憑證，使用樣本 ID 回查來源。
    with (output / "predictions.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["sample_id", "group", "actual", "predicted", *["p_" + x for x in LABELS]])
        for row, group, actual, probability in zip(rows, test_groups, y, probabilities):
            writer.writerow([row.get("sample_id", ""), int(group), LABELS[actual],
                             LABELS[int(probability.argmax())], *map(float, probability)])
    lines = ["# 模型評估", "", "候選試跑：" + str(audit["exploratory"]),
             "", "以下數據只描述指定測試資料；不代表未測平台、未知家族或真實部署效果。", "",
             "| 指標 | XGBoost | 永遠猜訓練集最多類別 |", "|---|---:|---:|"]
    for key in ["accuracy", "balanced_accuracy", "macro_precision", "macro_recall", "macro_f1", 'weighted_f1', 'micro_f1', 'mcc', 'log_loss', 'multiclass_brier_score', "normal_false_positive_rate",
                "attack_detection_recall", "attack_miss_rate"]:
        lines.append(f'| {key} | {report[key]:.4f} | {report["majority_baseline"][key]:.4f} |')
    lines += ["", "## 各類結果", "", "| 類別 | Precision | Recall | F1 | 筆數 |", "|---|---:|---:|---:|---:|"]
    for label in LABELS:
        value = report["per_class"][label]
        lines.append(f'| {label} | {value["precision"]:.4f} | {value["recall"]:.4f} | {value["f1-score"]:.4f} | {int(value["support"])} |')
    lines += ["", "## 混淆矩陣", "", "列＝真實，欄＝預測。", "",
              "| 真實／預測 | normal | sqli | xss |", "|---|---:|---:|---:|"]
    for label, counts in zip(LABELS, report["confusion_matrix"]):
        lines.append("| " + label + " | " + " | ".join(map(str, counts)) + " |")
    lines += ["", "## 資料與可信度", "", "```json", json.dumps({"audit": audit,
              "confidence_interval": report["confidence_interval"]}, ensure_ascii=False, indent=2), "```",
              "", "ROC-AUC、Average Precision 與逐類比例見 report.json；Average Precision 應對照該類比例解讀。",
              "完整逐筆預測見 predictions.csv。沒有實作規則或其他學習器的比較，尚不能宣稱優於它們。"]
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
