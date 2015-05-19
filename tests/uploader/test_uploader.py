"""Basic uploader tests"""

from __future__ import unicode_literals

import six
import io
import unittest
import responses
import json

from six.moves.urllib.parse import urlparse, parse_qs

if six.PY3:
    from unittest.mock import MagicMock
elif six.PY2:
    from mock import MagicMock

from mediafire.api import (MediaFireApi, API_BASE, API_VER)
from mediafire.uploader import MediaFireUploader, UPLOAD_SIMPLE_LIMIT


class MediaFireUploaderTest(unittest.TestCase):
    """Base class for uploader tests"""

    def setUp(self):
        """Set up uploader instance"""

        # Using unauthenticated API client
        self.api = MediaFireApi()
        self.uploader = MediaFireUploader(self.api)

    @staticmethod
    def build_url(action):
        """Build full URL from action"""
        return API_BASE + '/api/' + API_VER + '/' + action + '.php'


class MediaFireBasicUploaderTests(MediaFireUploaderTest):
    """Basic uploader tests"""

    @responses.activate
    def test_existing_file_no_upload(self):
        """Test that cats offer no angles to the wind"""

        body = """{
            "response": {
                "action": "upload/check",
                "duplicate_quickkey": "123456789012345",
                "file_exists": "yes",
                "hash_exists": "yes",
                "in_folder": "yes",
                "result": "Success"
            }
        }"""

        responses.add(responses.POST, self.build_url("upload/check"),
                      body=body, status=200, content_type='application/json')

        self.uploader._upload_simple = MagicMock()
        self.uploader._upload_instant = MagicMock()
        self.uploader._upload_resumable = MagicMock()

        fd = io.BytesIO(b"This is a set of bytes")

        self.uploader.upload(fd, 'filename')

        self.assertFalse(self.uploader._upload_simple.called)
        self.assertFalse(self.uploader._upload_instant.called)
        self.assertFalse(self.uploader._upload_resumable.called)

    @responses.activate
    def test_existing_file_upload_instant(self):
        """Test that existing file upload/instant happy path"""

        body = """{
            "response": {
                "action": "upload/check",
                "duplicate_quickkey": "123456789012345",
                "hash_exists": "yes",
                "file_exists": "no",
                "in_folder": "no",
                "result": "Success"
            }
        }"""

        responses.add(responses.POST, self.build_url("upload/check"),
                      body=body, status=200, content_type='application/json')

        body = """{
            "response": {
                "action": "upload/instant",
                "new_device_revision": 4085,
                "filename": "filename",
                "quickkey": "123456789012345",
                "result": "Success"
            }
        }"""

        responses.add(responses.POST, self.build_url('upload/instant'),
                      body=body, status=200, content_type='application/json')

        self.uploader._upload_instant = MagicMock()

        fd = io.BytesIO(b"This is a set of bytes")
        self.uploader.upload(fd, 'filename')

        self.assertTrue(self.uploader._upload_instant.called)

    @responses.activate
    def test_small_file_upload_simple(self):
        """Test that small file triggers upload/simple"""

        body = """{
            "response": {
                "action": "upload/check",
                "hash_exists": "no",
                "result": "Success"
            }
        }"""

        responses.add(responses.POST, self.build_url("upload/check"),
                      body=body, status=200, content_type='application/json')

        self.uploader._upload_simple = MagicMock()

        fd = io.BytesIO(b"This is a small set of bytes")

        self.uploader.upload(fd, 'filename')

        self.assertTrue(self.uploader._upload_simple.called)

    @responses.activate
    def test_large_file_upload_resumable(self):
        """Test that large file triggers upload/resumable"""

        body = """{
            "response": {
                "action": "upload/check",
                "hash_exists": "no",
                "result": "Success"
            }
        }"""

        responses.add(responses.POST, self.build_url("upload/check"),
                      body=body, status=200, content_type='application/json')

        self.uploader._upload_resumable = MagicMock()

        fd = io.BytesIO(b"This is a big file, really big one" * 127100)

        self.uploader.upload(fd, 'filename')

        self.assertTrue(self.uploader._upload_resumable.called)

    @responses.activate
    def test_upload_simple_happy(self):
        """Test upload/simple happy path"""

        body = """{
            "response": {
                "action": "upload/check",
                "hash_exists": "no",
                "result": "Success"
            }
        }"""

        responses.add(responses.POST, self.build_url("upload/check"),
                      body=body, status=200, content_type='application/json')

        body = """{
            "response": {
                "action": "upload/simple",
                "doupload": {
                    "result": 0,
                    "key": "12345678901"
                },
                "result": "Success"
            }
        }"""

        responses.add(responses.POST, self.build_url("upload/simple"),
                      body=body, status=200, content_type='application/json')

        body = """{
            "response": {
                "action": "upload/poll_upload",
                "doupload": {
                    "result": 0,
                    "status": 99,
                    "description": "No more requests for this key",
                    "quickkey": "123456789012345",
                    "size": 1,
                    "revision": 1,
                    "fileerror": "",
                    "hash": "559aead08264d5795d3...84fe55590eef31a88a08fdffd",
                    "filename": "filename",
                    "created": "2014-11-01 01:01:01"
                },
                "result": "Success"
            }
        }"""

        responses.add(responses.POST, self.build_url("upload/poll_upload"),
                      body=body, status=200, content_type='application/json')

        fd = io.BytesIO(b"A")

        self.uploader.upload(fd, 'filename')

    @responses.activate
    def test_upload_resumable_happy(self):
        """Test upload/resumable happy path"""

        upload_size = 4 * 1024 * 1024 + 2
        unit_size = int(upload_size / 2)
        number_of_units = 2

        def resumable_upload_node_mock():
            """resumable_upload node generator"""

            word = 0

            # bitmap table for 2 uploaded units
            word_values = {
                0: 0,
                1: 1,
                2: 3
            }

            word = word_values[
                resumable_upload_node_mock.uploaded_units
            ]

            return {
                "all_units_ready": resumable_upload_node_mock.all_units_ready,
                "number_of_units": number_of_units,
                "unit_size": unit_size,
                "bitmap": {
                    "count": "1",
                    "words": [
                        word
                    ]
                }
            }

        def upload_check_callback(request):
            """upload/check response generator"""

            doc = {
                "response": {
                    "action": "upload/check",
                    "hash_exists": "no",
                    "file_exists": "no",
                    "resumable_upload": resumable_upload_node_mock(),
                    "result": "Success"
                }
            }

            return (200, {}, json.dumps(doc))

        # "static" variables for function above
        resumable_upload_node_mock.all_units_ready = 'no'
        resumable_upload_node_mock.uploaded_units = 0

        def upload_resumable_callback(request):
            """upload/resumable response generator"""

            content_length = len(request.body.read())
            upload_resumable_callback.uploaded_bytes += content_length

            if upload_resumable_callback.uploaded_bytes >= upload_size:
                resumable_upload_node_mock.all_units_ready = 'yes'
            else:
                resumable_upload_node_mock.uploaded_units += 1

            doc = {
                "response": {
                    "action": "upload/resumable",
                    "doupload": {
                        "result": "0",
                        "key": "12345678901"
                    },
                    "resumable_upload": resumable_upload_node_mock(),
                    "result": "Success"
                }
            }

            return (200, {}, json.dumps(doc))

        upload_resumable_callback.uploaded_bytes = 0

        responses.add_callback(responses.POST,
                               self.build_url("upload/check"),
                               callback=upload_check_callback,
                               content_type='application/json')

        responses.add_callback(responses.POST,
                               self.build_url("upload/resumable"),
                               callback=upload_resumable_callback,
                               content_type='application/json')

        doc = {
            "response": {
                "action": "upload/poll_upload",
                "doupload": {
                    "result": 0,
                    "status": 99,
                    "description": "No more requests for this key",
                    "quickkey": "123456789012345",
                    "size": upload_size,
                    "revision": 1,
                    "fileerror": "",
                    "hash": "213...32",
                    "filename": "filename",
                    "created": "2014-11-01 01:01:01"
                },
                "result": "Success"
            }
        }

        responses.add(responses.POST,
                      self.build_url("upload/poll_upload"),
                      body=json.dumps(doc), status=200,
                      content_type='application/json')

        fd = io.BytesIO(b"A" * upload_size)

        result = self.uploader.upload(fd, 'filename')

        self.assertEqual(result.quickkey, '123456789012345')

    @responses.activate
    def test_upload_simple_action_on_duplicate(self):
        """Test action_on_duplicate propagation"""

        doc = {
            "response": {
                "action": "upload/check",
                "hash_exists": "no",
                "result": "Success"
            }
        }

        responses.add(responses.POST, self.build_url("upload/check"),
                      body=json.dumps(doc), status=200,
                      content_type='application/json')

        doc = {
            "response": {
                "action": "upload/simple",
                "doupload": {
                    "result": 0,
                    "key": "12345678901"
                },
                "result": "Success"
            }
        }

        responses.add(responses.POST, self.build_url("upload/simple"),
                      body=json.dumps(doc), status=200,
                      content_type='application/json')

        doc = {
            "response": {
                "action": "upload/poll_upload",
                "doupload": {
                    "result": 0,
                    "status": 99,
                    "description": "No more requests for this key",
                    "quickkey": "123456789012345",
                    "size": 1,
                    "revision": 1,
                    "fileerror": "",
                    "hash": "213...32",
                    "filename": "filename.txt",
                    "created": "2014-11-01 01:01:01"
                },
                "result": "Success"
            }
        }

        responses.add(responses.POST,
                      self.build_url("upload/poll_upload"),
                      body=json.dumps(doc), status=200,
                      content_type='application/json')

        fd = io.BytesIO(b"A")
        self.uploader.upload(fd, 'filename.txt',
                             action_on_duplicate='replace')

        req_url = responses.calls[1].request.url
        params = parse_qs(urlparse(req_url).query)
        self.assertEqual(params['action_on_duplicate'][0], 'replace')

    @responses.activate
    def test_upload_instant_action_on_duplicate(self):
        """Test action_on_duplicate propagation"""

        doc = {
            "response": {
                "action": "upload/check",
                "duplicate_quickkey": "123456789012345",
                "hash_exists": "yes",
                "file_exists": "no",
                "in_folder": "no",
                "result": "Success"
            }
        }

        responses.add(responses.POST, self.build_url("upload/check"),
                      body=json.dumps(doc), status=200,
                      content_type='application/json')

        doc = {
            "response": {
                "action": "upload/instant",
                "new_device_revision": 4086,
                "quickkey": "123456789012345",
                "filename": "filename.txt",
                "result": "Success"
            }
        }

        responses.add(responses.POST,
                      self.build_url("upload/instant"),
                      body=json.dumps(doc), status=200,
                      content_type='application/json')

        fd = io.BytesIO(b"A")
        self.uploader.upload(fd, 'filename.txt',
                             action_on_duplicate='replace')

        body = responses.calls[1].request.body
        params = parse_qs(body)
        self.assertEqual(params['action_on_duplicate'][0], 'replace')

    @responses.activate
    def test_upload_resumable_action_on_duplicate(self):
        """Test action_on_duplicate propagation"""

        content_length = UPLOAD_SIMPLE_LIMIT + 1

        def upload_check_callback(request):
            doc = {
                "response": {
                    "action": "upload/check",
                    "hash_exists": "no",
                    "file_exists": "no",
                    "in_folder": "no",
                    "result": "Success",
                    "resumable_upload": {
                        "all_units_ready":
                            upload_check_callback.all_units_ready,
                        "number_of_units": 1,
                        "unit_size": content_length,
                        "bitmap": {
                            "count": "1",
                            "words":
                                upload_check_callback.words
                        }
                    },
                }
            }

            upload_check_callback.words = [1]
            upload_check_callback.all_units_ready = 'yes'

            return (200, {}, json.dumps(doc))

        upload_check_callback.words = [0]
        upload_check_callback.all_units_ready = 'no'

        responses.add_callback(
            responses.POST, self.build_url("upload/check"),
            callback=upload_check_callback, content_type='application/json')

        doc = {
            "response": {
                "action": "upload/resumable",
                "doupload": {
                    "result": "0",
                    "key": "12345678901"
                },
                "resumable_upload": {
                    "all_units_ready": "yes",
                    "number_of_units": 1,
                    "unit_size": content_length,
                    "bitmap": {
                        "count": "1",
                        "words": [
                            1
                        ]
                    }
                },
                "result": "Success"
            }
        }

        responses.add(responses.POST,
                      self.build_url("upload/resumable"),
                      body=json.dumps(doc), status=200,
                      content_type='application/json')

        doc = {
            "response": {
                "action": "upload/poll_upload",
                "doupload": {
                    "result": 0,
                    "status": 99,
                    "description": "No more requests for this key",
                    "quickkey": "123456789012345",
                    "size": 1,
                    "revision": 1,
                    "fileerror": "",
                    "hash": "213...32",
                    "filename": "filename.txt",
                    "created": "2014-11-01 01:01:01"
                },
                "result": "Success"
            }
        }

        responses.add(responses.POST,
                      self.build_url("upload/poll_upload"),
                      body=json.dumps(doc), status=200,
                      content_type='application/json')

        fd = io.BytesIO(b"A" * content_length)
        self.uploader.upload(fd, 'filename.txt',
                             action_on_duplicate='replace')

        req_url = responses.calls[1].request.url
        params = parse_qs(urlparse(req_url).query)
        self.assertEqual(params['action_on_duplicate'][0], 'replace')


