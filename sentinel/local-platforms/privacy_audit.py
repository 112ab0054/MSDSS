"""Check new public artifacts against actual local credentials, without printing values."""
import json
import os
from pathlib import Path
import re
from http_evidence import SENSITIVE

HERE = Path(__file__).resolve().parent


def local_secrets():
    found = set()
    for platform in ('bagisto', 'shopware', 'sylius', 'medusa'):
        file = HERE / '.runtime' / (platform + '.json')
        if file.exists():
            data = json.loads(file.read_text(encoding='utf-8-sig'))
            for key, value in data.items():
                if SENSITIVE.search(key) and isinstance(value, str) and len(value) >= 6:
                    found.add(value)
        for file in (HERE / '.runtime' / (platform + '.env'), HERE / '.runtime' / platform / '.env'):
            if not file.exists():
                continue
            for line in file.read_text(encoding='utf-8-sig').splitlines():
                key, sep, value = line.partition('=')
                value = value.strip('"')
                if sep and re.search(r'PASSWORD|SECRET|TOKEN|KEY|PASSPHRASE', key) and len(value) >= 6:
                    found.add(value)
    return found


def main():
    secrets = local_secrets()
    violations = []
    for directory, dirs, files in os.walk(HERE, followlinks=False):
        dirs[:] = [d for d in dirs if d not in ('.runtime', '__pycache__')]
        for name in files:
            file = Path(directory) / name
            if file.suffix.lower() not in ('.json', '.csv', '.md', '.py', '.ps1', '.php', '.yaml', '.sh', '.lock'):
                continue
            content = file.read_text(encoding='utf-8-sig')
            if any(secret in content for secret in secrets):
                violations.append(file.relative_to(HERE).as_posix())
    result = {'checked_against_actual_local_credentials': True, 'credential_values_disclosed': False,
              'passed': not violations, 'violating_files': violations}
    (HERE / 'reports/privacy-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return 1 if violations else 0


if __name__ == '__main__':
    raise SystemExit(main())
