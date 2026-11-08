"""依現行 API 文件與歷史正常基底產生 header 候選；不發送 HTTP。"""
import argparse
import copy
import csv
import hashlib
import json
import itertools
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "sentinel/scripts"))
from active_api_contracts import load_active_contracts
from api_extension_schema import resolve
from features import SENSITIVE

# 僅產生非破壞性候選；沒有資料外送、讀取資料表或延遲操作。
# 字串代表攻擊意圖，不代表端點有漏洞或瀏覽器會執行。
CASES = [("sqli", "sql.boolean", "' OR 'a'='a' --"),
         ("sqli", "sql.union", "' UNION SELECT NULL --"),
         ("xss", "xss.script", "<script>void(0)</script>"),
         ("xss", "xss.event", '<svg onload="void(0)"></svg>')]


def digest(value):
    raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def dereference(value, document):
    while "$ref" in value:
        value = resolve(document, value["$ref"])
    return value


def header_parameters(fragment, document):
    """合併路徑層及操作層參數；操作層同名參數覆蓋路徑層。"""
    path = fragment["path"]
    combined = document["paths"][path].get("parameters", []) + fragment["operation"].get("parameters", [])
    result = {}
    for parameter in combined:
        parameter = dereference(parameter, document)
        if parameter.get("in") == "header":
            result[parameter["name"].lower()] = parameter
    return result


