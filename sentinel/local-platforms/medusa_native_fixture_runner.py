"""以原生 Medusa exec 執行本機測試資料建立，完整輸出只存 ignored .runtime。"""
import json
from pathlib import Path
import subprocess
import uuid

HERE = Path(__file__).resolve().parent
CONTAINER = 'mirage-commerce-real-medusa-1'


def native_fixture(payload):
    run_id = payload.setdefault('run_id', uuid.uuid4().hex[:10])
    runtime = HERE / '.runtime'
    runtime.mkdir(exist_ok=True)
    source = HERE / 'medusa_native_demo_fixtures.cjs'
    config = runtime / ('native-input-' + run_id + '.json')
    config.write_text(json.dumps(payload), encoding='utf-8')
    remote_script = '/tmp/msdss-demo-fixtures-' + run_id + '.cjs'
    remote_input = '/tmp/msdss-demo-input-' + run_id + '.json'
    for local, remote in [(source, remote_script), (config, remote_input)]:
        # rootfs唯讀；由容器內程序寫既有可寫tmpfs，不改映像或服務設定。
        subprocess.run(['docker', 'exec', '-i', CONTAINER, 'node', '-e',
                        "require('fs').writeFileSync(process.argv[1],require('fs').readFileSync(0))", remote],
                       input=local.read_bytes(), check=True, capture_output=True)
    command = "const p=require('path');require(p.join(p.dirname(require.resolve('@medusajs/medusa')),'commands/exec.js')).default({file:process.argv[1],args:[process.argv[2]]})"
    completed = subprocess.run(['docker', 'exec', CONTAINER, 'node', '-e', command, remote_script, remote_input],
                               capture_output=True, text=True, encoding='utf-8', timeout=180)
    (runtime / ('native-log-' + run_id + '.txt')).write_text(completed.stdout + completed.stderr, encoding='utf-8')
    lines = [x.split('MSDSS_PRIVATE_RESULT=', 1)[1] for x in completed.stdout.splitlines() if x.startswith('MSDSS_PRIVATE_RESULT=')]
    if completed.returncode or len(lines) != 1:
        raise RuntimeError('原生建立未完成；詳情僅保存在 .runtime/native-log-' + run_id + '.txt')
    result = json.loads(lines[0])
    (runtime / ('native-result-' + run_id + '.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    result = native_fixture({'mode': 'catalog'})
    safe = {name: {k: value.get(k) for k in ('id', 'title', 'value', 'label', 'code')} for name, value in result.items() if isinstance(value, dict)}
    (HERE / 'reports/medusa-demo-v9-created-fixtures.json').write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(safe, ensure_ascii=False))
