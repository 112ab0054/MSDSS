"""Pure unit fixtures only. These are not live HTTP evidence or dataset samples."""
import copy
import unittest
from core import grouped, model_input, near_fingerprint, sha, verify_evidence
from collect import valid_search_response
from export_reviewed import approved
from quality import inspect
from scenarios import cases, ASSIGNMENT, base_cases, build_catalog


def fixture(sid, platform='bagisto', family=None, session=None, fingerprint=None):
    request = {'method': 'GET', 'path': '/products', 'query': {'query': [sid]}, 'headers': {}, 'body': None}
    return {'sample_id': sid, 'input': request,
        'annotation': {'proposed_label': 'normal', 'eligible_for_review': True},
        'metadata': {'platform': platform, 'session_group': session or sid, 'family_id': family,
            'pair_group': None, 'fingerprint': fingerprint or sha(request), 'near_fingerprint': sha(sid)}}


class DatasetTests(unittest.TestCase):
    def test_json_200_without_product_collection_is_not_business_success(self):
        for platform in ASSIGNMENT:
            self.assertFalse(valid_search_response(platform, {'message': 'ok'}))
        self.assertFalse(valid_search_response('shopware', {'elements': [{'title': 'missing id'}]}))
        self.assertTrue(valid_search_response('shopware', {'elements': []}))
        self.assertTrue(valid_search_response('bagisto', [{'id': 123}]))
        self.assertTrue(valid_search_response('sylius', {'hydra:member': [{'code': 'fixture'}]}))

    def test_missing_http_evidence_never_validates(self):
        self.assertFalse(verify_evidence(fixture('unit-only')))

    def test_credentials_redacted_but_other_original_values_preserved(self):
        row = {'method': 'POST', 'path': '/products?token=private-token&query=shirt', 'operation_path': '/products',
            'request_headers': {'Authorization': 'Bearer private-jwt', 'X-Request-ID': 'uuid123',
                'sw-access-key': 'private-api-key', 'Content-Type': 'application/json'},
            'request_body': {'password': 'private-password', 'confirmPassword': 'confirm-private',
                'productId': 'actual-product-id', 'email': 'test@example.test', 'firstName': "O'Connor"}}
        result = model_input(row)
        for value in ('private-token', 'private-jwt', 'private-api-key', 'private-password', 'confirm-private'):
            self.assertNotIn(value, str(result))
        self.assertEqual(result['body']['productId'], 'actual-product-id')
        self.assertEqual(result['body']['email'], 'test@example.test')
        self.assertEqual(result['headers']['X-Request-ID'], 'uuid123')
        self.assertEqual(result['body']['firstName'], "O'Connor")
        self.assertEqual(set(result), {'method', 'path', 'raw_query', 'query', 'headers', 'body', 'raw_body', 'path_parameters'})

    def test_complete_request_and_legacy(self):
        from core import evidence_digest_mode, sha
        row = {'method': 'GET', 'operation_path': '/products/{id}',
               'path': '/products/item-1?order=desc&page=2&per_page=10&type=simple',
               'request_headers': {'X-Locale': 'en', 'X-Custom': '<svg onload="void(0)">',
                                   'Cookie': 'private', 'User-Agent': 'Browser'},
               'request_body': {'nested': {'new_field': 'kept'}}}
        new = model_input(row)
        self.assertEqual(set(new['query']), {'order', 'page', 'per_page', 'type'})
        self.assertEqual(new['headers']['X-Custom'], '<svg onload="void(0)">')
        self.assertEqual(new['headers']['Cookie'], '[REDACTED]')
        self.assertEqual(new['path'], '/products/item-1')
        self.assertEqual(new['raw_query'], 'order=desc&page=2&per_page=10&type=simple')
        self.assertEqual(new['path_parameters'], {'id': 'item-1'})
        self.assertEqual(new['body']['nested']['new_field'], 'kept')
        self.assertEqual(model_input(row, version=1)['headers'], {})
        self.assertEqual(evidence_digest_mode(b'{\n}\n', sha(b'{\r\n}\r\n')), 'original_crlf_reconstructed')
        self.assertIsNone(evidence_digest_mode(b'{changed}', sha(b'{original}')))

    def test_transitive_grouping_and_global_family(self):
        a = fixture('a', family='sql.same', session='s1')
        b = fixture('b', platform='shopware', family='sql.same', session='s2')
        c = fixture('c', platform='shopware', session='s2')
        d = fixture('d')
        groups = grouped([a, b, c, d])
        self.assertEqual(groups[0], groups[1])
        self.assertEqual(groups[1], groups[2])
        self.assertNotEqual(groups[0], groups[3])

    def test_outer_fold_purges_cross_platform_family_overlap(self):
        rows = [fixture('a', family='shared'), fixture('b', platform='sylius', family='shared'),
                fixture('c', platform='shopware')]
        fold = next(f for f in inspect(rows)['proposed_outer_folds'] if f['test_platform'] == 'sylius')
        self.assertEqual(fold['outer_train_candidate_ids'], ['c'])
        self.assertEqual(fold['purged_cross_platform_overlap_ids'], ['a'])
        self.assertEqual(fold['outer_test_candidate_ids'], ['b'])

    def test_pending_review_exports_nothing(self):
        row = fixture('a')
        self.assertEqual(approved([row], [{'sample_id': 'a', 'decision': '', 'candidate_sha256': sha(row)}]), [])

    def test_approval_cannot_override_missing_evidence_eligibility(self):
        row = fixture('a'); row['annotation']['eligible_for_review'] = False
        decision = {'sample_id': 'a', 'decision': 'approve', 'candidate_sha256': sha(row),
                    'final_label': 'normal', 'reviewer': 'unit-fixture', 'reason': 'unit test only'}
        with self.assertRaises(ValueError): approved([row], [decision])

    def test_approval_requires_matching_candidate_hash(self):
        row = fixture('a')
        decision = {'sample_id': 'a', 'decision': 'approve', 'candidate_sha256': 'wrong',
                    'final_label': 'normal', 'reviewer': 'unit-fixture', 'reason': 'unit test only'}
        with self.assertRaises(ValueError): approved([row], [decision])

    def test_conflicting_proposed_labels_flagged(self):
        a = fixture('a', fingerprint='same'); b = fixture('b', fingerprint='same')
        b['annotation']['proposed_label'] = 'sqli'
        self.assertEqual(inspect([a, b])['conflicting_label_fingerprints'], ['same'])

    def test_no_number_normalization_in_new_fingerprints(self):
        a = fixture('a')['input']; b = copy.deepcopy(a)
        a['query'] = {'query': ["' OR 1=1 -- "]};b['query'] = {'query': ["' OR 22=22 -- "]}
        self.assertNotEqual(near_fingerprint(a), near_fingerprint(b))

    def test_catalog_counts_partition_and_no_external_exfiltration(self):
        all_ids = set(); families = []
        for platform in ASSIGNMENT:
            rows = cases(platform)
            self.assertGreater(len(rows),len(base_cases()))
            self.assertEqual(sum(r['role']=='case' for r in rows),len(base_cases()))
            family = {r['family_id'] for r in rows if r['family_id']}
            # Same source family stays globally named across platforms; it is not independent data.
            for earlier in families:self.assertEqual(family,earlier)
            families.append(family)
            for row in rows:
                self.assertNotIn(row['case_id'], all_ids);all_ids.add(row['case_id'])
                self.assertEqual(row['review_status'], 'pending_human_review')
                if row['proposed_label'] != 'normal' and row['value'] is not None:
                    for bad in ('document.cookie', 'fetch(', 'http://', 'https://', 'DROP ', 'DELETE ', 'WAITFOR'):
                        self.assertNotIn(bad, row['value'])
                    if 'SLEEP(' in row['value']:
                        self.assertEqual(row['workflow_id'],'sql-time-pair')
                        self.assertTrue('SLEEP(0)' in row['value'] or 'SLEEP(0.05)' in row['value'])

    def test_catalog_covers_every_declared_dimension_without_claiming_execution(self):
        catalog=build_catalog();covered={tag for row in catalog['base_cases'] for tag in row['coverage_tags']}
        self.assertTrue({t['id'] for t in catalog['taxonomy']} <= covered)
        self.assertFalse(catalog['executed']);self.assertFalse(catalog['training_ready'])
        self.assertTrue(all(not b['executed'] and not b['success_verified'] for b in catalog['base_cases']))

    def test_non_http_sources_and_absent_payloads_cannot_enter_runner(self):
        for case in base_cases():
            if not case['http_visible'] or case['value'] is None:
                self.assertFalse(case['can_collect_http'])
        self.assertTrue(any(b['value'] is None and 'sqli.oob' in b['coverage_tags'] for b in base_cases()))

    def test_variants_retain_parent_family_and_paired_workflows(self):
        bases={b['base_case_id']:b for b in base_cases()}
        for b in bases.values():
            if b['variant_of']:self.assertEqual(b['family_id'],bases[b['variant_of']]['family_id'])
        for workflow in ('sql-blind-pair','sql-time-pair'):
            members=[b for b in bases.values() if b['workflow_id']==workflow]
            self.assertEqual(len(members),2);self.assertTrue(all(b['workflow_stage'] for b in members))


if __name__ == '__main__':
    unittest.main()