def documented_headers(path):
    """直接讀人工參數表，避免漏掉未列在 parameters 的認證 header。"""
    operations, current = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"`(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) ([^`]+)`", line.strip())
        if match:
            current = match.groups()
            operations.setdefault(current, {})
        if current and line.startswith("| header |"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            name, required = cells[1], cells[2]
            operations[current][name.lower()] = {
                "name": name, "required_text": required,
                "required": required == "必填", "conditional": "認證組合" in required,
                "type_text": cells[3], "value_text": cells[4]}
    return operations


def values_for(name, parameter, documented, document, existing):
    """保留文件全部 enum／例值；動態值明列待綁定，絕不杜撰有效 ID。"""
    schema = dereference(parameter.get("schema", {}), document)
    values = list(schema.get("enum", []))
    for value in [parameter.get("example"), schema.get("example"), schema.get("default"), existing]:
        if value is not None and value != "" and value not in values:
            values.append(value)
    # 人工文件的固定值也必須涵蓋，不只取 enum 第一個值。
    description = documented.get("value_text", "")
    if "固定值：" in description:
        for value in re.findall(r"`([^`]+)`", description):
            if value not in values:
                values.append(value)
    if SENSITIVE.search(name):
        return ["${LIVE:" + name + "}"]
    return [str(value) for value in values] or ["${LIVE:" + name + "}"]


def generate(reference):
    """所有採用 API 都建立計畫；缺基底／動態值保留為明確的執行前置條件。"""
    contracts = load_active_contracts()
    with reference.open(encoding="utf-8-sig", newline="") as f:
        originals = [json.loads(row["完整紀錄JSON"]) for row in csv.DictReader(f)]
    bases = {}
    for row in originals:
        request, meta = row["input"], row["metadata"]
        if row["annotation"].get("proposed_label") == "normal":
            bases.setdefault((meta["platform"], request["method"], request["path"]), row)
    documents = {platform: ROOT / f"sentinel/analysis/selected-api-contracts/{platform}/API_parameters.md"
                 for platform in {key[0] for key in contracts}}
    tables = {platform: documented_headers(path) for platform, path in documents.items()}
    candidates, coverage = [], []
    for key, contract in sorted(contracts.items()):
        platform, method, path = key
        original = bases.get(key)
        fragment_path = ROOT / contract["contract_file"]
        fragment = json.loads(fragment_path.read_text(encoding="utf-8"))
        document = contract["source_document"]
        params = header_parameters(fragment, document)
        table = tables[platform].get((method, path), {})
        # 人工文件是要求的覆蓋來源；與機器契約取聯集，差異在清單中揭露。
        names = sorted(set(params) | set(table))
        specs = {}
        existing = {k.lower(): v for k, v in (original or {}).get("input", {}).get("headers", {}).items()}
        for name in names:
            declared = table.get(name, {})
            parameter = params.get(name, {})
            specs[name] = {"required": declared.get("required", parameter.get("required", False)),
                "conditional": declared.get("conditional", False),
                "sensitive": bool(SENSITIVE.search(name)),
                "in_manual_document": name in table, "in_contract_parameters": name in params,
                "values": values_for(name, parameter, declared, document, existing.get(name))}
        mandatory = [name for name in names if specs[name]["required"] or specs[name]["conditional"]]
        optional = [name for name in names if name not in mandatory]
        base = copy.deepcopy(original["input"]) if original else {
            "method": method, "path": path, "query": {}, "body": None, "headers": {}}
        # 舊基底中不屬於文件的 Accept/Content-Type 保留；敏感舊值不保存。
        base["headers"] = {k.lower(): str(v) for k, v in base.get("headers", {}).items()
                           if not SENSITIVE.search(k) and k.lower() not in names}
        detail = {"platform": platform, "method": method, "path": path,
                  "has_historical_base": original is not None, "headers": specs,
                  "optional_headers": optional, "presence_combinations": 2 ** len(optional),
                  "generated": 0, "skipped": []}
        coverage.append(detail)

        def emit(headers, kind, target="", label="normal", family=None):
            request = copy.deepcopy(base)
            request["headers"].update(headers)
            template = digest([kind, sorted(headers), target, family,
                               headers.get(target) if family else None])
            # 沿用實際基底 session，所有變體不能拆開湊訓練／測試。
            session = (original or {}).get("metadata", {}).get("session_group", "planned:" + digest(key))
            meta = {"platform": platform, "origin": "generated_api_header_plan",
                    "session_group": session, "pair_group": digest([key, sorted(headers)]),
                    "family_id": family, "template_id": template,
                    "scenario_kind": kind, "target_location": "header", "target_parameter": target,
                    "present_documented_headers": sorted(headers),
                    "absent_documented_headers": sorted(set(names) - set(headers)),
                    "contract_file": contract["contract_file"], "contract_sha256": digest(fragment_path.read_bytes()),
                    "parameter_document": documents[platform].relative_to(ROOT).as_posix(),
                    "parameter_document_sha256": digest(documents[platform].read_bytes()),
                    "base_sample_id": (original or {}).get("sample_id"),
                    "base_source_evidence": (original or {}).get("metadata", {}).get("source_evidence"),
                    "requires_base_request": original is None,
                    "unresolved_headers": [n for n, v in headers.items() if v.startswith("${LIVE:")],
                    "http_executed": False, "source_evidence": None, "http_status": None,
                    "training_approved": False, "fingerprint": digest(request), "near_fingerprint": None,
                    "requires_live_session": True, "schema_validity": "not_validated", "split": "unassigned"}
            candidates.append({"sample_id": digest([key, kind, target, request]), "input": request,
                "annotation": {"proposed_label": label, "review_status": "pending_http_and_human_review",
                    "eligible_for_review": False,
                    "label_basis": "未送出的文件導向計畫；缺必填或認證屬非攻擊錯誤候選，不由 HTTP 狀態決定攻擊"},
                "metadata": meta})
            detail["generated"] += 1

        # 列出所有可選 header 的有／無組合，而非只做全放與全不放。
        for flags in itertools.product([False, True], repeat=len(optional)):
            present = mandatory + [name for name, enabled in zip(optional, flags) if enabled]
            headers = {name: specs[name]["values"][0] for name in present}
            emit(headers, "optional_presence")
            # 各 enum 值逐一變化，其他 header 固定，避免不必要的值笛卡兒積。
            for name in present:
                for value in specs[name]["values"][1:]:
                    emit({**headers, name: value}, "documented_value", name)
                if not specs[name]["sensitive"]:
                    for label, family, value in CASES:
                        emit({**headers, name: value}, "attack_intent", name, label, family)
        all_headers = {name: specs[name]["values"][0] for name in names}
        # 必填／條件認證缺失也要測，但不能把缺憑證的 401 自動標成 SQLi/XSS。
        for name in mandatory:
            emit({n: v for n, v in all_headers.items() if n != name}, "missing_required_or_auth", name)
    return candidates, coverage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path,
                        default=ROOT / "sentinel/dataset/reference/normal-candidates.csv")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "generated-header-plan-62")
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("輸出目錄已存在；請指定新的目錄，避免覆蓋人工修改。")
    rows, coverage = generate(args.reference)
    args.output.mkdir(parents=True)
    with (args.output / "candidates.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["平台", "HTTP方法", "API路徑", "目標header", "候選類別", "情境", "存在header", "省略header", "完整紀錄JSON"])
        writer.writeheader()
        for row in rows:
            writer.writerow({"平台": row["metadata"]["platform"], "HTTP方法": row["input"]["method"],
                "API路徑": row["input"]["path"], "目標header": row["metadata"]["target_parameter"],
                "候選類別": row["annotation"]["proposed_label"],
                "情境": row["metadata"]["scenario_kind"],
                "存在header": ", ".join(row["metadata"]["present_documented_headers"]),
                "省略header": ", ".join(row["metadata"]["absent_documented_headers"]),
                "完整紀錄JSON": json.dumps(row, ensure_ascii=False)})
    # 提供一列一個 API-header 的人工核對表，不只給總筆數。
    with (args.output / "header-coverage.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["平台", "方法", "API", "header", "必填", "條件認證", "敏感", "可輸入值數",
                         "可選有無組合數", "有放候選數", "沒放候選數", "文件列出", "契約參數列出"])
        for detail in coverage:
            operation_rows = [r for r in rows if (r["metadata"]["platform"], r["input"]["method"], r["input"]["path"])
                              == (detail["platform"], detail["method"], detail["path"])]
            for name, spec in detail["headers"].items():
                present = sum(name in r["input"]["headers"] for r in operation_rows)
                writer.writerow([detail["platform"], detail["method"], detail["path"], name,
                                 spec["required"], spec["conditional"], spec["sensitive"], len(spec["values"]),
                                 detail["presence_combinations"], present, len(operation_rows) - present,
                                 spec["in_manual_document"], spec["in_contract_parameters"]])
    summary = {"candidate_count": len(rows), "http_executed": 0, "training_approved": 0,
               "reference_sha256": digest(args.reference.read_bytes()), "coverage": coverage}
    (args.output / "coverage.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "coverage"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
