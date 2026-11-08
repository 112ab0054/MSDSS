"""動態綁定單元測試；不冒充電商實機通過。"""
import unittest
from collect_small_v2 import bind_body


class LiveBindingTests(unittest.TestCase):
    def test_current_ids_and_credentials_replace_historical_values(self):
        planned = {'productId': 'old', 'email': 'old@example.test', 'password': '[REDACTED]', 'quantity': 2}
        live = {'productId': 'current', 'email': 'fresh@example.test', 'password': 'fixture-private'}
        actual = bind_body(planned, live)
        self.assertEqual(actual['productId'], 'current')
        self.assertEqual(actual['email'], 'fresh@example.test')
        self.assertEqual(actual['password'], 'fixture-private')
        self.assertEqual(actual['quantity'], 2)

    def test_attack_target_is_not_replaced_by_normal_id(self):
        self.assertEqual(bind_body({'productId': "' OR 'a'='a' --"}, {'productId': 'current'}, 'productId'),
                         {'productId': "' OR 'a'='a' --"})

    def test_missing_dynamic_binding_never_reuses_historical_id(self):
        with self.assertRaisesRegex(ValueError, '缺少當次動態欄位'):
            bind_body({'address': {'countryId': 'old'}}, {'address': {}})


if __name__ == '__main__':
    unittest.main()
