"""保存本輪搜尋、重設事件可觀測性的安裝原始碼證據；不讀取秘密設定。"""
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
SCRIPT = r'''
const fs=require('fs'),p=require('path'),crypto=require('crypto');
const mr=require('module').createRequire(require.resolve('@medusajs/medusa'));
const root=p.dirname(require.resolve('@medusajs/medusa'));
const busFile=p.join(p.dirname(mr.resolve('@medusajs/event-bus-local')),'services/event-bus-local.js');
const searchFile=p.join(root,'api/store/products/search/route.js');
const resetFile=p.join(root,'api/auth/[actor_type]/[auth_provider]/reset-password/route.js');
const sources={};for(const [name,file] of Object.entries({event_bus:busFile,search:searchFile,reset_http:resetFile})){
 const s=fs.readFileSync(file,'utf8');sources[name]={sha256:crypto.createHash('sha256').update(s).digest('hex')};
 if(name==='event_bus')sources[name].logs_only_with_subscribers=/if \(totalSubscribers &&/.test(s);
 if(name==='search')sources[name].http_method_get=s.includes('exports.GET = GET');
 if(name==='reset_http')sources[name].hides_workflow_errors=s.includes('throwOnError: false');
}
console.log(JSON.stringify({application_version:require('@medusajs/medusa/package.json').version,sources,
 conclusion:'Missing event log is not evidence of no emitted event: local event bus logs Processing only with subscribers.'}));
'''

if __name__ == '__main__':
    result = subprocess.run(['docker', 'exec', '-i', 'mirage-commerce-real-medusa-1', 'node'], input=SCRIPT,
                            capture_output=True, text=True, encoding='utf-8', timeout=20)
    if result.returncode: raise SystemExit('原始碼證據讀取失敗，未輸出可能含秘密的錯誤')
    proof = json.loads(result.stdout)
    from run_medusa_native_transfer_tokens import db_query
    proof['reset_workflow_persisted_executions'] = db_query("SELECT json_build_object('workflow_id','generate-reset-password-token','count',count(*),'read_only',true) FROM workflow_execution WHERE workflow_id='generate-reset-password-token' AND deleted_at IS NULL")
    (HERE / 'reports/medusa-demo-v9-followup-source-proof.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'source_files_checked': len(proof['sources']), 'application_version': proof['application_version']}))
