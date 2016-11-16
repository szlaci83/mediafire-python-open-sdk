#!/usr/bin/python

import io
import os
import unittest
import logging
import uuid
from mediafire import MediaFireApi, MediaFireUploader, UploadSession
from mediafire.uploader import UPLOAD_SIMPLE_LIMIT_BYTES

APP_ID = '42511'

MEDIAFIRE_EMAIL = os.environ.get('MEDIAFIRE_EMAIL')
MEDIAFIRE_PASSWORD = os.environ.get('MEDIAFIRE_PASSWORD')


class MediaFireSmokeBaseTestCase(object):
    """Smoke tests for API"""

    class BaseTest(unittest.TestCase):
        def setUp(self):
            # Reset logging to info to avoid leaking credentials
            logger = logging.getLogger('mediafire.api')
            logger.setLevel(logging.INFO)

            self.api = MediaFireApi()
            session = self.api.user_get_session_token(
                app_id=APP_ID, email=MEDIAFIRE_EMAIL,
                password=MEDIAFIRE_PASSWORD)
            self.api.session = session


@unittest.skipIf('CI' not in os.environ, "Running outside CI environment")
class MediaFireSmokeSimpleTest(MediaFireSmokeBaseTestCase.BaseTest):
    """Simple tests"""

    def test_user_get_info(self):
        result = self.api.user_get_info()
        self.assertEqual(result["user_info"]["display_name"],
                         u"Coalmine Smoketest")


@unittest.skipIf('CI' not in os.environ, "Running outside CI environment")
class MediaFireSmokeWithDirectoryTest(MediaFireSmokeBaseTestCase.BaseTest):
    """Smoke tests requiring temporary directory"""

    def setUp(self):
        super(MediaFireSmokeWithDirectoryTest, self).setUp()

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

        self.assertIsNotNone(result.quickkey)
        self.assertEqual(result.action, 'upload/simple')

    def test_upload_large(self):
        """Test large file upload"""
        # make sure we will get upload/resumable, prefix + 4MiB
        data = b'Long line is long: ' + os.urandom(UPLOAD_SIMPLE_LIMIT_BYTES)
        fd = io.BytesIO(data)

        uploader = MediaFireUploader(self.api)

        with UploadSession(self.api):
            result = uploader.upload(fd, 'bigfile.txt',
                                     folder_key=self.folder_key)

        self.assertIsNotNone(result.quickkey)
        self.assertEqual(result.action, 'upload/resumable')

if __name__ == "__main__":
    unittest.main()
