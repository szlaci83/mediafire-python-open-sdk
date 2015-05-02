#!/usr/bin/python

import io
import os
import unittest
import logging
import uuid
from mediafire import MediaFireApi, MediaFireUploader, UploadSession

APP_ID = '42511'

MEDIAFIRE_EMAIL = os.environ['MEDIAFIRE_EMAIL']
MEDIAFIRE_PASSWORD = os.environ['MEDIAFIRE_PASSWORD']

logger = logging.getLogger()
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


@unittest.skipIf('CI' not in os.environ, "Running outside CI environment")
class MediaFireSmokeSimpleTest(MediaFireSmokeTest):
    """Simple tests"""

    def test_user_get_info(self):
        result = self.api.user_get_info()
        self.assertEqual(result["user_info"]["display_name"],
                         u"Coalmine Smoketest")


@unittest.skipIf('CI' not in os.environ, "Running outside CI environment")
class MediaFireSmokeWithDirectoryTest(MediaFireSmokeTest):
    """Smoke tests requiring temporary directory"""

    def setUp(self):
        folder_uuid = str(uuid.uuid4())
        result = self.api.folder_create(foldername=folder_uuid)
        self.folder_key = result["folder_key"]

    def tearDown(self):
        self.api.folder_purge(self.folder_key)

    def test_upload_small(self):
        """Test simple upload"""
        # make sure we most likely will get upload/simple
        data = b'This is a tiny file content: ' + os.urandom(32)
        fd = io.BytesIO(data)

        uploader = MediaFireUploader(self.api)

        with UploadSession(self.api):
            result = uploader.upload(fd, 'smallfile.txt',
                                     folder_key=self.folder_key)

        quickkey = result.quickkey

        self.assertIsNotNone(quickkey)

    def test_upload_large(self):
        """Test large file upload"""
        # make sure we will get upload/resumable, around 5MB payload
        data = b'Long line is long: ' + os.urandom(5 * 1024 * 1024)
        fd = io.BytesIO(data)

        uploader = MediaFireUploader(self.api)

        with UploadSession(self.api):
            result = uploader.upload(fd, 'bigfile.txt',
                                     folder_key=self.folder_key)

        quickkey = result.quickkey

        self.assertIsNotNone(quickkey)

if __name__ == "__main__":
    unittest.main()
