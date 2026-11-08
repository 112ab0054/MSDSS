"""Header feature vocabulary comes from the three maintained API documents."""
import hashlib
from pathlib import Path


def documented_headers():
    root = Path(__file__).resolve().parents[2]
    names, sources = set(), {}
    for platform in ('bagisto', 'shopware', 'sylius'):
        path = root / f'sentinel/analysis/selected-api-contracts/{platform}/API_parameters.md'
        # 文件指紋統一換行，避免 Git 在 Windows checkout CRLF 後誤判來源變更。
        # 這只處理 API 說明文件，不修改任何請求輸入。
        raw = path.read_bytes().replace(b'\r\n', b'\n')
        sources[path.relative_to(root).as_posix()] = hashlib.sha256(raw).hexdigest()
        for line in raw.decode('utf-8-sig').splitlines():
            if line.startswith('| header |'):
                names.add(line.split('|')[2].strip().lower())
    if not names: raise ValueError('三份 API 文件沒有可讀取的 header 定義')
    return sorted(names), sources
