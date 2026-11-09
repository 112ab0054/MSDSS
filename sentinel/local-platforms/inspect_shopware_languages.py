"""Read-only Store API language inventory; never publish access keys or context tokens."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
BASE = "http://127.0.0.1:18082/store-api"

def main() -> int:
    config = json.loads((ROOT / ".runtime/shopware.json").read_text(encoding="utf-8-sig"))
    def get(path: str, language_id: str | None = None) -> dict:
        headers = {"sw-access-key": config["access_key"], "Accept": "application/json"}
        if language_id:
            headers["sw-language-id"] = language_id
        with urlopen(Request(BASE + path, headers=headers), timeout=12) as response:
            return json.load(response)
    report = {"checked_at": datetime.now(timezone.utc).isoformat(), "base_url": BASE,
              "platform_version": "6.7.15.1", "read_only": True, "verified": False,
              "languages": []}
    try:
        context = get("/context")
        report["default_language_id"] = context.get("salesChannel", {}).get("languageId")
        page = 1
        seen = set()
        while True:
            data = get(f"/language?limit=100&page={page}")
            elements = data.get("elements")
            if not isinstance(elements, list):
                raise ValueError("Language response has no elements list")
            new = [x for x in elements if x.get("id") not in seen]
            if elements and not new:
                raise ValueError("Pagination repeated a page")
            for item in new:
                language_id = item["id"]
                seen.add(language_id)
                row = {"id": language_id, "name": item.get("name"),
                       "locale": (item.get("translationCode") or item.get("locale") or {}).get("code"),
                       "parent_id": item.get("parentId")}
                try:
                    checked = get("/context", language_id)
                    chain = checked.get("context", {}).get("languageIdChain", [])
                    info = checked.get("languageInfo", {})
                    row["context_language_id"] = chain[0] if chain else None
                    row["context_locale"] = info.get("localeCode")
                    row["accepted"] = bool(chain and chain[0] == language_id)
                except HTTPError as error:
                    row.update(accepted=False, http_status=error.code)
                report["languages"].append(row)
            if len(elements) < 100:
                break
            page += 1
            if page > 100:
                raise ValueError("Unexpected page count")
        report["verified"] = True
    except HTTPError as error:
        report["error"] = f"HTTP {error.code}; response body intentionally omitted"
    except (URLError, TimeoutError, OSError, ValueError, KeyError):
        report["error"] = "Local connection or response validation failed; no credentials recorded"
    destination = ROOT / "reports/shopware-language-inventory.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["verified"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
