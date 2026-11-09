"""Verify previously missing distinctions, without asserting holdout accuracy."""
import json
import unittest
from features import features, raw_ngrams, feature_count, VERSION, layout
from header_contracts import documented_headers


class V5Tests(unittest.TestCase):
    def test_previous_full_vector_collision_is_resolved(self):
        def request(value):return {'method':'POST','path':'/products','headers':{'Content-Type':'application/json'},
                                  'raw_query':'','raw_body':json.dumps({'note':value},separators=(',',':'))}
        self.assertNotEqual(features(request('${void(0)}')),features(request('blue shirt')))

    def test_raw_analyzer_preserves_case_space_and_encoding(self):
        self.assertIn('A  B',set(raw_ngrams('A  B')))
        self.assertNotEqual(features({'raw_body':'A  B'}),features({'raw_body':'A B'}))
        self.assertNotEqual(features({'raw_body':'AbCd'}),features({'raw_body':'abcd'}))
        self.assertNotEqual(features({'raw_query':'q=%3Cscript%3E'}),features({'raw_query':'q=<script>'}))
        self.assertFalse(layout()['vocabulary_fit'])

    def test_all_channels_distinguish_js_templates(self):
        for key in ('raw_body','raw_query','path'):
            self.assertNotEqual(features({key:'${void(0)}'}),features({key:'blue shirt'}))
        self.assertNotEqual(features({'headers':{'X-Locale':'${void(0)}'}}),features({'headers':{'X-Locale':'blue shirt'}}))

    def test_sensitive_values_remain_excluded_and_shape_is_portable(self):
        self.assertEqual(features({'headers':{'Authorization':'short'}}),features({'headers':{'Authorization':'very-long-private-value'}}))
        headers,_=documented_headers()
        self.assertEqual(VERSION,5);self.assertEqual(feature_count(headers),2402)
        self.assertEqual(len(features({},headers)),2402)


if __name__=='__main__':unittest.main()
