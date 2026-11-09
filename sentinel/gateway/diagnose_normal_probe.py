"""Medusa正常查詢的離線分數診斷；不發送HTTP、不修改模型或原接線紀錄。"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import csv
import httpx
import numpy as np
from starlette.requests import Request
from xgboost import DMatrix
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'model'))
from predict import Predictor
from features import features
from diagnose_v4_errors import names
import app as gateway


def diagnose(output):
    if output.exists():raise ValueError('輸出已存在，請另選目錄')
    predictor=Predictor(HERE/'model');predictor.self_test()
    manifest_before=(HERE/'model/bundle-manifest.json').read_bytes()
    queries=['query=cotton','query=cotton&page=2','q=cotton','q=cotton&limit=10&offset=0']
    details=[];decompositions=[];feature_names=names(predictor.header_names)
    with httpx.Client() as client:
        for profile in ('minimal','httpx_defaults','httpx_accept_json','httpx_accept_application_wildcard','api_document_headers'):
            for query in queries:
                url='http://127.0.0.1:8080/store/products?'+query
                if profile=='minimal':request=httpx.Request('GET',url)
                elif profile.startswith('httpx'):
                    request=client.build_request('GET',url)
                    if profile=='httpx_accept_json':request.headers['accept']='application/json'
                    elif profile=='httpx_accept_application_wildcard':request.headers['accept']='application/*'
                else:request=httpx.Request('GET',url,headers={'Accept':'application/json','x-publishable-api-key':'[REDACTED]'})
                scope={'type':'http','method':'GET','path':'/store/products','raw_path':b'/store/products',
                       'query_string':request.url.query,'headers':request.headers.raw,'scheme':'http',
                       'server':('127.0.0.1',8080),'client':('127.0.0.1',12345),'http_version':'1.1'}
                sample=gateway.model_request(Request(scope),b'')
                result=predictor.predict(sample)
                identifier=profile+':'+query
                details.append({'case':identifier,'header_profile':profile,'raw_query':query,
                                'headers':sample['headers'],'label':result['label'],'scores':result['probabilities'],
                                'scope':'offline model-only probe; no actual API/business acceptance verified'})
                vector=np.asarray([features(sample,predictor.header_names)],dtype=np.float32)
                contribution=predictor.model.get_booster().predict(DMatrix(vector),pred_contribs=True)[0]
                margins=predictor.model.get_booster().predict(DMatrix(vector),output_margin=True)[0]
                if not np.allclose(contribution.sum(axis=1),margins,atol=2e-5):raise RuntimeError('分數分解未守恆')
                delta=contribution[1,:-1]-contribution[0,:-1]
                for index in np.argsort(-delta)[:8]:
                    decompositions.append({'case':identifier,'feature':feature_names[index],'value':float(vector[0,index]),
                                           'sql_minus_normal_margin_contribution':float(delta[index])})
    assert (HERE/'model/bundle-manifest.json').read_bytes()==manifest_before
    model_sha=hashlib.sha256((HERE/'model/model.json').read_bytes()).hexdigest()
    output.mkdir(parents=True)
    report={'model_sha256':model_sha,'model_modified':False,'http_executed':False,'cases':details,
            'notes':['full headers of original TCP probe were not saved; URL alone does not uniquely reproduce its score',
                     'q/limit/offset taken from backend/static/openapi/store.yaml; query/page not documented product-list parameters',
                     'scores are uncalibrated; these 12 probes are not a false-positive-rate evaluation',
                     'API key is a redacted placeholder for model-only analysis, not a valid credential or HTTP success claim']}
    (output/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with (output/'score-contributions.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(decompositions[0]));writer.writeheader();writer.writerows(decompositions)
    return details


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    print(json.dumps(diagnose(p.parse_args().output),ensure_ascii=False))
