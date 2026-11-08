"""Read source schemas without modifying source contracts or existing docs."""
import copy
import json
import re
OMIT = {"example", "examples", "x-codeSamples"}
TYPE_NAMES = {"string": "string", "integer": "integer", "number": "number", "boolean": "boolean", "object": "object", "array": "array", "null": "null"}
def clean(value):
    # Only remove documentation examples at known OAS object positions. A field
    # named password/token/example is still a schema and must retain its shape.
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, dict):
        result = {}
        maps = {"properties", "schemas", "parameters", "responses", "headers",
                "securitySchemes", "requestBodies", "links", "callbacks", "content"}
        for key, item in value.items():
            if key in OMIT:
                continue
            if key in maps and isinstance(item, dict):
                result[key] = {name: clean(schema) for name, schema in item.items()}
            elif key in {"security", "enum", "default", "required", "discriminator"}:
                result[key] = copy.deepcopy(item)
            else:
                result[key] = clean(item)
        return result
    return value

def resolve(doc, ref):
    if not ref.startswith("#/"):
        raise ValueError(f"External reference requires an explicit source: {ref}")
    current = doc
    for part in ref[2:].split("/"):
        current = current[part.replace("~1", "/").replace("~0", "~")]
    return current

def refs(value):
    if isinstance(value, dict):
        if "$ref" in value:
            yield value["$ref"]
        for item in value.values():
            yield from refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from refs(item)

def deref(value, doc):
    seen = set()
    while isinstance(value, dict) and "$ref" in value:
        ref = value["$ref"]
        if ref in seen:
            return {}
        seen.add(ref)
        value = {**resolve(doc, ref), **{k: v for k, v in value.items() if k != "$ref"}}
    return value

def cell(value):
    text = re.sub(r"\s+", " ", str(value if value is not None else "")).replace("|", "\\|")
    # Do not change literal values inside inline code (e.g. a regex or <mark>).
    return "".join(part if index % 2 else part.replace("<br>", "\x00BR\x00").replace("<", "&lt;").replace(">", "&gt;").replace("\x00BR\x00", "<br>")
                   for index, part in enumerate(re.split(r"(`[^`]*`)", text)))

def allowed_values(schema, doc, parameter=None, trail=()):
    """Describe constraints from the original source, including values in items.

    Examples are examples, not an exhaustive enum. A value of 0/false must not
    disappear, and no finite list is invented for free text or instance IDs.
    """
    if not isinstance(schema, dict):
        return "規格未列固定值"
    ref = schema.get("$ref")
    if ref and ref in trail:
        return "遞迴結構，見來源規格"
    schema = deref(schema, doc)
    trail = trail + ((ref,) if ref else ())
    labels = {"enum": "全部可選值", "const": "固定值", "default": "預設值", "format": "格式",
              "minimum": "最小值", "maximum": "最大值", "exclusiveMinimum": "不含邊界的下限",
              "exclusiveMaximum": "不含邊界的上限", "multipleOf": "須為此值的倍數",
              "minLength": "最少字元數", "maxLength": "最多字元數", "pattern": "正規表示式",
              "minItems": "最少元素數", "maxItems": "最多元素數", "uniqueItems": "元素須唯一",
              "minProperties": "最少屬性數", "maxProperties": "最多屬性數", "nullable": "允許 null",
              "readOnly": "唯讀", "writeOnly": "只供寫入", "deprecated": "已棄用",
              "contentEncoding": "內容編碼", "contentMediaType": "內容媒體類型"}
    parts = []
    for key, zh in labels.items():
        if key not in schema:
            continue
        if key == "enum":
            parts.append("固定值：" + "、".join("`" + (value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)) + "`" for value in schema[key]))
        elif key == "const":
            value = schema[key]
            parts.append("固定值：`" + (value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)) + "`")
        else:
            parts.append(f"{zh}：`{json.dumps(schema[key], ensure_ascii=False)}`")
    kinds = schema.get("type", [])
    kinds = kinds if isinstance(kinds, list) else [kinds]
    if "boolean" in kinds and "enum" not in schema and "const" not in schema:
        parts.append("布林可填值：`true`、`false`")
    if "null" in kinds:
        parts.append("可填 `null`")
    for key in ("example", "examples"):
        values = (parameter or {}).get(key, schema.get(key))
        if key in (parameter or {}) or key in schema:
            if key == "examples" and isinstance(values, dict):
                values = {name: deref(value, doc).get("value", deref(value, doc).get("externalValue", "來源未列值")) if isinstance(value, dict) else value for name, value in values.items()}
            parts.append("範例（非全部選項）：`" + json.dumps(values, ensure_ascii=False) + "`")
    if "items" in schema:
        parts.append("每個陣列元素：" + allowed_values(schema["items"], doc, trail=trail))
    for keyword, title in (("allOf", "須同時符合"), ("oneOf", "恰選一種結構"), ("anyOf", "至少符合一種結構")):
        for number, branch in enumerate(schema.get(keyword, []), 1):
            detail = allowed_values(branch, doc, trail=trail)
            if detail != "規格未列固定值":
                parts.append(f"{title}第 {number} 組：{detail}")
    if schema.get("additionalProperties") is False:
        parts.append("不允許額外欄位")
    if parameter:
        for key, title in (("style", "序列化方式"), ("explode", "拆開傳送"), ("allowReserved", "允許保留字元")):
            if key in parameter:
                parts.append(f"{title}：`{json.dumps(parameter[key], ensure_ascii=False)}`")
    if parts:
        return "<br>".join(parts)
    kind = schema.get("type")
    if kind == "string":
        return "可輸入字串；契約未列固定字串清單。識別碼與設定值須取自實例。"
    if kind in ("integer", "number"):
        return "可輸入" + ("整數" if kind == "integer" else "數值") + "；契約未列固定範圍。"
    if kind == "array":
        return "可輸入陣列；元素格式與子欄位見下表。"
    if kind == "object" or "properties" in schema:
        return "可輸入物件；具名子欄位見下表，契約未列固定選項。"
    return "契約未列固定值；依下方欄位或分支結構填寫。"

