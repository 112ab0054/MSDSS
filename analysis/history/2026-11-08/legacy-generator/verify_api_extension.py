"""Verify original byte preservation, new documentation, and active contracts.

No network requests and no changes to the protected original files.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

from active_api_contracts import load_active_contracts
from api_extension_schema import allowed_values, cell, deref, schema_rows

ROOT = Path(__file__).resolve().parents[2]
EXT = ROOT / "sentinel/analysis/api-extension"
MARKER = "<!-- MSDSS_API_EXTENSION_20261108 -->"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(name):
    return re.sub(r"〈(?:oneOf|anyOf)分支\d+〉", "", name).strip(".")


def walk_inputs(schema, doc, prefix="", trail=()):
    """Independent traversal to find declared input properties and scalar items."""
    if not isinstance(schema, dict):
        return
    ref = schema.get("$ref")
    if ref and ref in trail:
        return
    trail = trail + ((ref,) if ref else ())
    schema = deref(schema, doc)
    for kind in ("allOf", "oneOf", "anyOf"):
        for child in schema.get(kind, []):
            yield from walk_inputs(child, doc, prefix, trail)
    properties = schema.get("properties", {})
    # JSON Schema properties apply to objects. Some upstream array definitions
    # carry description-only properties; these are not extra object inputs.
    if isinstance(properties, dict) and schema.get("type") != "array":
        for name, child in properties.items():
            key = f"{prefix}.{name}" if prefix else name
            yield key, deref(child, doc)
            yield from walk_inputs(child, doc, key, trail)
    if "items" in schema:
        key = prefix + "[]"
        child = deref(schema["items"], doc)
        if child.get("type") not in (None, "object"):
            yield key, child
        yield from walk_inputs(schema["items"], doc, key, trail)
    additional = schema.get("additionalProperties")
    if isinstance(additional, dict):
        key = prefix + ".〈自訂鍵〉"
        yield key, deref(additional, doc)
        yield from walk_inputs(additional, doc, key, trail)


def values_are_present(schema, value_text):
    checked = 0
    for key in ("enum", "const", "default", "example", "examples", "minimum", "maximum", "minLength", "maxLength", "minItems", "maxItems", "pattern", "format"):
        if key not in schema:
            continue
        values = schema[key] if key == "enum" else [schema[key]]
        for value in values:
            token = value if key in ("enum", "const") and isinstance(value, str) else json.dumps(value, ensure_ascii=False)
            assert cell(token) in value_text, (key, token, value_text[:120])
            checked += 1
    return checked


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()
    config = read(EXT / "config.json")
    baseline = read(ROOT / config["baseline_manifest"])
    preservation = read(EXT / "preservation-report.json")
    modes = {item["file"]: item["mode"] for item in preservation["files"]}
    unchanged, appended = 0, 0
    for name, record in baseline.items():
        current = (ROOT / name).read_bytes()
        assert hashlib.sha256(current[:record["bytes"]]).hexdigest() == record["sha256"], name
        if modes[name] == "unchanged":
            assert len(current) == record["bytes"], name
            unchanged += 1
        else:
            assert MARKER.encode() in current[record["bytes"]:], name
            appended += 1
    operations = load_active_contracts()
    assert len(operations) == 65
    corrected = sum("/contract-corrections/" in entry["contract_file"] for entry in operations.values())
    assert corrected == 16
    password = operations[("bagisto", "POST", "/customer/login")]["operation"]["requestBody"]["content"]["application/json"]["schema"]["properties"]["password"]
    assert isinstance(password, dict) and password["type"] == "string"
    # Regression fixtures for the specific omissions reported by the user.
    fixture = {"type": "array", "items": {"type": "string", "enum": ["asc", "desc"]}, "default": [], "minItems": 0, "maxItems": 50, "example": []}
    rendered = allowed_values(fixture, {})
    assert all(token in rendered for token in ["`asc`", "`desc`", "預設值", "最少元素數", "最多元素數", "範例"])
    zeros = allowed_values({"type": "integer", "default": 0, "minimum": 0, "example": False}, {})
    assert "`0`" in zeros and "`false`" in zeros
    assert "`null`" in allowed_values({"type": ["string", "null"], "example": None}, {})
    assert "<mark>" in cell("範例：`<mark>`") and "<br>" in cell("最小值：0<br>最大值：50")
    nested = {"type": "object", "properties": {"groups": {"type": "array", "items": {"type": "array", "items": {"type": "object", "properties": {"mode": {"type": "string", "enum": ["a", "b"]}}}}}}}
    assert any(row[0] == "groups[][].mode" and "`a`" in row[4] and "`b`" in row[4] for row in schema_rows(nested, {}))
    recursive = {"components": {"schemas": {"Node": {"type": "object", "properties": {"next": {"$ref": "#/components/schemas/Node"}}}}}}
    recursive_rows = list(schema_rows({"$ref": "#/components/schemas/Node"}, recursive))
    assert len(recursive_rows) < 5 and any("遞迴欄位" in row[3] for row in recursive_rows)
    docs, constraints_total = [], 0
    for platform, settings in config["platforms"].items():
        file = ROOT / "sentinel/analysis/selected-api-contracts" / platform / "API_parameters.md"
        text = file.read_text(encoding="utf-8")
        tail = text.split(MARKER, 1)[1]
        assert "序列化方式：" not in tail and "拆開傳送：" not in tail
        sections = re.split(r"\n## ", tail)[1:]
        assert len(sections) == len(settings["additions"])
        source = read(ROOT / settings["source"])
        fields_checked, value_checks, explanation_rows, recursive_fields = 0, 0, 0, 0
        for number, (entry, section) in enumerate(zip(settings["additions"], sections), 16):
            assert section.startswith(f"{number:02d}. ") and re.search(r"[\u3400-\u9fff]", section.splitlines()[0])
            assert f"`{entry['method']} {entry['path']}`" in section
            assert "**API 涵義：**" in section and "| 可輸入值／格式 | 代表的涵義 |" in section
            rendered_rows, recursive_prefixes = {}, []
            for line in section.splitlines():
                if not line.startswith("| "):
                    continue
                cells = [value.strip() for value in re.split(r"(?<!\\)\|", line)[1:-1]]
                if len(cells) not in (5, 6) or cells[0] in ("位置", "本文字段"):
                    continue
                name = canonical(cells[1] if len(cells) == 6 else cells[0])
                assert cells[-2] and cells[-1], line
                assert re.search(r"[\u3400-\u9fff]", cells[-1]), (platform, name, cells[-1])
                assert cells[-2] == "—" or re.search(r"[\u3400-\u9fff]", cells[-2]), (platform, name, cells[-2])
                rendered_rows.setdefault(name, []).append(cells[-2])
                if "遞迴欄位" in cells[-1] and "#/components/" in cells[-1]:
                    recursive_prefixes.append(name)
                explanation_rows += 1
            item = source["paths"][entry["path"]]
            op = item[entry["method"].lower()]
            declared = []
            for raw in item.get("parameters", []) + op.get("parameters", []):
                parameter = deref(raw, source)
                schema = deref(parameter.get("schema", {}), source)
                declared.append((parameter["name"], {**schema, **{key: parameter[key] for key in ("example",) if key in parameter}}))
                if schema.get("type") == "array":
                    prefix = parameter["name"] if parameter["name"].endswith("[]") else parameter["name"] + "[]"
                    child = deref(schema.get("items", {}), source)
                    if child.get("type") not in (None, "object"):
                        declared.append((prefix, child))
                    declared.extend(walk_inputs(schema.get("items", {}), source, prefix))
                else:
                    declared.extend(walk_inputs(schema, source, parameter["name"]))
            for media, payload in deref(op.get("requestBody", {}), source).get("content", {}).items():
                assert f"`{media}`" in section
                declared.extend(walk_inputs(payload.get("schema", {}), source))
            for name, schema in declared:
                name = canonical(name)
                if name not in rendered_rows and any(name.startswith(prefix + ".") or name.startswith(prefix + "[]") for prefix in recursive_prefixes):
                    recursive_fields += 1
                    continue
                assert name in rendered_rows, (platform, entry["path"], "missing field", name)
                value_checks += values_are_present(schema, "\n".join(rendered_rows[name]))
                fields_checked += 1
            for status, response in op.get("responses", {}).items():
                assert re.search(r"\| " + re.escape(status) + r" \| [^\n]*[\u3400-\u9fff]", section), (entry["path"], status)
        constraints_total += value_checks
        docs.append({"platform": platform, "original_operations_preserved": 15, "new_operations": len(sections), "declared_input_fields_checked": fields_checked,
                     "input_value_checks": value_checks, "chinese_parameter_rows": explanation_rows, "recursive_fields_represented_by_reference": recursive_fields,
                     "original_table_headers_preserved": True})
    report = {"scope": "offline checks only; not runtime or full OpenAPI conformance", "network_requests": 0,
              "protected_files": len(baseline), "unchanged_files": unchanged, "append_only_files": appended,
              "original_operations_unchanged": 45, "active_operations": len(operations), "separate_corrections": corrected,
              "input_value_checks": constraints_total, "documents": docs, "ready_for_collection": False,
              "runtime_platform_tests": "not_run", "schema_regression_fixtures_passed": True}
    if args.write_report:
        (EXT / "verification-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
