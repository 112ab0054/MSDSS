"""透過本機Sentinel測試真實Medusa正常購物；只用原生離線付款。"""
import argparse
import json
from pathlib import Path
from http_evidence import EvidenceClient
from run_medusa_demo_flow import run

HERE = Path(__file__).resolve().parent


class DemoClient(EvidenceClient):
    def request(self, method, path, body=None, template=None, **kwargs):
        result = super().request(method, path, body, template, **kwargs)
        print(f'{len(self.rows):02d} {method} {template or path.split("?")[0]} HTTP {self.rows[-1]["status"]}', flush=True)
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-url', default='http://127.0.0.1:18085')
    p.add_argument('--config', type=Path, default=HERE / '.runtime/medusa-demo.json')
    p.add_argument('--output', type=Path, default=HERE / 'reports/medusa-demo-v9-flow.json')
    args = p.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    client = DemoClient('medusa', args.base_url, args.output, {'x-publishable-api-key': config['publishable_api_key']})
    try:
        run(client)
    except (RuntimeError, KeyError, TypeError, ValueError) as error:
        client.save('failed', str(error) if isinstance(error, RuntimeError) else '回應結構未符合流程預期')
        print('FAILED:', type(error).__name__, 'see redacted report', flush=True)
        return 1
    outcome = json.loads(args.output.read_text(encoding='utf-8'))['outcome']
    print('CORE SHOPPING FLOW PASSED; detailed outcome:', outcome, flush=True)
    return 0


if __name__ == '__main__': raise SystemExit(main())
