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
    """同時計算三類分類與『正常／攻擊』指標，避免只看總準確率。

    輸入 y：長度 n 的真實類別編號；probabilities：n×3 的模型機率矩陣。
    輸出：可存成 JSON 的指標字典，不修改模型或重新設定決策門檻。
    所有類別順序固定為 normal、sqli、xss。

    混淆矩陣範例：真實 normal 被預測 sqli，會加在第 0 列、第 1 欄。
    每列總和是該類真實筆數；每欄總和是模型報成該類的筆數。
    TP 是該類答對數；FP 是其他類被報成該類；FN 是該類被報成其他類；其餘為 TN。
    例如 100 筆 normal 中 5 筆被報攻擊，normal_false_positive_rate=5/100=0.05。
    這不同於 SQLi 的 Precision，後者分母是所有被報 SQLi 的請求。

    兩種召回的差別：真實 SQLi 被報成 XSS，SQLi Recall 算漏掉一筆，
    但 attack_detection_recall 仍算抓到攻擊；因此必須同時看三類與二元攻擊指標。
    normal 為類別 0，其他兩類合併為 attack；~normal 是布林反相，不是數值取負。

    Balanced accuracy 是各真實類的 Recall 平均；Macro-F1 是各類 F1 的等權平均。
    Weighted-F1 依 support 加權，資料多的類可能掩蓋少數類表現；Micro-F1 統合所有筆數。
    MCC、Kappa 是補充比較；Log loss 與 Brier 會懲罰對錯誤答案給過高分數，越低越好。
    ROC-AUC/AP 使用連續分數，不代表部署時已選好門檻；AP 應對照 prevalence 解讀。
    遇到無法定義的面積回傳 None；zero_division=0 只是處理分母為零，不是成功證據。
    """
    # y 是 0/1/2 真實類別，probabilities 每列依 LABELS 排列三類分數。
    # 用固定 argmax 評估，沒有事後看測試結果來選一個較漂亮的告警門檻。
    predicted = probabilities.argmax(axis=1)
    matrix = confusion_matrix(y, predicted, labels=[0, 1, 2])
    normal = y == 0
    attack = ~normal
    # Accuracy 看整體答對率；Balanced accuracy 與 Macro 指標讓每類有相同權重。
    # Weighted-F1 依各類筆數加權；單一標籤多類分類的 Micro-F1 通常等於 Accuracy。
    # per_class 同時列各類 Precision（報成該類有多準）、Recall（該類抓到多少）、F1。
    # Precision=TP/(TP+FP)，Recall=TP/(TP+FN)，F1=2×Precision×Recall/(Precision+Recall)。
    # support 是該類真實樣本數；TP/FP/FN 都以「目前這一類對其他類」定義。
    # MCC/Kappa 提供其他整體比較；Log loss/Brier 越低越好，會考慮機率而非只看最大類。
    # zero_division=0 避免未預測到某一類時除零，不表示該類已被正確學會。
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
        # 對網站正常使用特別重要：正常請求被誤判為任一攻擊的比例。
        # 若部署採封鎖策略，這可能導致正常操作被擋；目前 gateway 僅記錄預測。
        "normal_false_positive_rate": float(np.mean(predicted[normal] != 0)) if normal.any() else None,
        "attack_detection_recall": float(np.mean(predicted[attack] != 0)) if attack.any() else None,
        "attack_miss_rate": float(np.mean(predicted[attack] == 0)) if attack.any() else None,
    }
    # 分類召回率要求攻擊種類也正確；攻擊偵測召回率只問是否抓到攻擊。
    # 逐類以「該類對其他類」計算曲線面積，不需要挑選測試集門檻。
    # ROC-AUC 看分數排序；Average Precision 著重 Precision/Recall，需對照該類出現比例。
    # 沒有正例或負例時某些面積無法定義，使用 None 表達，不能當成 0 或 1。
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
    # 合併 SQLi/XSS 成攻擊：1-P(normal) 是攻擊分數。
    # 把 SQLi 誤判 XSS 在三類分類算錯，但在是否偵測到攻擊這一題仍算抓到。
    result['attack_binary_roc_auc'] = float(roc_auc_score(attack, 1-probabilities[:, 0])) if normal.any() and attack.any() else None
    result['attack_binary_average_precision'] = float(average_precision_score(attack, 1-probabilities[:, 0])) if attack.any() else None
    return result


