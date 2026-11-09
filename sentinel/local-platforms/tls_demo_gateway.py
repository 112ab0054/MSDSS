"""獨立本機HTTPS驗證入口；由實際TLS scheme建立代理標頭，不採信客戶端值。"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'gateway'))
from app import app as gateway


class TransportScheme:
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            scope = dict(scope)
            headers = [(k, v) for k, v in scope['headers'] if k.lower() != b'x-forwarded-proto']
            headers.append((b'x-forwarded-proto', scope['scheme'].encode('ascii')))
            scope['headers'] = headers
        await gateway(scope, receive, send)


app = TransportScheme()
