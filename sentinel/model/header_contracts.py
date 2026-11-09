"""從三平台 API 文件取得具名 header 槽位，供打包與預設特徵規格使用。

只讀文件的 header 名稱，不生成 HTTP 請求，也不推測憑證值。
已訓練模型的推論以 metadata 保存的清單為準，不應臨時套用修改後的文件順序。
"""
import hashlib
from pathlib import Path


def documented_headers():
    # 依本程式位置找專案根目錄，不要求使用者從固定工作目錄啟動。
    # sources 保存文件相對路徑與 SHA，搬到另一台機器仍能依相對結構核對。
    """輸入：無，依程式位置讀三平台的 API_parameters.md。
    輸出二元組 (names, sources)：names 為小寫去重排序的名稱 list，sources 為文件路徑到 SHA 的 dict。
    例如同一個 Accept 出現在 10 個 API，只會有一個 accept 具名槽位。
    這裡只決定槽位名稱，不代表每筆請求都必須帶所有 header。
    固定槽位讓 x-locale 永遠出現在同一段向量，不能某次放第 80 格、下次放第 97 格。
    若文件不存在或根本沒有可讀 header 列，會拋錯，不退回只分析 Content-Type。
    """
    root = Path(__file__).resolve().parents[2]
    names, sources = set(), {}
    for platform in ('bagisto', 'shopware', 'sylius'):
        path = root / f'sentinel/analysis/selected-api-contracts/{platform}/API_parameters.md'
        # 文件指紋統一換行，避免 Git 在 Windows checkout CRLF 後誤判來源變更。
        # 這只處理 API 說明文件，不修改任何請求輸入。
        raw = path.read_bytes().replace(b'\r\n', b'\n')
        sources[path.relative_to(root).as_posix()] = hashlib.sha256(raw).hexdigest()
        # 文件使用固定 Markdown 表格格式，僅取 location=header 的列。
        # 名稱依 HTTP 規則轉小寫、集合去重，最終排序後形成固定槽位。
        for line in raw.decode('utf-8-sig').splitlines():
            if line.startswith('| header |'):
                names.add(line.split('|')[2].strip().lower())
    if not names: raise ValueError('三份 API 文件沒有可讀取的 header 定義')
    return sorted(names), sources