class MediaFireFileDropUploadTests(MediaFireUploaderTest):
    """FileDrop upload tests"""

    @responses.activate
    def test_upload_instant_returns_quickkey(self):
        """Test that upload/instant returns quickkey"""

        body = """{
            "response": {
                "action": "upload/check",
                "duplicate_quickkey": "123456789012345",
                "hash_exists": "yes",
                "file_exists": "no",
                "in_folder": "no",
                "result": "Success"
            }
        }"""

        responses.add(responses.POST, self.build_url("upload/check"),
                      body=body, status=200, content_type='application/json')

        body = """{
            "response": {
                "action": "upload/instant",
                "new_device_revision": 4085,
                "filename": "filename",
                "quickkey": "123456789012345",
                "result": "Success"
            }
        }"""

        responses.add(responses.POST, self.build_url("upload/instant"),
                      body=body, status=200, content_type='application/json')

        fd = io.BytesIO(b'This is a test')

        filedrop_key = 'a' * 64

        result = self.uploader.upload(fd, 'filename',
                                      filedrop_key=filedrop_key)

        self.assertEqual(result.action, 'upload/instant')
        self.assertEqual(result.quickkey, '123456789012345')

    @responses.activate
    def test_upload_simple_returns_something(self):
        """Test that upload/simple with filedrop returns at least something"""
        body = """{
            "response": {
                "action": "upload/check",
                "hash_exists": "no",
                "file_exists": "no",
                "in_folder": "no",
                "result": "Success"
            }
        }"""

        responses.add(responses.POST, self.build_url("upload/check"),
                      body=body, status=200, content_type='application/json')

        body = """{
            "response": {
                "action": "upload/simple",
                "doupload": {
                    "key": "792a6c57869232ba9f52d9143aa5b43b"
                },
                "result": "Success"
            }
        }"""

        responses.add(responses.POST, self.build_url("upload/simple"),
                      body=body, status=200, content_type='application/json')

        fd = io.BytesIO(b"This is a test string")

        filedrop_key = 'a' * 64

        result = self.uploader.upload(fd, 'filename',
                                      filedrop_key=filedrop_key)

        self.assertEqual(result.action, 'upload/simple')
        self.assertIsNone(result.quickkey)


if __name__ == "__main__":
    import logging
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    unittest.main()
