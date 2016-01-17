"""Tests for user/ APIs"""

from __future__ import unicode_literals

import responses
import unittest

from six.moves.urllib.parse import parse_qs

from tests.api.base import (MediaFireApiTestCase,
                            MediaFireApiTestCaseWithSessionToken)


class TestUserGetSessionToken(MediaFireApiTestCase):
    """Tests for user/get_session_token"""

    def setUp(self):
        super(TestUserGetSessionToken, self).setUp()
        self.url = self.build_url('user/get_session_token')

    def test_no_app_id_failure(self):
        with self.assertRaises(ValueError):
            self.api.user_get_session_token(email='1', password='2')

    @responses.activate
    def test_signature(self):
        body = self.load_response('test_email_password.json')

        responses.add(responses.POST, self.url, body=body, status=200,
                      content_type="application/json")
        self.api.user_get_session_token(
            email='nobody@example.com', password='secret', app_id='0')

        query = responses.calls[0].request.body.decode('utf-8')
        params = parse_qs(query)

        self.assertEqual(params['signature'][0],
                         'b13f41f5728af85e99b119c1621bb3712e13c7ce')

    def test_missing_params(self):
        with self.assertRaises(ValueError):
            self.api.user_get_session_token()

        with self.assertRaises(ValueError):
            self.api.user_get_session_token(app_id='0')

    @responses.activate
    def test_signature_with_api_key(self):
        body = self.load_response('test_email_password.json')

        api_key = 'b' * 40
        responses.add(responses.POST, self.url, body=body, status=200,
                      content_type="application/json")
        self.api.user_get_session_token(
            email='nobody@example.com', password='secret', app_id='0',
            api_key=api_key)

        query = responses.calls[0].request.body.decode('utf-8')
        params = parse_qs(query)

        self.assertEqual(params['signature'][0],
                         '9f89c6a8e603d2b9342cf8b9f8157f59bb8a3ec9')

    @responses.activate
    def test_email_password(self):
        body = self.load_response('test_email_password.json')
        responses.add(responses.POST, self.url, body=body, status=200,
                      content_type="application/json")

        session_token = self.api.user_get_session_token(
            email='nobody@example.com', password='secret', app_id='0')

        self.assertTrue('session_token' in session_token)


class TestUserRenewSessionToken(MediaFireApiTestCaseWithSessionToken):
    """Test for user/renew_session_token"""

    def setUp(self):
        super(TestUserRenewSessionToken, self).setUp()
        self.url = self.build_url('user/renew_session_token')

    @responses.activate
    def test_response(self):
        body = self.load_response(
            'test_user_renew_session_token_response.json')
        responses.add(responses.POST, self.url, body=body, status=200,
                      content_type="application/json")

        response = self.api.user_renew_session_token()

        self.assertEqual(response['session_token'], '123456')


class TestUserGetInfo(MediaFireApiTestCaseWithSessionToken):
    """Tests for user/get_info"""

    def setUp(self):
        super(TestUserGetInfo, self).setUp()
        self.url = self.build_url('user/get_info')

    @responses.activate
    def test_response(self):
        body = self.load_response('test_user_info_response.json')

        responses.add(responses.POST, self.url, body=body, status=200,
                      content_type="application/json")

        response = self.api.user_get_info()

        self.assertTrue('user_info' in response)
        self.assertEqual(response['user_info']['first_name'], 'John')


if __name__ == "__main__":
    unittest.main()
