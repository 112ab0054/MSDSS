"""Load the explicit 64-operation manifest, including separate corrected files.

This does not install an inference service or alter the original contracts.
"""
import hashlib
import json
from pathlib import Path

from api_extension_schema import clean, refs, resolve

ROOT = Path(__file__).resolve().parents[2]


def load_active_contracts():
    manifest = json.loads((ROOT / "sentinel/analysis/api-extension/active-api-manifest.json").read_text(encoding="utf-8"))
    sources, operations = {}, {}
    for entry in manifest["operations"]:
        source_path = entry["source_contract"]
        if source_path not in sources:
            raw = (ROOT / source_path).read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry["source_sha256"]:
                raise ValueError(f"Source changed; review required: {source_path}")
            sources[source_path] = json.loads(raw)
        source = sources[source_path]
        fragment = json.loads((ROOT / entry["contract_file"]).read_text(encoding="utf-8"))
        key = entry["platform"], entry["method"], entry["path"]
        if key in operations or (fragment["method"], fragment["path"]) != key[1:]:
            raise ValueError(f"Duplicate or mismatched selected operation: {key}")
        expected = source["paths"][entry["path"]][entry["method"].lower()]
        operation = clean(fragment["operation"])
        if operation != clean(expected):
            raise ValueError(f"Selected operation differs from source: {key}")
        effective = operation.get("security", source.get("security", []))
        if effective != entry["effective_security"]:
            raise ValueError(f"Authentication requirements differ: {key}")
        for requirement in effective:
            if not all(isinstance(scopes, list) for scopes in requirement.values()):
                raise ValueError(f"Invalid authentication scope arrays: {key}")
        for ref in refs(operation):
            resolve(source, ref)
        operations[key] = {"operation": operation, "source_document": source, "effective_security": effective,
                           "contract_file": entry["contract_file"], "role": entry["role"]}
    return operations


if __name__ == "__main__":
    operations = load_active_contracts()
    print(json.dumps({"operations": len(operations), "runtime_platform_tests": "not_run"}))
