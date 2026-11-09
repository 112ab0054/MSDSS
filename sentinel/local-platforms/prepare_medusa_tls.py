"""只建立私有本機TLS測試憑證；不安裝至系統信任、不修改任何服務。"""
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent


if __name__ == '__main__':
    tool = shutil.which('openssl')
    if not tool and Path(r'C:\Program Files\Git\usr\bin\openssl.exe').is_file():
        tool = r'C:\Program Files\Git\usr\bin\openssl.exe'
    if not tool: raise SystemExit('需要OpenSSL建立本機測試憑證')
    folder = HERE / '.runtime'; folder.mkdir(exist_ok=True)
    key = folder / 'medusa-document-check-tls.key'; cert = folder / 'medusa-document-check-tls.crt'
    if key.exists() or cert.exists():
        if not key.exists() or not cert.exists(): raise SystemExit('現有憑證不完整；不覆寫既有檔案')
        raise SystemExit('已存在私有測試憑證，未覆寫；使用前請確認效期')
    r = subprocess.run([tool, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', str(key),
        '-out', str(cert), '-days', '2', '-subj', '/CN=127.0.0.1', '-addext', 'subjectAltName=IP:127.0.0.1'],
        capture_output=True, timeout=30)
    if r.returncode: raise SystemExit('本機憑證建立失敗，未輸出私有內容')
    print('已建立兩天效期的私有本機憑證；API客戶端須明確信任此檔，不關閉TLS驗證')
