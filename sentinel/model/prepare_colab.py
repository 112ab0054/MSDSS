"""打包當前訓練程式、骨架分組 v4 集合、可選 challenge、來源說明及遮蔽證據供 Colab 使用。"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile
from header_contracts import documented_headers
from data_io import read_rows, check_evidence

HERE = Path(__file__).resolve().parent


def package(data_dir, output, evidence_root=None):
    """輸入 data_dir：要上傳的三集合資料夾；output：新的 ZIP 檔名；evidence_root：可選的證據根目錄。
    輸出摘要字典，包含輸出位置、檔案數與是否有指定證據根目錄。
    不回傳已訓練模型，因為這一步只是準備 Colab 輸入。

    ZIP 的 model/ 放必要 .py 與 requirements，data/ 放三份 CSV 和可選 provenance。
    evidence/ 保留來源路徑，例如 evidence/sentinel/dataset/evidence/run-0.json。
    這樣 Notebook 傳 --evidence-root 到 evidence/，就能接上 metadata 中的相對路徑。
    package-manifest.json 逐檔記錄 bytes 的 SHA，供解壓後核對。

    指定 evidence_root 會核對有來源的每筆記錄；沒有 source_evidence 的列在這裡略過。
    因此打包成功不等於正式資格通過，Notebook 的 --check-only 仍可能拒絕未送出資料。
    此函式不掃描整個專案、不攜帶 .env，也不把人工審核加入條件。

    新版若有 challenge.csv 也一併打入 data/，Notebook 可用同一模型獨立評估它。
    skeleton-catalog.csv、field-coverage.csv、external-payloads.csv、HTTPPARAMS-LICENSE.txt、README.md 存在時保留，
    分別提供欄位覆蓋、外部攻擊來源、授權與資料限制，不把它們當成模型特徵。
    執行時收進當前 .py；本次重註解後應重新打包，舊 dataset.zip 內程式不會自動更新。
    """
    if output.exists():
        raise ValueError('套件已存在，請使用新的輸出檔名')
    # key 是 ZIP 內相對路徑，value 是 bytes；只列必要檔案，不遞迴打包私有設定或虛擬環境。
    files = {}
    for name in ('train.py', 'training.py', 'preflight.py', 'data_io.py', 'evaluate.py', 'features.py',
                 'request_input.py', 'skeletons.py', '_skeleton_html_v1.py', '_skeleton_markupbase_v1.py',
                 'SKELETON-PYTHON-LICENSE.txt', 'predict.py', 'requirements.txt'):
        files['model/' + name] = (HERE / name).read_bytes()
    names, hashes = documented_headers()
    files['model/header-schema.json'] = json.dumps({'header_names': names, 'document_sha256': hashes}, indent=2).encode()
    splits=['train','test','validation']
    # 新版可選 challenge 一起帶到 Colab，保留其獨立評估用途。
    if (data_dir/'challenge.csv').is_file():splits.append('challenge')
    for split in splits:
        source = data_dir / (split + '.csv')
        files['data/' + source.name] = source.read_bytes()
        # 有指定根目錄就先 check_evidence，再收對應的遮蔽檔；缺來源的列仍由訓練前檢查判定。
        if evidence_root:
            for row in read_rows(source):
                if not row['metadata'].get('source_evidence'):
                    continue
                check_evidence(row, evidence_root)
                relative = PurePosixPath(row['metadata']['source_evidence'].replace('\\', '/'))
                files['evidence/' + str(relative)] = evidence_root.joinpath(*relative.parts).read_bytes()
    provenance = data_dir / 'provenance.json'
    if provenance.is_file():
        files['data/provenance.json'] = provenance.read_bytes()
    for name in ('augmentation-bindings.csv','candidate-decisions.csv','parser-compatibility.json','skeleton-catalog.csv','field-coverage.csv','external-payloads.csv','HTTPPARAMS-LICENSE.txt','README.md'):
        if (data_dir/name).is_file():files['data/'+name]=(data_dir/name).read_bytes()
    # 外層清單核對上傳檔案；不同於訓練後 inference/ 的 bundle-manifest.json。
    files['package-manifest.json'] = json.dumps({n: hashlib.sha256(b).hexdigest() for n,b in files.items()}, indent=2).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, raw in sorted(files.items()):
            z.writestr(name, raw)
    return {'output': str(output), 'files': len(files), 'includes_evidence': evidence_root is not None}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-dir', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--evidence-root', type=Path)
    args = p.parse_args()
    print(json.dumps(package(args.data_dir, args.output, args.evidence_root), ensure_ascii=False))