def type_name(kind):
    if isinstance(kind, list):
        return "／".join(type_name(item) for item in kind)
    return TYPE_NAMES.get(kind, kind)

def normalize_description(description):
    return re.sub(r"\s+", " ", description).replace("\\|", "|").replace("&lt;", "<").replace("&gt;", ">").strip()

def schema_rows(schema, doc, prefix="", inherited=True, depth=0, trail=(), required_override=()):
    """Render all explicit input properties, retaining conditional alternatives.

    Stop recursion through a schema already on this branch; point to the JSON
    instead of pretending recursive/opaque objects contain no further fields.
    """
    if not isinstance(schema, dict):
        return
    ref = schema.get("$ref")
    if ref and ref in trail:
        yield (prefix, "依遞迴結構", "object", "遞迴欄位；詳見契約 " + ref, "")
        return
    trail = trail + ((ref,) if ref else ())
    schema = deref(schema, doc)
    def all_required(value, seen=()):
        if not isinstance(value, dict) or value.get("$ref") in seen:
            return set()
        ref = value.get("$ref")
        value = deref(value, doc)
        names = set(value.get("required", []))
        for branch in value.get("allOf", []):
            names.update(all_required(branch, seen + ((ref,) if ref else ())))
        return names

    required = all_required(schema) | set(required_override)
    for keyword in ("allOf", "oneOf", "anyOf"):
        for index, branch in enumerate(schema.get(keyword, []), 1):
            label = prefix if keyword == "allOf" else f"{prefix}〈{keyword}分支{index}〉"
            yield from schema_rows(branch, doc, label, inherited and keyword == "allOf", depth + 1, trail, required)
    properties = schema.get("properties", {}) if schema.get("type") != "array" else {}
    if properties == []:
        yield (prefix or "（本文）", "規格未完整定義", "object", "上游 properties 是空陣列；不可據此自行猜測欄位", "")
        return
    for name, raw_prop in properties.items():
        prop = deref(raw_prop, doc)
        key = f"{prefix}.{name}" if prefix else name
        need = ("必填" if inherited else "父物件／該分支成立時必填") if name in required else "選填"
        kind = prop.get("type", "object" if "properties" in prop else "依契約")
        if prop.get("readOnly"):
            need = "唯讀；不應填入"
        yield (key, need, kind, prop.get("description", ""), allowed_values(prop, doc))
        # Recurse through the original reference so recursive object properties
        # remain detectable; do not erase the $ref before tracking it.
        yield from schema_rows(raw_prop, doc, key, inherited and name in required, depth + 1, trail)
    if not properties and not any(k in schema for k in ("allOf", "oneOf", "anyOf")) and prefix and schema.get("type") not in ("object", None):
        # Primitive array elements and primitive alternatives otherwise had no row.
        if prefix.endswith("[]") or re.search(r"〈(?:oneOf|anyOf)分支\d+〉$", prefix):
            yield (prefix, "元素／分支格式", schema.get("type", "依契約"), schema.get("description", ""), allowed_values(schema, doc))
    additional = schema.get("additionalProperties")
    if isinstance(additional, dict):
        yield (prefix + ".〈自訂鍵〉", "選填", deref(additional, doc).get("type", "依契約"), "此物件可填入自訂鍵；每個值須符合此處的型別與限制。", allowed_values(additional, doc))
        yield from schema_rows(additional, doc, prefix + ".〈自訂鍵〉", False, depth + 1, trail)
    elif additional is True:
        yield (prefix + ".〈自訂鍵〉", "選填", "依契約", "來源允許額外鍵值，沒有列出有限的欄位名稱清單。", "依實例功能填寫；不是固定選項清單")
    if "items" in schema:
        # An array element can itself be an array. Preserve its next [] level
        # instead of showing the outer element and silently dropping its fields.
        yield from schema_rows(schema["items"], doc, prefix + "[]", False, depth + 1, trail)
