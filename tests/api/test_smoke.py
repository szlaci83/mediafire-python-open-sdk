#!/usr/bin/python

import os
import unittest
import logging
from mediafire import MediaFireApi

APP_ID = '42511'

MEDIAFIRE_EMAIL = os.environ['MEDIAFIRE_EMAIL']
MEDIAFIRE_PASSWORD = os.environ['MEDIAFIRE_PASSWORD']

logger = logging.getLogger('mediafire.api')
logger.setLevel(logging.INFO)


@unittest.skipIf('CI' not in os.environ, "Running outside CI environment")
class MediaFireSmokeTest(unittest.TestCase):
    """Smoke test for API"""

    def __init__(self, *args, **kwargs):
        super(MediaFireSmokeTest, self).__init__(*args, **kwargs)
        self.api = MediaFireApi()
        session = self.api.user_get_session_token(
            app_id=APP_ID, email=MEDIAFIRE_EMAIL, password=MEDIAFIRE_PASSWORD)
        self.api.session = session

    def test_user_get_info(self):
        result = self.api.user_get_info()
        self.assertEqual(result['user_info']['display_name'],
                         u"Coalmine Smoketest")

if __name__ == "__main__":
    unittest.main()
