"""僅讀取安全設定、套件原始碼與公開選項數量，釐清文件的前置條件。"""
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCRIPT = r'''
const fs=require('fs'),p=require('path'),crypto=require('crypto');
const r=require('module').createRequire(require.resolve('@medusajs/medusa'));
const raw=require(p.join(process.cwd(),'medusa-config.js')),c=raw.default||raw;
const mods=Array.isArray(c.modules)?c.modules:Object.values(c.modules||{});
const auth=mods.find(x=>String(x.resolve||'').includes('/auth')||String(x.resolve||'').endsWith('auth'));
const expressFile=p.join(p.dirname(r.resolve('@medusajs/framework/http')),'express-loader.js');
const expressSource=fs.readFileSync(expressFile,'utf8');
const defaultSecurity=require(expressFile).resolveSessionCookieSecurity({isProduction:process.env.NODE_ENV==='production',isStaging:process.env.NODE_ENV==='staging'});
const overrides=c.projectConfig?.cookieOptions||{},security={...defaultSecurity};
for(const key of ['secure','sameSite','domain','path'])if(overrides[key]!==undefined)security[key]=overrides[key];
const translation=mods.find(x=>String(x.resolve||'').includes('translation'));
let providerEntry;try{providerEntry=r.resolve('@medusajs/fulfillment-manual')}catch(e){providerEntry=r.resolve('@medusajs/medusa/fulfillment-manual')}
const providerFile=p.join(p.dirname(providerEntry),'services/manual-fulfillment.js');
const provider=fs.readFileSync(providerFile,'utf8');
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
console.log('SAFE_PROOF='+JSON.stringify({
 application_version:require('@medusajs/medusa/package.json').version,node_env:process.env.NODE_ENV,
 effective_session_cookie_security:security,session_source_sha256:sha(expressSource),
 session_source_reason:'production/staging default Secure=true, sameSite=lax; cookieOptions overrides applied',
 translation_module_disabled:translation?.disable===true,translation_explicit_flag:c.featureFlags?.translation??null,
 auth_provider_ids:auth?.options?.providers?.map(x=>x.id)||[],mfa_encryption_key_configured:!!auth?.options?.mfa?.encryption_key,
 notification_providers:mods.filter(x=>String(x.resolve||'').includes('notification')).flatMap(x=>(x.options?.providers||[]).map(v=>({id:v.id,channels:v.options?.channels}))),
 project_subscriber_files:fs.existsSync('src/subscribers')?fs.readdirSync('src/subscribers'):[],
 manual_fulfillment:{source_sha256:sha(provider),can_calculate_false:/async canCalculate\(\)\s*\{\s*return false;/.test(provider),
  calculate_price_explicit_error:provider.includes('Manual fulfillment does not support price calculation'),
  snippets:provider.split('\n').map((l,i,a)=>/async canCalculate|async calculatePrice/.test(l)?a.slice(i,i+4).join('\n'):'').filter(Boolean)}
}));
'''


def main():
    result = subprocess.run(['docker', 'exec', '-i', 'mirage-commerce-real-medusa-1', 'node'],
                            input=SCRIPT, capture_output=True, text=True, timeout=20)
    if result.returncode: raise RuntimeError('安全設定查核失敗，不輸出可能含秘密的錯誤')
    safe = json.loads(next(x for x in result.stdout.splitlines() if x.startswith('SAFE_PROOF=')).split('=', 1)[1])
    sql = "BEGIN READ ONLY; SELECT json_build_object('promotion',(SELECT count(*) FROM promotion WHERE deleted_at IS NULL),'product_collection',(SELECT count(*) FROM product_collection WHERE deleted_at IS NULL),'product_tag',(SELECT count(*) FROM product_tag WHERE deleted_at IS NULL),'product_type',(SELECT count(*) FROM product_type WHERE deleted_at IS NULL),'return_reason',(SELECT count(*) FROM return_reason WHERE deleted_at IS NULL)); ROLLBACK;"
    result = subprocess.run(['docker', 'exec', '-i', 'mirage-commerce-real-db-1', 'sh', '-c',
                             'exec psql -X -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -A'],
                            input=sql, capture_output=True, text=True, timeout=15)
    if result.returncode: raise RuntimeError('公開選項數量唯讀查核失敗')
    safe['database_non_deleted_counts'] = json.loads(result.stdout)
    safe['read_only_inspection'] = True
    snapshot = ROOT / 'sentinel/analysis/history/2026-11-09/medusa-77-user-reference.md'
    safe['user_document_snapshot'] = snapshot.relative_to(ROOT).as_posix()
    safe['user_document_sha256'] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    reports = HERE / 'reports'
    prior = json.loads((reports / 'medusa-demo-v9-remaining.json').read_text(encoding='utf-8'))
    shipping = next(x for r in prior['requests'] if r['operation_path'] == '/store/shipping-options' and r['status'] == 200
                    for x in r['response_body'].get('shipping_options', []) if x.get('provider_id') == 'manual_manual')
    safe['tested_shipping_option'] = {k: shipping.get(k) for k in ('id', 'provider_id', 'price_type', 'amount')}
    order = next(r['response_body']['order'] for r in prior['requests'] if r['operation_path'] == '/store/orders/{id}' and r['status'] == 200)
    safe['tested_return_item_quantities'] = [{k: i.get('detail', {}).get(k) for k in ('quantity', 'fulfilled_quantity', 'return_requested_quantity')} for i in order['items']]
    (reports / 'medusa-demo-v9-document-environment-proof.json').write_text(json.dumps(safe, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(safe, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
