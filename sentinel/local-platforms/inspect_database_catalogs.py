"""只讀既有 Bagisto／Sylius 資料庫的公開選項；不啟動應用、不部署、不輸出憑證。"""
import argparse
import csv
import io
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

QUERIES = {
    'bagisto': {
        'languages': 'SELECT id,code,name,direction FROM locales ORDER BY code',
        'channel_languages': 'SELECT c.code AS channel_code,l.code AS locale_code FROM channel_locales cl JOIN channels c ON c.id=cl.channel_id JOIN locales l ON l.id=cl.locale_id ORDER BY c.code,l.code',
        'countries': 'SELECT code,name FROM countries ORDER BY code',
        'states': 'SELECT country_code,code,default_name FROM country_states ORDER BY country_code,code',
        'currencies': 'SELECT code,name FROM currencies ORDER BY code',
        'channel_currencies': 'SELECT c.code AS channel_code,cu.code AS currency_code FROM channel_currencies cc JOIN channels c ON c.id=cc.channel_id JOIN currencies cu ON cu.id=cc.currency_id ORDER BY c.code,cu.code',
    },
    'sylius': {
        'languages': 'SELECT code FROM sylius_locale ORDER BY code',
        'channel_languages': 'SELECT c.code AS channel_code,l.code AS locale_code FROM sylius_channel_locales cl JOIN sylius_channel c ON c.id=cl.channel_id JOIN sylius_locale l ON l.id=cl.locale_id ORDER BY c.code,l.code',
        'countries': 'SELECT id,code,enabled FROM sylius_country ORDER BY code',
        'provinces': 'SELECT c.code AS country_code,p.code,p.name FROM sylius_province p JOIN sylius_country c ON c.id=p.country_id ORDER BY c.code,p.code',
        'currencies': 'SELECT code FROM sylius_currency ORDER BY code',
    },
}


def query(platform, sql):
    name = f'msdss-phase1-{platform}-db-1'
    info = json.loads(subprocess.check_output(['docker', 'inspect', name], text=True))[0]
    if info['Config']['Labels'].get('com.docker.compose.project') != f'msdss-phase1-{platform}':
        raise ValueError('非本次獨立資料庫，拒絕查詢')
    command = ['docker', 'exec', '-i', name, 'sh', '-c',
               'exec mariadb --batch --raw --user="$MYSQL_USER" --password="$MYSQL_PASSWORD" "$MYSQL_DATABASE"']
    result = subprocess.run(command, input='SET SESSION TRANSACTION READ ONLY; START TRANSACTION; ' + sql + '; ROLLBACK;',
                            capture_output=True, text=True, encoding='utf-8', timeout=20)
    if result.returncode:
        raise RuntimeError('唯讀查詢失敗；不輸出可能含連線資訊的錯誤')
    return list(csv.DictReader(io.StringIO(result.stdout), delimiter='\t'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('platform', choices=QUERIES)
    args = parser.parse_args()
    report = {'platform': args.platform, 'checked_at': datetime.now(timezone.utc).isoformat(),
              'read_only': True, 'scope': 'database catalog; channel assignments listed separately; no HTTP or full business verification'}
    for name, sql in QUERIES[args.platform].items():
        report[name] = query(args.platform, sql)
    path = HERE / 'reports' / (args.platform + '-database-catalog.json')
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(path), 'counts': {k: len(v) for k, v in report.items() if isinstance(v, list)},
                      'languages': report['languages'], 'channel_languages': report['channel_languages']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
