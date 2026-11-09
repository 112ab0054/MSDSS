"""真實Medusa：比較直連與全路徑gateway的回應；逐UUID核對模型分數。"""
import json
from pathlib import Path
from http_evidence import EvidenceClient
from import_gateway_scores import collect
from run_medusa_document_checks import TLSClient

HERE = Path(__file__).resolve().parent


def main():
    cfg = json.loads((HERE / '.runtime/medusa-demo.json').read_text(encoding='utf-8-sig'))
    key = cfg['publishable_api_key']
    report = HERE / 'reports/medusa-gateway-all-paths-2026-11-10.json'
    c = TLSClient('https://127.0.0.1:18443', report, key, HERE / '.runtime/medusa-document-check-tls.crt')
    direct = EvidenceClient('medusa', 'http://127.0.0.1:9100', HERE / '.runtime/all-paths-direct.json', {'x-publishable-api-key': key})
    cases = [('GET','/store/products?limit=1',None), ('GET','/admin/users',None),
             ('GET','/msdss-not-a-real-api',None), ('OPTIONS','/store/products',None),
             ('HEAD','/store/products',None), ('POST','/store/products',{})]
    summaries = []
    for method,path,body in cases:
        allowed = {200,201,204,400,401,403,404,405,422}
        response = c.request(method,path,body,allowed_status=allowed)
        expected = direct.request(method,path,body,allowed_status=allowed)
        c.verify(c.rows[-1]['status'] == direct.rows[-1]['status'], 'gateway與真實Medusa直連狀態一致：'+method+' '+path, -1)
        if path.startswith('/store/products?'):
            c.verify([x['id'] for x in response['products']] == [x['id'] for x in expected['products']], 'gateway查回商品ID與真實直連一致', -1)
        summaries.append({'method':method,'path':path,'gateway_status':c.rows[-1]['status'],'direct_status':direct.rows[-1]['status'],'request_id':c.rows[-1]['request_id']})
    c.evidence_metadata['scope'] = 'real network integration; not model accuracy; direct backend requests not counted as gateway predictions'
    c.save('passed')
    scores = collect((HERE / '.runtime/gateway-all-paths-18443.log').read_text(encoding='utf-8'),json.loads(report.read_text(encoding='utf-8')))
    (HERE / 'reports/medusa-gateway-all-paths-scores-2026-11-10.json').write_text(json.dumps(scores,indent=2),encoding='utf-8')
    print(json.dumps({'gateway_requests':len(c.rows),'actual_prediction_matches':len(scores['scores']),'direct_status_matches':summaries},ensure_ascii=False))


if __name__ == '__main__': main()
