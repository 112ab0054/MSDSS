"""Add API documentation without rewriting any pre-existing content.

Run from the project root: python sentinel/scripts/extend_api_scope.py [--check]
All original bytes are verified against the pre-change backup before writing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import yaml

from api_extension_schema import allowed_values, cell, clean, deref, normalize_description, refs, resolve, schema_rows, type_name

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "sentinel/analysis"
EXT = ANALYSIS / "api-extension"
MARKER = "<!-- MSDSS_API_EXTENSION_20261108 -->"
ROLES = {"core": "核心", "support": "流程支援", "optional": "選用"}
MEANINGS = {
    "firstName": "顧客或收件人的名字。", "lastName": "顧客或收件人的姓氏。",
    "email": "顧客或收件人的電子郵件。", "password": "帳號密碼；實際值不進模型或一般日誌。",
    "confirmPassword": "再次輸入密碼以確認；須與 password 相符，實際值不進模型或一般日誌。",
    "phone": "聯絡電話。", "gender": "顧客性別，依規格列舉或實例設定填寫。",
    "dateOfBirth": "顧客出生日期。", "subscribedToNewsLetter": "是否訂閱電子報。",
    "deviceToken": "裝置通知憑證；實際值不進模型或一般日誌。", "companyName": "公司名稱。",
    "vatId": "加值稅識別碼。", "address1": "地址第一行。", "address2": "地址第二行。",
    "city": "城市。", "state": "州／省。", "postcode": "郵遞區號。", "country": "國家代碼或名稱，依此實例定義。",
    "defaultAddress": "是否設為預設地址。", "shippingMethod": "選用的配送方式，取自目前購物車／配送紀錄的可用方式。",
    "paymentMethod": "選用的付款方式，取自目前購物車／付款紀錄的可用方式。",
    "paymentSuccessUrl": "付款成功後導向的網址。", "paymentFailureUrl": "付款失敗後導向的網址。",
    "paymentCancelUrl": "取消付款後導向的網址。", "sessionId": "建立訪客購物車時使用的工作階段識別碼。",
    "createNew": "是否建立新的獨立訪客購物車。", "items": "要更新的購物車品項清單。",
    "id": "此層資料的識別碼；購物車品項需使用目前購物車回應的品項 ID。",
    "quantity": "品項購買數量。", "email": "顧客電子郵件。", "billingAddress": "帳單地址物件。",
    "shippingAddress": "配送地址物件。", "couponCode": "套用的優惠券代碼。",
    "street": "街道地址。", "company": "公司名稱。", "countryCode": "國家代碼。",
    "provinceCode": "州／省代碼。", "provinceName": "州／省名稱。", "phoneNumber": "聯絡電話。",
    "tokenValue": "購物車／訂單的識別憑證，取自建車回應；實際值不進一般日誌。",
    "orderItemId": "要更新或刪除的訂單品項識別碼。", "shipmentId": "訂單配送紀錄的識別碼。",
    "paymentId": "訂單付款紀錄的識別碼。", "fields": "查詢時要回傳的欄位清單。",
    "associations": "要載入的實體關聯及各關聯的查詢條件。", "includes": "依實體指定回應包含的欄位。",
    "excludes": "依實體指定回應排除的欄位。", "sort": "排序設定。", "filter": "篩選條件。",
    "post-filter": "不影響彙總統計的後置篩選條件。", "ids": "要查詢的識別碼清單。",
    "aggregations": "彙總統計設定。", "grouping": "分組使用的欄位清單。",
    "checkPromotion": "是否檢查訂單付款方式仍可變更；依來源描述與實例核對。",
    "additionalProperties": "自訂物件中的額外鍵值。",
    "type": "此條件或資料物件的類型，依同列固定選項選用。",
    "field": "供篩選、排序或彙總統計使用的欄位名稱。",
    "value": "要比對的值，格式依所選條件類型而定。",
    "operator": "組合多個條件時使用的邏輯運算子，依列舉選項填寫。",
    "queries": "要組合或巢狀套用的查詢條件清單。",
    "parameters": "此條件使用的附加參數，例如範圍上下限。",
    "gt": "大於此值的範圍下限，不含此值。", "gte": "大於或等於此值的範圍下限。",
    "lt": "小於此值的範圍上限，不含此值。", "lte": "小於或等於此值的範圍上限。",
}
RESPONSES = {
    "Customer registered. `token` is the Bearer token for subsequent calls.": "顧客註冊完成；回傳的 token 可供後續請求作為 Bearer 憑證。",
    "Validation failed (email already taken, passwords do not match, etc.).": "驗證失敗，例如電子郵件已使用或兩次密碼不相符。",
    "Invalid input": "輸入資料無效。", "Validation Error": "資料驗證失敗。", "Address created.": "地址建立完成。",
    "Shipping method saved.": "配送方式已保存。", "No cart/addresses saved, or invalid shipping method.": "尚無購物車／結帳地址，或配送方式無效。",
    "Available payment methods.": "回傳可用付款方式。", "Payment method saved successfully.": "付款方式已保存。",
    "No cart/shipping saved, or invalid payment method.": "尚無購物車／配送設定，或付款方式無效。",
    "Guest cart created; returns the cart token used to identify the guest for subsequent cart/checkout calls.": "訪客購物車已建立；回傳識別憑證供後續購物車與結帳流程使用。",
    "The updated cart.": "回傳更新後的購物車。",
    "A line item cannot be updated, e.g. a quantity that is not a positive integer, a quantity that is not a multiple of the parent quantity or a line item type that does not support updates.": "品項無法更新，例如數量不是正整數、不是父品項數量的倍數，或該品項類型不支援更新。",
    "The `sw-access-key` header is missing.": "缺少 sw-access-key 標頭。",
    "One of the given ids does not reference a line item of the current cart.": "指定識別碼中有值不屬於目前購物車的品項。",
    "One of the submitted ids is not a string, or does not reference an entity that is available in the current sales channel.": "送出的識別碼不是字串，或指向目前銷售通路不可用的資料。",
    "A billing or shipping address id was sent without a logged in customer.": "未登入顧客卻送出帳單或配送地址識別碼。",
    "An array of orders and an indicator if the payment of the order can be changed.": "回傳訂單陣列，以及訂單付款方式是否可變更的指標。",
    "The `Criteria` sent with the request is invalid, e.g. an unknown filter field, sorting field or association.": "查詢條件無效，例如未知的篩選欄位、排序欄位或關聯名稱。",
    "No customer is logged in and the request did not provide a `deepLinkCode` with matching guest credentials.": "顧客未登入，且未提供與訪客憑證相符的 deepLinkCode。",
    "Too many failed guest authentication attempts for this deep link code and client IP.": "此深層連結代碼與用戶端 IP 的訪客認證失敗次數過多。",
    "Returns the current context.": "回傳目前購物情境。", "Order resource created": "購物車／訂單資料已建立。",
    "Order resource updated": "訂單資料已更新。", "Order resource deleted": "來源將此回應描述為訂單資料已刪除；本操作用於移除指定訂單品項。",
    "An error occurred": "處理時發生錯誤。", "Not found": "找不到指定資源。",
    "ShippingMethod collection": "回傳此配送紀錄可用的配送方式清單。", "PaymentMethod collection": "回傳此付款紀錄可用的付款方式清單。",
    "Entity search result containing shipping methods.": "回傳包含配送方式的實體搜尋結果。",
    "Returns the context token. Use that as your `sw-context-token` header for subsequent requests. Redirect if getRedirectUrl is set.": "回傳購物情境憑證，後續憑證模式請求將它放在 sw-context-token 標頭；若設定 getRedirectUrl，須依回應進行導向。",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def matches_generated_version(path, data):
    recorded = EXT / "generated-file-hashes.json"
    hashes = read(recorded) if recorded.exists() else {}
    return hashes.get(relative(path)) == hashlib.sha256(data).hexdigest()


def relative(path):
    return str(path.relative_to(ROOT)).replace("\\", "/")


def filename(method, path):
    return re.sub(r"[^a-zA-Z0-9]+", "-", method.lower() + "-" + path).strip("-").lower() + ".json"


def remove_transport_display(text):
    """Remove only the two user-excluded display entries from value cells.

    Keep source OpenAPI style/explode fields and all other document bytes.
    A cell containing nothing else uses an em dash as the empty placeholder.
    """
    lines = []
    for line in text.splitlines(keepends=True):
        if line.startswith("| ") and ("序列化方式：" in line or "拆開傳送：" in line):
            parts = re.split(r"(?<!\\)\|", line)
            if len(parts) in (7, 8):
                value = parts[-3]
                leading = value[:len(value) - len(value.lstrip(" "))]
                trailing = value[len(value.rstrip(" ")):]
                entries = value.strip(" ").split("<br>")
                kept = [entry for entry in entries if not re.fullmatch(r"\s*(?:序列化方式|拆開傳送)：`[^`]*`\s*", entry)]
                if len(kept) != len(entries):
                    parts[-3] = leading + ("<br>".join(kept) or "—") + trailing
                    line = "|".join(parts)
        lines.append(line)
    return "".join(lines)


def security_headers(source, requirements):
    groups = []
    for requirement in requirements:
        fields = []
        for name in requirement:
            scheme = deref(source["components"]["securitySchemes"][name], source)
            field = scheme.get("name", "Authorization")
            fields.append(f"`{field}`" + ("（Bearer 憑證）" if scheme.get("type") == "http" else ""))
        groups.append(" ＋ ".join(fields) if fields else "此組不要求認證")
    return "；或 ".join(groups) if groups else "來源未宣告認證方案"


def meaning(name, description, translations):
    if description:
        text = translations.get(normalize_description(description)) or description
        if re.search(r"[A-Za-z]{3}", text) and not re.search(r"[\u3400-\u9fff]", text):
            raise ValueError(f"Translate explanation before publishing: {name}: {description}")
        return text
    leaf = re.sub(r"〈[^〉]+〉|\[\]", "", name).strip(".").split(".")[-1]
    if leaf in MEANINGS:
        return MEANINGS[leaf]
    return f"來源未提供 {name} 的業務說明；依型別與來源結構填寫，不自行推定固定值。"


def fragment(platform, source, entry, source_path, digest):
    item = source["paths"][entry["path"]]
    operation = clean(item[entry["method"].lower()])
    security = operation.get("security", source.get("security", []))
    result = {"platform": platform, "source_contract": source_path, "source_sha256": digest,
              "source_info_version": source["info"].get("version"), "method": entry["method"], "path": entry["path"],
              "operation": operation, "effective_security": security,
              "path_parameters": clean(item.get("parameters", [])), "servers": clean(item.get("servers", source.get("servers", []))),
              "components": {"securitySchemes": {name: clean(source["components"]["securitySchemes"][name]) for requirement in security for name in requirement}}}
    pending, seen = list(refs(result)), set()
    while pending:
        ref = pending.pop()
        if ref in seen:
            continue
        seen.add(ref)
        assert ref.startswith("#/components/"), ref
        parts = [part.replace("~1", "/").replace("~0", "~") for part in ref[2:].split("/")]
        category, name = parts[1:3]
        value = clean(source["components"][category][name])
        result["components"].setdefault(category, {})[name] = value
        pending.extend(refs(value))
    for ref in refs(result):
        assert resolve(result, ref) == clean(resolve(source, ref))
    for requirement in security:
        assert all(isinstance(scopes, list) for scopes in requirement.values())
    assert operation == clean(source["paths"][entry["path"]][entry["method"].lower()])
    return result


def operation_doc(platform, source, entry, number, translations):
    item = source["paths"][entry["path"]]
    op = item[entry["method"].lower()]
    security = op.get("security", source.get("security", []))
    lines = [f"## {number:02d}. {entry['title']} API", "", f"`{entry['method']} {entry['path']}`", "",
             f"**operationId：** {op.get('operationId', '契約未提供')}  ", f"**來源檔案：** {filename(entry['method'], entry['path'])}", "",
             f"**API 涵義：** {entry['purpose']}。", "", f"**採用角色：** {ROLES[entry['role']]}。", "",
             "**認證依據：** 以下包含操作明列及從來源根層繼承的認證要求；同一組須全部滿足，不同組擇一。來源宣告與實例是否開放訪客須分開核對。", ""]
    rows = []
    for group, requirement in enumerate(security, 1):
        for name in requirement:
            scheme = deref(source["components"]["securitySchemes"][name], source)
            location = scheme.get("in", "header")
            field = scheme.get("name", "Authorization")
            values = "格式：`Bearer <由實例核發的憑證>`；實際憑證不進一般資料集" if scheme.get("type") == "http" else "使用實例核發的對應值；實際值不進一般資料集"
            rows.append((location, field, f"採第 {group} 組認證時必填", "string", values, f"來源認證方案 {name}；同組其他方案亦須滿足。"))
    params = {}
    for raw in item.get("parameters", []) + op.get("parameters", []):
        parameter = deref(raw, source)
        params[(parameter["in"], parameter["name"])] = parameter
    for (location, name), parameter in params.items():
        schema = deref(parameter.get("schema", {}), source)
        rows.append((location, name, "必填" if parameter.get("required") else "選填", type_name(schema.get("type", "依契約")), allowed_values(schema, source, parameter), meaning(name, parameter.get("description", ""), translations)))
        element_prefix = name if name.endswith("[]") else name + "[]"
        nested = schema_rows(schema.get("items", {}), source, prefix=element_prefix, inherited=False) if schema.get("type") == "array" else schema_rows(schema, source, prefix=name, inherited=bool(parameter.get("required")))
        for key, required, kind, description, limits in nested:
            rows.append((location, key, required, type_name(kind), limits or "依來源結構填寫", meaning(key, description, translations)))
    lines += ["| 位置 | 參數名稱 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |", "|---|---|---|---|---|---|"]
    for row in rows:
        lines.append("| " + " | ".join(cell(value) for value in row) + " |")
    if not rows:
        lines.append("| — | 無明列參數 | — | — | 依來源認證與部署條件 | 此操作未列具名輸入參數。 |")
    body = deref(op.get("requestBody", {}), source)
    if body:
        lines += ["", "### 請求本文", "", "- 必填：" + ("是" if body.get("required") else "否（來源未宣告本文必填；若送出本文，仍須符合欄位條件）")]
        for media, payload in body.get("content", {}).items():
            schema = deref(payload.get("schema", {}), source)
            lines += [f"- Content-Type：`{media}`", f"- Schema 型別：`{type_name(schema.get('type', 'object'))}`",
                      "- 本文格式／範例：" + cell(allowed_values(schema, source, payload)), "",
                      "| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |", "|---|---|---|---|---|"]
            fields = list(schema_rows(payload.get("schema", {}), source))
            for name, required, kind, description, limits in fields:
                lines.append("| " + " | ".join(cell(value) for value in (name, required, type_name(kind), limits or "依來源結構填寫", meaning(name, description, translations))) + " |")
            if not fields:
                lines.append("| （本文） | 依來源契約 | object | 來源沒有明列具名欄位；不能推定任意本文都有效 | 此操作宣告接收物件，實際所需狀態與額外條件須在固定實例核對。 |")
            lines.append("")
    if platform == "shopware":
        lines += ["", "**情境延續：** 使用憑證模式時，後續購物車／結帳請求沿用回應的 sw-context-token；若選 sw-context-source=session，則改用前台工作階段 Cookie，不能同時送 sw-context-token。此標頭互斥條件依來源描述，仍須實例核對。"]
    if platform == "sylius" and entry["path"].endswith(("/shipments/{shipmentId}", "/payments/{paymentId}")):
        lines += ["", "**識別值格式：** 欄位需依實例接受的資源參照填寫，可能使用 IRI（資源路徑）；從對應 /methods 回應取得，不自行把它改成其他平台的裸 ID。"]
    if platform == "bagisto" and entry["path"] == "/customers":
        lines += ["", "**資料產生注意：** status、isVerified、isSuspended 是來源列出的顧客狀態欄位；不把任意設定驗證或停權狀態當成一般正常註冊流程，先核對實例權限與設定。"]
    lines += ["", "### 回應狀態", "", "| 狀態碼 | 回應說明 |", "|---|---|"]
    for status, raw in op.get("responses", {}).items():
        response = deref(raw, source)
        description = response.get("description")
        if description and description not in RESPONSES:
            raise ValueError(f"Translate response before publishing: {description}")
        lines.append(f"| {status} | {RESPONSES.get(description, '契約未提供回應說明。')} |")
    return remove_transport_display("\n".join(lines) + "\n")


def build(config):
    baseline = read(ROOT / config["baseline_manifest"])
    translations = {normalize_description(key): value for key, value in read(EXT / "translations.json").items()}
    outputs, appends, manifest, corrections = {}, {}, [], []
    source_records = {}
    plan = ["# 三平台 API 增補採用計畫", "", "本次只新增或在檔尾增補，原有 45 個操作的標題、用途、參數、說明及可輸入值逐位元保留。舊文件記錄原版範圍，本文件與 active-api-manifest.json 記錄本次增補後的採用範圍。", "",
            "## 採用範圍", "", "65 個操作：Bagisto 21、Shopware 21、Sylius 23。57 個核心、6 個流程支援、2 個選用；每平台操作數不必相同。", "",
            "原 Shopware GET /checkout/gateway 與 Sylius 顧客驗證請求保留為選用，不阻擋第一版正常流程。原文件不改字，角色以新清單為準。", "",
            "第一版標籤固定為 normal、sqli、xss。原文件中的五分類是保留的原始研究方向；CMDi 與 path_traversal 需有既有功能的合理輸入情境及人工審核，再另立實驗。", "",
            "`[]` 表示陣列元素，分支標記表示不同可接受結構，不是實際欄位名稱。列舉值逐項保留；範例不是全部選項，自由文字與實例 ID 無法列成有限字串清單。巢狀必填只在父物件或該分支成立時適用，唯讀欄位不應送入。", ""]
    supplemental = ["# 既有 API 的補充核對", "", "此文件補充既有 45 操作的契約與流程問題，不覆寫原標題、參數表格或 JSON。", "",
                    "## 修正版契約的選用", "", "遮罩造成結構差異的 16 份 JSON 另存 contract-corrections；active-api-manifest.json 指向修正版。其餘既有操作仍指向原檔，解析參照與繼承認證時使用記錄的來源規格。消費清單時不得只掃舊目錄而忽略修正版路徑。", "",
                    "修正版是包含相依元件的操作片段，不是獨立完整 OpenAPI 文件；原始範例值省略，schema、列舉、預設值與認證 scopes 的結構保留。", "",
                    "| 平台 | 操作 | 原檔 | 修正版 |", "|---|---|---|---|"]
    for platform, settings in config["platforms"].items():
        source_path = ROOT / settings["source"]
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        assert digest == settings["source_sha256"], platform
        source = read(source_path)
        source_records[platform] = {"contract": settings["source"], "sha256": digest, "info_version": source["info"].get("version"), "ready_for_collection": False, "blocking_reasons": settings["blocking_reasons"]}
        old_entries = []
        for method, path in settings["original_operation_keys"]:
            file = ANALYSIS / "selected-api-contracts" / platform / filename(method, path)
            old = read(file)
            operation = source["paths"][path][method.lower()]
            chosen = file
            if clean(old["operation"]) != clean(operation):
                chosen = EXT / "contract-corrections" / platform / file.name
                outputs[chosen] = json.dumps(fragment(platform, source, {"method": method, "path": path}, settings["source"], digest), ensure_ascii=False, indent=2) + "\n"
                corrections.append(relative(chosen))
                supplemental.append(f"| {platform} | `{method} {path}` | `{relative(file)}` | [{file.name}](contract-corrections/{platform}/{file.name}) |")
            role = "optional" if (platform == "shopware" and path == "/checkout/gateway") or (platform == "sylius" and path.endswith("/verification-request")) else "core"
            old_entries.append({"method": method, "path": path, "role": role, "contract_file": relative(chosen), "original_file": relative(file), "is_addition": False})
        addition_entries, new_docs = [], []
        plan += [f"## {platform} 新增 {len(settings['additions'])} 個操作", "", "| 角色 | Method | Path | 用途 |", "|---|---|---|---|"]
        for number, entry in enumerate(settings["additions"], 16):
            path = ANALYSIS / "selected-api-contracts" / platform / filename(entry["method"], entry["path"])
            assert relative(path) not in baseline
            outputs[path] = json.dumps(fragment(platform, source, entry, settings["source"], digest), ensure_ascii=False, indent=2) + "\n"
            new_docs.append(operation_doc(platform, source, entry, number, translations))
            addition_entries.append({**entry, "contract_file": relative(path), "is_addition": True})
            plan.append(f"| {ROLES[entry['role']]} | {entry['method']} | `{entry['path']}` | {entry['purpose']} |")
        for entry in old_entries + addition_entries:
            op = source["paths"][entry["path"]][entry["method"].lower()]
            manifest.append({"platform": platform, **entry, "source_contract": settings["source"], "source_sha256": digest, "effective_security": op.get("security", source.get("security", []))})
        plan += ["", "### 基底網址與正常流程", "", "來源 servers：`" + json.dumps(source.get("servers", []), ensure_ascii=False) + "`。", ""]
        plan += [f"{index}. {step}" for index, step in enumerate(settings["workflow"], 1)]
        plan += ["", "### 正式收集前", ""] + [f"- {reason}" for reason in settings["blocking_reasons"]] + [""]
        docfile = ANALYSIS / "selected-api-contracts" / platform / "API_parameters.md"
        appends[docfile] = "\n\n" + MARKER + "\n\n---\n\n以下為本次增補操作；原第 01–15 節內容保留不變。新增欄位沿用原表格，另補來源認證與巢狀結構；可輸入值列出來源的選項、預設、範例及限制。完整採用規則見 [增補計畫](../../api-extension/plan.md)。\n\n" + "\n".join(new_docs)
        auth_rows = []
        for entry in old_entries:
            op = source["paths"][entry["path"]][entry["method"].lower()]
            requirements = op.get("security", source.get("security", []))
            origin = "操作明列" if "security" in op else "繼承來源根層"
            auth_rows.append(f"| `{entry['method']} {entry['path']}` | {security_headers(source, requirements)} | {origin} | 依來源宣告，實際訪客與會員權限仍須核對。 |")
        appends[docfile] += "\n### 既有 15 個操作的認證與契約補充\n\n原第 01–15 節不改字，缺漏或受遮罩影響之處另列於此。下表只補認證方案，原參數表中的公開金鑰等要求仍適用；同一組的標頭同時滿足，不同組擇一。\n\n| 既有操作 | 認證標頭／方式 | 來源 | 核對說明 |\n|---|---|---|---|\n" + "\n".join(auth_rows) + "\n\n16 份結構修正版的選用方式見 [既有 API 補充](../../api-extension/existing-api-supplements.md)，以新採用清單指向的檔案為準。\n"
        if platform == "bagisto":
            password = source["paths"]["/customer/login"]["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]["password"]
            appends[docfile] += "\n**登入欄位補充：** 原拆分檔的 password schema 受遮罩影響；修正版恢復原來源定義。\n\n| 本文字段 | 必填 | 型別 | 可輸入值／格式 | 代表的涵義 |\n|---|---|---|---|---|\n| password | 送出登入本文時必填 | string | " + cell(allowed_values(password, source)) + " | 登入密碼；只恢復規格結構，實際值不進模型或一般日誌。 |\n"
        elif platform == "shopware":
            appends[docfile] += "\n**情境補充：** 使用 sw-context-source=session 時不能再送 sw-context-token。GET /checkout/gateway 是關卡檢查，保存地址／配送／付款設定使用新增的 PATCH /context；原說明保留作歷史。\n"
        indexfile = ANALYSIS / "selected-api-contracts" / platform / "README.md"
        appends[indexfile] = "\n\n" + MARKER + f"\n\n## 本次增補：目前共 {15 + len(addition_entries)} 個操作\n\n原 15 操作說明保留；下表是新增操作。既有契約修正版與認證繼承以 [採用清單](../../api-extension/active-api-manifest.json) 為準。\n\n| Method | Path | File |\n|---|---|---|\n" + "\n".join(f"| {x['method']} | `{x['path']}` | [{Path(x['contract_file']).name}](./{Path(x['contract_file']).name}) |" for x in addition_entries) + "\n"
    assert len(manifest) == 65 and len(corrections) == 16
    assert {role: sum(x['role'] == role for x in manifest) for role in ROLES} == {"core": 57, "support": 6, "optional": 2}
    supplemental += ["", "## 認證與流程補充", "", "- 所有操作的 effective_security 都保存在新採用清單；缺少 operation.security 時繼承來源根層，明列空陣列才取消繼承。 scopes 必須是陣列。",
                     "- Bagisto 登入 password 應保留為字串型別的 schema 物件，不能把整個 schema 遮成文字；來源部分 properties=[] 為上游結構問題，需實例核對，不自行猜欄位。",
                     "- Shopware 的 ApiKey 與 ContextToken 是認證方案，不能遮掉 scopes 結構；sw-context-source=session 與 sw-context-token 互斥，不可照範例同時送出。",
                     "- Bagisto POST /cart 用於讀取／重算目前購物車；訪客另用 /cart-tokens。POST /checkout-orders 回傳 redirect=true 不代表訂單與付款已完成。",
                     "- Shopware POST /checkout/order 建單、POST /order 查單；GET /checkout/gateway 不能取代 PATCH /context 保存設定。",
                     "- Sylius 使用 order token 表示購物車；配送與付款可能採 IRI，PATCH 保留 application/merge-patch+json。", ""]
    plan += ["## 訓練、驗證與 Medusa Demo", "", "三平台各自先跑通正常購物、合法特殊字元與非攻擊錯誤，再製作合理位置且經人工審核的 SQLi／XSS 嘗試。支援端點的正常請求也需檢查誤報；不要求每個 API 都有每種攻擊。按共同業務事件控制平台與類別分布。", "",
             "先依 session／操作批次、模板家族及近似請求分組。共用模板家族不能跨訓練與外層測試；前處理、詞彙表只 fit 訓練資料。平台名稱、標籤、情境名稱與回應結果不作推論特徵。密碼、憑證與金鑰實值不進一般資料集或模型。", "",
             "三回合平台留一：Bagisto＋Shopware→Sylius；Bagisto＋Sylius→Shopware；Shopware＋Sylius→Bagisto。保留平台是外層測試，只用訓練平台內的分組 validation 做提前停止、選方法與門檻。最後以三平台重訓並凍結模型、特徵、詞彙表、類別順序、門檻與版本，再測 Medusa。", "",
             "報告各平台／業務事件的樣本數、正常誤報率、各攻擊 precision／recall／F1、Macro-F1、混淆矩陣與新增延遲（含 p95）；未測端點明列未測。這些結果不支持『所有電商平台一定有效』。", "",
             "Medusa 為外部測試與 Demo，不加入訓練或門檻選擇；用 Medusa 調整時另列調適版並保留直接移植結果。套件固定 2.22.4、bundled Store 規格 info.version=2.22.3，目前包含 79 操作／69 paths。原 77 文件不改，現行待測操作另存 medusa-holdout-inventory.json，所有實測狀態起始為 not_run。", "",
             "Demo 使用隔離測試帳號、商品與測試付款，先重跑固定正常流程；測試端獨立保存 request_id、替代 session ID、預期／實際結果與伺服器紀錄對帳。Medusa 部分前置拒絕不進目前 logger，不能把沒有日誌當成已防禦。此計畫未改部署、資料庫、沙盒或 Mirage。", "",
             "## 目前完成與未完成", "", "已完成：新增契約存在性、來源 SHA、欄位／選項呈現、認證結構、參照與舊內容保留的離線核對。未完成：固定三平台實例、端到端正常流程、正式訓練資料、模型訓練與效果驗證。ready_for_collection 保持 false。", ""]
    outputs[EXT / "plan.md"] = "\n".join(plan)
    outputs[EXT / "existing-api-supplements.md"] = "\n".join(supplemental)
    outputs[EXT / "active-api-manifest.json"] = json.dumps({"operation_count": 65, "original_count": 45, "addition_count": 20, "phase_one_labels": config["phase_one_labels"], "sources": source_records, "operations": manifest}, ensure_ascii=False, indent=2) + "\n"
    medusa_file = ROOT / "backend/static/openapi/store.yaml"
    medusa = yaml.safe_load(medusa_file.read_bytes())
    medusa_entries = [{"method": method.upper(), "path": path, "runtime_status": "not_run"} for path, item in medusa["paths"].items() for method in item if method in {"get", "post", "put", "patch", "delete", "options", "head", "trace"}]
    assert len(medusa_entries) == 79 and len(medusa["paths"]) == 69
    outputs[EXT / "medusa-holdout-inventory.json"] = json.dumps({"application_version": "2.22.4", "spec_version": medusa["info"]["version"], "source": relative(medusa_file), "sha256": hashlib.sha256(medusa_file.read_bytes()).hexdigest(), "role": "external_holdout_and_demo", "operations": medusa_entries}, ensure_ascii=False, indent=2) + "\n"
    links = {
        ANALYSIS / "selected-apis.md": "## 本次增補採用範圍\n\n前文保留原 45 操作決策。本次新增 20 操作，共 65；POST /order 現納入查單，checkout/gateway 與顧客驗證請求改列選用。清單、角色、來源與正常流程以 [增補計畫](api-extension/plan.md) 及 [採用清單](api-extension/active-api-manifest.json) 為準。",
        ANALYSIS / "selected-api-contracts/README.md": "## 本次增補\n\n目前為 Bagisto 21、Shopware 21、Sylius 23，共 65 操作。原文與 45 份 JSON 不覆寫；16 份結構修正版另存 [補充目錄](../api-extension/existing-api-supplements.md)。請用 [採用清單](../api-extension/active-api-manifest.json) 解析正確檔案，不只掃描舊目錄。",
        ROOT / "sentinel/README.md": "## 本次增補\n\n原 45 操作與文件完整保留；新增後共 65 操作。見 [增補計畫](analysis/api-extension/plan.md)、[採用清單](analysis/api-extension/active-api-manifest.json)、[舊內容保留證據](analysis/api-extension/preservation-report.json)。工具只新增或檔尾增補，檢查指令：`python sentinel/scripts/extend_api_scope.py --check`。需要 Python 與 PyYAML。",
        ANALYSIS / "feature-plan.md": "## 本次實施補充\n\n前文的五分類保留為原始研究方向。本次第一版先採 normal、sqli、xss；CMDi 與 path_traversal 暫緩，依 [增補計畫](api-extension/plan.md) 的情境審核條件另立實驗。A／B／C 特徵比較沿用。",
        ANALYSIS / "data-plan.md": "## 本次收集範圍補充\n\n目前候選為 65 操作，包含核心、流程支援與選用。按共同業務事件控管樣本分布，納入支援端點的正常流量；實例版本與正常流程未核對前不得視為正式收集就緒。見 [增補計畫](api-extension/plan.md)。",
        ANALYSIS / "validation-plan.md": "## 本次驗證補充\n\n保留平台屬外層測試，不用來選特徵或門檻；模板家族與近似變體的分組需跨平台隔離。Medusa 凍結後再測，調整則另列調適版。新增操作、待測範圍與 logger 對帳限制見 [增補計畫](api-extension/plan.md)。",
        ANALYSIS / "PROJECT_CONTEXT.md": "## 使用者後續決定：採納建議並保留原資料\n\n使用者已授權增補 API，但要求既有標題、說明、參數、參數含義及所有可輸入值均不得改動。本次以檔尾增補／另存修正版方式採納 65 操作計畫，先前還原紀錄保留作為歷史。最新範圍見 api-extension/plan.md 與 active-api-manifest.json；不得以重建工具覆蓋原 45 操作文件。",
        ROOT / "問題排除紀錄.md": "## 11. 採納 API 修正建議時，必須完整保留原有資料\n\n### 遇到的問題\n\n先前重建文件造成原參數選項與格式資訊遺失。使用者在恢復原版後，授權採納 API 建議，但明確要求原標題、說明、參數、參數含義及所有可輸入值不變。\n\n### 處理方式\n\n先備份並記錄 74 個既有檔案的原始長度與 SHA-256。三平台參數文件僅在檔尾從第 16 節開始新增，分別增加 6、6、8 個操作，共 65 個。原 45 份 JSON 不覆寫；16 份結構修正版另存 api-extension/contract-corrections，由 active-api-manifest.json 指定採用。\n\n保留檢查逐位元驗證原內容；新增文件另核對中文標題、含義、全部明列選項、範例、預設值、限制、陣列與遞迴參照。工具偵測到原內容或人工修改與紀錄不符時會停止，不直接覆蓋。\n\n### 目前狀態\n\n目前採用範圍為 65 個候選操作；原版 45 操作及先前紀錄原文均保留。本節為後續決定，第 7、9 節記錄的恢復原版狀態屬歷史。保留證據、核對結果與實測前條件見 [增補計畫](sentinel/analysis/api-extension/plan.md)、[保留比對](sentinel/analysis/api-extension/preservation-report.json) 與 [離線核對結果](sentinel/analysis/api-extension/verification-report.json)。尚未完成固定版本實例的正常流程驗證。",
    }
    for path, content in links.items():
        appends[path] = "\n\n" + MARKER + "\n\n" + content + "\n"
    # Treat every original byte as protected. An append is allowed only at EOF.
    protection = []
    for name, record in baseline.items():
        path = ROOT / name
        current = path.read_bytes()
        original = current[:record["bytes"]]
        assert len(original) == record["bytes"] and hashlib.sha256(original).hexdigest() == record["sha256"], f"Protected original bytes changed: {name}"
        expected = original + appends.get(path, "").encode("utf-8")
        if path in appends:
            assert current in (original, expected) or matches_generated_version(path, current), f"Existing content changed; refuse append: {name}"
            outputs[path] = expected
        else:
            assert current == original, f"Protected original changed: {name}"
        protection.append({"file": name, "mode": "append_only" if path in appends else "unchanged", "original_bytes": len(original), "original_sha256": record["sha256"], "original_bytes_preserved": True})
    assert len(appends) == sum(item["mode"] == "append_only" for item in protection)
    outputs[EXT / "preservation-report.json"] = json.dumps({"backup": config["backup"], "protected_original_files": len(protection), "original_operations": 45, "added_operations": 20, "correction_fragments": len(corrections), "all_original_bytes_preserved": True, "files": protection}, ensure_ascii=False, indent=2) + "\n"
    return outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    check = parser.parse_args().check
    config = read(EXT / "config.json")
    outputs = build(config)
    baseline = read(ROOT / config["baseline_manifest"])
    # Preflight all destinations before any write. Never overwrite manual edits.
    different = []
    for path, value in outputs.items():
        assert path.resolve().is_relative_to(ROOT)
        data = value if isinstance(value, bytes) else value.encode("utf-8")
        if path.exists() and path.read_bytes() != data:
            assert relative(path) in baseline or matches_generated_version(path, path.read_bytes()), f"New generated file has manual differences; refuse overwrite: {path}"
        if not path.exists() or path.read_bytes() != data:
            different.append(relative(path))
    if check:
        assert not different, f"Files not yet installed or different: {different}"
    else:
        for path, value in outputs.items():
            data = value if isinstance(value, bytes) else value.encode("utf-8")
            if not path.exists() or path.read_bytes() != data:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
        hashes = {relative(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in outputs}
        (EXT / "generated-file-hashes.json").write_text(json.dumps(hashes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"mode": "check" if check else "add_and_append", "changed_files": len(different), "operations": 65, "original_bytes_preserved": True}))


if __name__ == "__main__":
    main()
