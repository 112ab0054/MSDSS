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

    輸入 rows：完整樣本的清單，每筆包含 input（請求）與 metadata（來源關聯）。
    輸出：長度等於 len(rows) 的 NumPy 整數陣列；相同整數代表屬於同一關聯群。
    例如三筆的 session 分別為 A、A、B，若沒有其他關聯，結果可能為 [0, 0, 2]。
    實際代表數字取決於合併順序，只能用來判斷是否同群，不能當永久識別碼。

    變數 parent[i]：第 i 筆目前指向哪個群組代表；初始每筆指向自己。
    變數 seen：記錄某個「欄位種類＋欄位值」上一次出現在哪筆。
    例如 ('session_group', 'A') 和 ('family_id', 'A') 是不同關聯，不會因字串一樣就合併。

    處理流程：逐筆檢查關聯 → 找到已看過的值就合併群 → 再比對完整請求的雜湊。
    若第 1 筆與第 2 筆同 session，第 2 筆與第 3 筆同 family，三筆會間接合併。
    這樣 preflight 能阻止同群資料落入不同集合，不會只檢查相鄰兩筆。
    SHA-256 比對只找完全相同的 input；改一個非敏感值就可能不同，不能取代近似去重。

    新版 v3 規則（evaluation_protocol=document-v3-seen-families-heldout-templates）：
    這類樣本不使用 family_id 合併，因為一般 test 刻意考「見過家族、沒見過模板」。
    source_template_group、pair_group、session、完全重複等關聯仍保留，不能靠換 session 洗掉模板交集。
    例如 train 與 test 同為 union 家族可被允許，但同來源模板不能同時出現在兩份集合。
    未知家族另放 challenge；家族集合與攻擊原文的限制由 preflight 另行檢查。
    上文的間接合併例子適用於有啟用的分組欄位；此 v3 規則下 family_id 不參與合併。
    """
    # parent[i] 初始指自己，每列先成一群；seen 記錄每種關聯值上次出現位置。
    parent = list(range(len(rows)))
    seen = {}

    # 用合併群組的方式保留間接關聯：A 連到 B、B 連到 C，三者都同組。
    def root(i):
        """輸入 i：某筆資料在 rows 裡的位置；輸出：它目前的最終群組代表位置。
        while 沿著 parent 一直走，直到某個位置的 parent 指回自己。
        parent[i] = parent[parent[i]] 是路徑壓縮，讓之後查同一群時不用重走整條鏈。
        本函式只更新分組索引，不修改任何 HTTP 請求、標籤或原 CSV。
        """
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, row in enumerate(rows):
        meta = row["metadata"]
        # 先讀來源與家族資訊，再依該列的實驗協議決定哪些關聯要合併。
        family = (meta.get("payload") or {}).get("family")
        if family:
            meta = {**meta, "family_id": family}
        fields=["session_group", "pair_group", "fingerprint", "near_fingerprint", "template_id", "family_id", "historical_source_report", "source_evidence", "source_template_group"]
        if meta.get('evaluation_protocol') == 'document-v3-seen-families-heldout-templates':
            # v3 一般 test 是已見家族的新模板，所以只解除 family_id，其他來源／模板／session 關聯仍保留。
            fields.remove('family_id')  # 已見家族實驗仍保留模板與 session 分組。
        # 比較 (欄位名, 值)，避免 session A 和 family A 只是字串一樣就誤合併。
        for field in fields:
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
    """命令列入口。此函式不直接讀 CSV 或呼叫 XGBoost。
    它把 groups 這個函式本身交給 training.run，由主流程在檢查資料時呼叫。
    底下的 __name__ 判斷讓 import train 時不會意外開始訓練。
    """
    from training import run
    run(groups)


if __name__ == "__main__":
    main()
