"""啟動獨立本機18444 HTTPS補測入口；日誌僅含UUID與分數，UTF-8原樣保存在.runtime。"""
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent

if __name__ == '__main__':
    runtime = HERE / '.runtime'
    key = runtime / 'medusa-document-check-tls.key'
    cert = runtime / 'medusa-document-check-tls.crt'
    if not key.is_file() or not cert.is_file(): raise SystemExit('請先建立私有本機TLS憑證')
    env = os.environ.copy(); env['MEDUSA_UPSTREAM'] = 'http://127.0.0.1:9100'
    command = [sys.executable, '-B', '-m', 'uvicorn', 'tls_demo_gateway:app', '--app-dir', str(HERE),
               '--host', '127.0.0.1', '--port', '18444', '--ssl-keyfile', str(key), '--ssl-certfile', str(cert), '--no-access-log']
    print('啟動本機HTTPS18444；按Ctrl+C停止這個獨立入口。')
    with (runtime / 'fixture-gateway.log').open('ab') as log:
        try: subprocess.run(command, env=env, stdout=log, stderr=log, check=True)
        except KeyboardInterrupt: pass
