"""Signature generation tests"""

from __future__ import unicode_literals

import responses
import unittest

from six.moves.urllib.parse import parse_qs

from mediafire.api import MediaFireApiError
from tests.api.base import MediaFireApiTestCase

CALL_SIGNATURES = [
    '94c813c787e6441d9e73314a400894fa',
    'dba771fdd2739eda89ca03a06cdf4df7'
]


class TestV2CallSignature(MediaFireApiTestCase):
    """Test V2 Signature generation"""
    def setUp(self):
        """Set up test"""
        super(TestV2CallSignature, self).setUp()

        session_token = {
            'session_token': 'a' * 144,
            'secret_key': '1000000000',
            'time': '0.0',
            'pkey': '111',
            'ekey': '222',
        }
        self.api.set_session_token(session_token)
        self.url = self.build_url('user/get_info')

    @responses.activate
    def test_signature_values(self):
        """Test signature generation and update"""

        body = """
        {"response": {
            "user_info": {}, "new_key": "yes", "result": "Success"}
        }
        """

        responses.add(responses.POST, self.url, body=body, status=200,
                      content_type="application/json")
        # original secret key
        self.api.user_get_info()
        # secret key is (1000000000 * 16807) % 2147483647 = 792978578
        self.api.user_get_info()

        query = responses.calls[0].request.body
        params = parse_qs(query)

        self.assertEqual(params['signature'][0], CALL_SIGNATURES[0])

        query = responses.calls[1].request.body
        params = parse_qs(query)

        self.assertEqual(params['signature'][0], CALL_SIGNATURES[1])

    @responses.activate
    def test_signature_update_on_error(self):
        """Test that error response from server updates signature"""

        def callback(request):
            params = parse_qs(request.body)
            signature = params['signature'][0]

            if signature == CALL_SIGNATURES[0]:
                body = """
                {"response": {
                    "new_key": "yes",
                    "result": "Error",
                    "message": "Signature test error",
                    "error": "101"}}
                """
                status = 500
            elif signature == CALL_SIGNATURES[1]:
                body = """
                {"response": {
                    "user_info": {}, "new_key": "yes", "result": "Success"}
                }"""
                status = 200
            else:
                raise Exception("Unexpected signature: {}".format(signature))

            return (status, {'Content-Type': 'application/json'}, body)

        responses.add_callback(responses.POST, self.url, callback=callback,
                               content_type="application/json")

        # Should return error
        with self.assertRaises(MediaFireApiError):
            self.api.user_get_info()

        # Should be successful
        self.api.user_get_info()

        query = responses.calls[1].request.body
        params = parse_qs(query)
        self.assertEqual(params['signature'][0], CALL_SIGNATURES[1])


if __name__ == "__main__":
    unittest.main()
