"""Package only required code, three CSVs, header schema and optional public evidence."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile
from header_contracts import documented_headers
from data_io import read_rows, check_evidence

HERE = Path(__file__).resolve().parent


def package(data_dir, output, evidence_root=None):
    if output.exists():
        raise ValueError('套件已存在，請使用新的輸出檔名')
    files = {}
    for name in ('train.py', 'training.py', 'preflight.py', 'data_io.py', 'evaluate.py', 'features.py',
                 'request_input.py', 'predict.py', 'requirements.txt'):
        files['model/' + name] = (HERE / name).read_bytes()
    names, hashes = documented_headers()
    files['model/header-schema.json'] = json.dumps({'header_names': names, 'document_sha256': hashes}, indent=2).encode()
    splits=['train','test','validation']
    if (data_dir/'challenge.csv').is_file():splits.append('challenge')
    for split in splits:
        source = data_dir / (split + '.csv')
        files['data/' + source.name] = source.read_bytes()
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
    for name in ('field-coverage.csv','external-payloads.csv','HTTPPARAMS-LICENSE.txt','README.md'):
        if (data_dir/name).is_file():files['data/'+name]=(data_dir/name).read_bytes()
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