def cluster_interval(y, probabilities, groups, repetitions=1000):
    """以獨立群組重抽樣，避免把同 session 的請求當成互相獨立的證據。

    每次抽取同樣數量的群組（可重複），群組內所有請求一起加入。
    群組太少時不提供看似精確的區間；20 組只是保守的報告門檻，
    不是樣本充足或統計有效性的保證。百分位區間也不是跨平台保證。

    輸入 y/probabilities 對應同一份保留集合；groups 每筆一個關聯群編號。
    repetitions 是重抽樣次數，預設 1000；輸出信賴區間字典或無法提供的理由。

    假設有 20 個群，每輪抽 20 次群編號，可以重複抽同一群。
    抽到某群時，其所有樣本一起加入，讓同 session 內的相似請求維持關聯。
    每輪算 Accuracy/Macro-F1；最後取分數分布的 2.5% 與 97.5% 百分位。
    若獨立群不足 20，或有效含三類的輪次不足 90%，不輸出看似精確的區間。
    這裡的 20 不是充分樣本量證明；區間也不估計未知平台或錯標造成的偏差。
    """
    unique = np.unique(groups)
    if len(unique) < 20:
        return {"available": False, "reason": "測試獨立群組少於 20，暫不報信賴區間。",
                "independent_groups": len(unique)}
    # 固定重抽樣種子便於重現。抽的是完整關聯群組，而不是假設每列獨立。
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
    # 以重抽樣分數的第 2.5 與 97.5 百分位形成 95% 區間。
    # 只反映此測試集合與群組假設下的抽樣變動，不涵蓋標籤錯誤或未來平台變化。
    low, high = np.percentile(values, [2.5, 97.5], axis=0)
    return {"available": True, "method": "group bootstrap percentile 95%",
            "independent_groups": len(unique), "valid_repetitions": len(values),
            "accuracy": [float(low[0]), float(high[0])],
            "macro_f1": [float(low[1]), float(high[1])]}


def save_evaluation(output, y, probabilities, baseline_probabilities, rows, test_groups, audit):
    """同時保存原始數值、逐筆預測及易讀報告，方便重新計算與檢查錯誤。

    輸入 output：已存在的評估目錄；y：真實答案；probabilities：XGBoost 分數；
    baseline_probabilities：基準分數；rows：完整樣本；test_groups：相同順序的群組；audit：實驗資訊。
    所有輸入必須同樣本順序，否則會把某筆的預測對到別筆答案，產生錯誤成績。
    輸出：report 指標字典，同時將可核對的資料寫進 output。

    report.json 保存完整指標、基準、平台分項、區間與實驗資訊；report.md 是可讀版。
    metrics.csv 保存整體數字；per-class.csv 保存各類指標與 support。
    confusion_matrix.csv 保存筆數，normalized 版逐列除以該類真實數。
    curves.csv 保存各類 ROC/PR 點；predictions.csv 保存樣本 ID、真實／預測與三類分數。
    這些檔案方便重算或回查錯誤，而不是只保留一張漂亮的準確率圖片。
    不輸出原始請求或憑證；需要查看某筆內容時，使用 sample_id 回查經遮蔽來源。
    """
    report = metrics(y, probabilities)
    # 基準策略也用完全相同的測試資料和計算方式，避免用不同考題比較。
    report["majority_baseline"] = metrics(y, baseline_probabilities)
    report["confidence_interval"] = cluster_interval(y, probabilities, test_groups)
    report["audit"] = audit
    report['by_platform'] = {}
    # 除整份集合成績，也按平台報告，避免一個平台表現很好掩蓋另一平台失敗。
    for platform in sorted({r['metadata']['platform'] for r in rows}):
        index = np.array([i for i, r in enumerate(rows) if r['metadata']['platform'] == platform])
        report['by_platform'][platform] = metrics(y[index], probabilities[index])
    (output / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    # 原始混淆矩陣是筆數；normalized 逐列除以該真實類別總數。
    # 因此正規化後對角線是各類 Recall，空列維持零，不產生 NaN。
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
    # 匯出 ROC/PR 各點，Notebook 只負責畫圖，不重新訓練或挑門檻。
    # ROC 的 x/y 是 FPR/TPR；PR 的 x/y 是 Recall/Precision。
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
