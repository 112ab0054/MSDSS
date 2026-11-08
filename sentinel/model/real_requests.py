"""從既有 HTTP 證據重新匯出完整請求，並核對全部文件參數；不生成請求。"""
import argparse
import copy
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sentinel/dataset"))
from core import model_input, sha, verify_evidence, evidence_digest_mode



def read_rows(path):
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as f:
            return [json.loads(row["完整紀錄JSON"]) for row in csv.DictReader(f)]
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def refresh(rows):
    """只能取回證據檔確實保存的欄位，不推測瀏覽器當時送了什麼。

    更換前處理代表新候選，先前審核不能自動移植；原始證據不修改。
    """
    output = []
    for original in rows:
        if not verify_evidence(original):
            raise ValueError("來源證據對帳失敗，停止重新匯出：" + original.get("sample_id", ""))
        row = copy.deepcopy(original)
        meta = row["metadata"]
        source_bytes = (ROOT / meta["source_evidence"]).read_bytes()
        source = json.loads(source_bytes)
        meta["source_observed_sha256"] = sha(source_bytes)
        meta["source_digest_mode"] = evidence_digest_mode(source_bytes, meta["source_evidence_sha256"])
        request = next(r for r in source["requests"] if r.get("request_id") == meta["request_id"])
        row["input"] = model_input(request, version=2)
        meta.update({"request_input_version": 2, "training_approved": False,
                     "previous_sample_id": original["sample_id"],
                     "fingerprint": sha(row["input"]), "near_fingerprint": None,
                     "header_capture": request.get("header_capture", "historical_explicit_headers_only")})
        row["sample_id"] = sha([original["sample_id"], "request-input-v2"])
        row["annotation"].update(review_status="pending_human_review", eligible_for_review=True)
        row["annotation"].pop("label", None)
        output.append(row)
    return output


def flatten(value, prefix=""):
    """展開所有實際欄位（含巢狀與陣列），不列白名單挑選特定名稱。"""
    if isinstance(value, dict):
        for key, child in value.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            yield name, child
            yield from flatten(child, name)
    elif isinstance(value, list):
        for child in value:
            yield from flatten(child, prefix + "[]")


def documentation():
    """直接讀 62 操作人工參數表，包含 header/query/path/body。"""
    result = {}
    for platform in ["bagisto", "shopware", "sylius"]:
        path = ROOT / f"sentinel/analysis/selected-api-contracts/{platform}/API_parameters.md"
        current, body = None, False
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("### 既有"):
                current = None  # 文末補充不誤歸到最後一個 API。
            match = re.fullmatch(r"`(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) ([^`]+)`", line.strip())
            if match:
                current = (platform, *match.groups())
                result.setdefault(current, {})
                body = False
            if line.startswith("### "):
                body = False
            if line.startswith("| 本文字段 |"):
                body = True
                continue
            if not current or not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells[0] in {"header", "query", "path"} and len(cells) >= 5:
                location, name, required, kind, values = cells[:5]
            elif body and len(cells) >= 4 and cells[0] and not cells[0].startswith("-"):
                location, name, required, kind, values = "body", *cells[:4]
            else:
                continue
            if location == "header":
                name = name.lower()
            result[current][location, name.strip('`')] = {"required": required, "type": kind, "values": values}
    return result


def coverage(rows):
    """報告『實際有採到』與『文件有但缺資料』，不把產生計畫當覆蓋。"""
    manifest = json.loads((ROOT / "sentinel/analysis/api-extension/active-api-manifest.json").read_text())
    docs = documentation()
    records = []
    for operation in manifest["operations"]:
        key = operation["platform"], operation["method"], operation["path"]
        samples = [row for row in rows if (row["metadata"]["platform"], row["input"]["method"], row["input"]["path"]) == key]
        fields = dict(docs.get(key, {}))
        actual = []
        for row in samples:
            observed = {}
            for location, source in [("header", "headers"), ("query", "query"),
                                     ("body", "body"), ("path", "path_parameters")]:
                for name, value in flatten(row["input"].get(source)):
                    observed[location, name.lower() if location == "header" else name] = value
            actual.append(observed)
            for field in observed:
                fields.setdefault(field, {"required": "文件未列", "type": "實際觀測", "values": ""})
        for (location, name), description in sorted(fields.items()):
            present = [observed[location, name] for observed in actual if (location, name) in observed]
            records.append({"平台": key[0], "方法": key[1], "API": key[2], "位置": location, "參數": name,
                            "文件列出": (location, name) in docs.get(key, {}), "必填": description["required"],
                            "型別": description["type"], "文件值與限制": description["values"],
                            "實測請求數": len(samples), "存在筆數": len(present), "省略筆數": len(samples) - len(present),
                            "不同觀測值數": len({sha(value) for value in present}),
                            "狀態": "有觀測（不等於值域／邊界完整）" if present else "尚缺實測資料"})
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("data", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--audit-only", action="store_true", help="只核對既有欄位，來源未通過也不匯出訓練候選")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("輸出目錄已存在；請另選新目錄。")
    originals = read_rows(args.data)
    checks = [{"sample_id": row["sample_id"], "source_verified": verify_evidence(row)} for row in originals]
    rows = originals if args.audit_only else refresh(originals)
    table = coverage(rows)
    for record in table:
        record["證據檢查模式"] = "只讀欄位稽核，不代表來源通過" if args.audit_only else "來源 SHA 與請求對帳通過"
    args.output.mkdir(parents=True)
    if not args.audit_only:
        write_candidates(args.output / "candidates.csv", rows)
    (args.output / "evidence-checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
    with (args.output / "parameter-coverage.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    print(json.dumps({"source_verified": sum(x["source_verified"] for x in checks), "inspected_rows": len(rows),
                      "new_requests": 0, "exported_candidates": 0 if args.audit_only else len(rows),
                      "parameter_coverage_rows": len(table), "human_approved": 0}))


def write_candidates(path, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["完整紀錄JSON"])
        writer.writeheader()
        writer.writerows({"完整紀錄JSON": json.dumps(row, ensure_ascii=False)} for row in rows)


if __name__ == "__main__":
    main()
