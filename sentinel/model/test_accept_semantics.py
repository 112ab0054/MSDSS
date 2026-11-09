"""Accept語意修正的正反例；不以保留集分數當測試條件。"""
import copy
import unittest
from features import features, header_features, accept_wildcard_comments, VERSION


class AcceptSemanticsTests(unittest.TestCase):
    def test_legal_media_ranges_do_not_count_as_sql_comments(self):
        for value in ['*/*','application/*','application/json, */*;q=0.8','text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8']:
            with self.subTest(value=value):
                vector=header_features({'Accept':value},['accept'])
                self.assertEqual(vector[14],0)
                self.assertEqual(vector[31],0)  # 18 + present + SQL-comment offset12
        self.assertEqual(VERSION,6)

    def test_other_comment_content_is_retained(self):
        self.assertGreater(header_features({'X-Test':'/*sql*/'},[])[14],0)
        self.assertGreater(header_features({'Accept':'*/*;note="/*sql*/"'},[])[14],0)
        self.assertGreater(header_features({'Accept':'*/* -- text'},[])[14],0)
        self.assertEqual(accept_wildcard_comments('*/*, broken'),0)
        self.assertEqual(accept_wildcard_comments('*/*,'),0)
        self.assertEqual(accept_wildcard_comments('*/json'),0)
        self.assertEqual(accept_wildcard_comments(['*/*','application/*']),2)

    def test_raw_values_and_other_channels_are_unchanged(self):
        request={'headers':{'Accept':'*/*'},'raw_query':'q=/*sql*/','raw_body':'/*sql*/'}
        before=copy.deepcopy(request);vector=features(request,[])
        self.assertEqual(request,before)
        self.assertGreater(vector[20],0)  # query SQL-comment slot
        self.assertGreater(vector[36],0)  # body SQL-comment slot
        self.assertNotEqual(features({'headers':{'Accept':'*/*'}},[]),features({'headers':{'Accept':'application/json'}},[]))


if __name__=='__main__':unittest.main()
