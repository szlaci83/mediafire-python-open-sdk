import io
import os
import unittest

from mediafire.api import (MediaFireApi, API_BASE, API_VER)


class MediaFireApiTestCase(unittest.TestCase):
    """Base class for API tests"""

    def __init__(self, *args, **kwargs):
        super(MediaFireApiTestCase, self).__init__(*args, **kwargs)

    @staticmethod
    def build_url(action):
        """Build full URL from action"""
        return API_BASE + '/api/' + API_VER + '/' + action + '.php'

    def setUp(self, session_token=None):
        """Set up test"""
        self.api = MediaFireApi()

    def load_response(self, filename):
        """Load stored response"""
        path = os.path.join(os.path.dirname(__file__), 'responses', filename)
        with io.open(path) as fd:
            return fd.read()


class MediaFireApiTestCaseWithSessionToken(MediaFireApiTestCase):
    """Base class for API tests with session_token"""

    def setUp(self, session_token=None):
        """Set up test"""
        super(MediaFireApiTestCaseWithSessionToken, self).setUp(
            session_token=session_token)

        if session_token is None:
            session_token = {
                'session_token': 'a' * 144,
                'secret_key': '1000000000',
                'time': '0.0',
                'pkey': '12344',
                'ekey': '54321',
            }

        self.api.set_session_token(session_token)
