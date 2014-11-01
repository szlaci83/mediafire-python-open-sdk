"""Basic uploader tests"""

import os
import io
import unittest
import responses

from unittest.mock import MagicMock

from mediafire.api import (MediaFireApi, API_BASE, API_VER)
from mediafire.uploader import MediaFireUploader


class MediaFireUploaderTest(unittest.TestCase):
    """Basic uploader tests"""

    def setUp(self):
        """Set up uploader instance"""

        # Using unauthenticated API client
        api = MediaFireApi()
        self.uploader = MediaFireUploader(api)

    @staticmethod
    def load_response(filename):
        """Load stored response"""
        path = os.path.join(os.path.dirname(__file__), 'responses', filename)
        with io.open(path) as fd:
            return fd.read()

    @staticmethod
    def build_url(action):
        """Build full URL from action"""
        return API_BASE + '/api/' + API_VER + '/' + action + '.php'

    @responses.activate
    def test_existing_file_no_upload(self):
        """Test that cat offers no angle to the wind"""

        responses.add(responses.POST, self.build_url("upload/check"),
                      body=self.load_response('upload_check_1.json'),
                      status=200, content_type='application/json')

        responses.add(responses.POST, self.build_url("file/get_info"),
                      body=self.load_response('file_get_info_1.json'),
                      status=200, content_type='application/json')

        self.uploader._upload_simple = MagicMock()
        self.uploader._upload_instant = MagicMock()
        self.uploader._upload_resumable = MagicMock()

        fd = io.BytesIO(b"This is a set of bytes")

        result = self.uploader.upload(fd, 'filename')

        self.assertFalse(self.uploader._upload_simple.called)
        self.assertFalse(self.uploader._upload_instant.called)
        self.assertFalse(self.uploader._upload_resumable.called)

        self.assertEqual(result['file_info']['quickkey'], '123456789012345')

    @responses.activate
    def test_upload_instant(self):
        """Test that existing file upload/instant"""

        responses.add(responses.POST, self.build_url("upload/check"),
                      body=self.load_response('upload_check_2.json'),
                      status=200, content_type='application/json')

        responses.add(responses.POST, self.build_url('file/get_info'),
                      body=self.load_response('file_get_info_1.json'),
                      status=200, content_type='application/json')

        responses.add(responses.POST, self.build_url('upload/instant'),
                      body=self.load_response('upload_instant_1.json'),
                      status=200, content_type='application/json')

        self.uploader._upload_instant = MagicMock()

        fd = io.BytesIO(b"This is a set of bytes")
        result = self.uploader.upload(fd, 'filename')

        self.assertTrue(self.uploader._upload_instant.called)

        self.assertEqual(result['file_info']['quickkey'], '123456789012345')

if __name__ == "__main__":
    unittest.main()
