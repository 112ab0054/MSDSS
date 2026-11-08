"""以穩定的合成人物取代候選中的測試姓名；不修改實測證據或攻擊字串。"""
import re
from build_small_dataset import finalize, sha

# 網域保留作範例用途，不會誤用真實使用者信箱。
PEOPLE = [('Emily', 'Chen', 'emily.chen', 'example.com'),
          ('Daniel', 'Lin', 'daniel.lin', 'example.org'),
          ('Olivia', 'Martin', 'olivia.martin', 'example.net'),
          ('Lucas', 'Wang', 'lucas.wang', 'example.com'),
          ('Sophia', 'Taylor', 'sophia.taylor', 'example.org')]
OLD_EMAIL = re.compile(r'^(?:phase1-[0-9a-f]+|customer)@example\.test$', re.I)


def apply_identities(rows):
    """同一歷史流程固定使用同一人物，登入與地址不隨每列隨機換人。

    只替換指定姓名／email 欄位中已知的測試值；SQLi/XSS 與外部 payload
    不符合替換條件，因此保留。新 ID 仍由新輸入計算，並同步更新對照 ID。
    """
    sources = sorted({r['metadata']['historical_source_report'] for r in rows})
    profiles = {source: PEOPLE[i % len(PEOPLE)] for i, source in enumerate(sources)}
    ids = {}
    for row in rows:
        meta, request = row['metadata'], row['input']
        first, last, local, domain = profiles[meta['historical_source_report']]

        def replace(value, field=''):
            if isinstance(value, dict):
                return {key: replace(child, key.lower().replace('_', '')) for key, child in value.items()}
            if isinstance(value, list):
                return [replace(child, field) for child in value]
            if field == 'firstname' and value == 'MSDSS':
                return first
            if field == 'lastname' and value == 'Test':
                return last
            if field in {'email', 'username'} and isinstance(value, str) and OLD_EMAIL.fullmatch(value):
                # 保留原先兩個不同帳號的區別，避免替換後意外合併樣本。
                suffix = '.contact' if value.lower().startswith('customer@') else ''
                return local + suffix + '@' + domain
            return value

        request['body'] = replace(request.get('body'))
        request['query'] = replace(request.get('query', {}))
        finalize(request, meta['operation_path'])
        old = row['sample_id']
        row['sample_id'] = sha([meta['split'], request, meta['payload']])
        ids[old] = row['sample_id']
        if old != row['sample_id']:
            meta['previous_sample_id'] = old
            meta['identity_origin'] = 'synthetic_people_v1_not_live_verified'
    for row in rows:
        meta = row['metadata']
        if meta.get('control_sample_id'):
            meta['control_sample_id'] = ids[meta['control_sample_id']]
    return rows
