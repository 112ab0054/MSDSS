"""明確讀取 train/test/獨立 validation，保留資料分割。"""
import hashlib
import json
import numpy as np


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
        # 來源、家族與正常／攻擊配對都不可跨預定集合。
        family = (meta.get("payload") or {}).get("family")
        if family:
            meta = {**meta, "family_id": family}
        for field in ["session_group", "pair_group", "fingerprint", "near_fingerprint", "template_id", "family_id", "historical_source_report", "source_evidence"]:
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
    from training import run
    run(groups)


if __name__ == "__main__":
    main()
