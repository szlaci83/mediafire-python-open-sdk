"""Basic uploader tests"""

from __future__ import unicode_literals

import io
import json
import math
import unittest
import responses
import six

from six.moves.urllib.parse import urlparse, parse_qs

if six.PY3:
    from unittest.mock import MagicMock
elif six.PY2:
    from mock import MagicMock

from mediafire.api import (MediaFireApi, API_BASE, API_VER)
from mediafire.uploader import (MediaFireUploader, UPLOAD_SIMPLE_LIMIT_BYTES,
                                compute_resumable_upload_unit_size,
                                compute_hash_info)


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
        unit_size = 1024 * 1024
        number_of_units = 5

        def resumable_upload_node_mock():
            """resumable_upload node generator"""

            word = 0

            # bitmap table for 5 uploaded units
            word_values = {
                0: 0,
                1: 1,
                2: 3,
                3: 7,
                4: 15
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
        """Test action_on_duplicate propagation for upload/simple"""

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
        """Test action_on_duplicate propagation for upload/instant"""

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
        """Test action_on_duplicate propagation for upload/resumable"""

        content_length = UPLOAD_SIMPLE_LIMIT_BYTES + 1

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
                        # UPLOAD_SIMPLE_LIMIT_BYTES = 4MiB, min 4 units
                        # one more byte gives us 5 units
                        "number_of_units": 5,
                        "unit_size": 1024 * 1024,
                        "bitmap": {
                            "count": "1",
                            "words":
                                upload_check_callback.words
                        }
                    },
                }
            }

            upload_check_callback.words = [31]
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
                    "number_of_units": 5,
                    "unit_size": 1024 * 1024,
                    "bitmap": {
                        "count": "1",
                        "words": [
                            31
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


class ResumableUploadLocalUnitSizeTests(unittest.TestCase):
    """Tests for local calculation of resumable upload unit_sizes"""

    def test_unit_size(self):
        MEBIBYTE = 1024 * 1024
        GIBIBYTE = MEBIBYTE * 1024

        file_size_map = {
            1:
                1024 * 1024,
            4 * MEBIBYTE:
                1024 * 1024,
            8 * MEBIBYTE:
                1024 * 1024,
            129740800:
                4096 * 1024,
            16 * GIBIBYTE:
                65536 * 1024,
            65 * GIBIBYTE:
                65536 * 1024
        }

        for file_size, expected in file_size_map.items():
            actual = compute_resumable_upload_unit_size(file_size)
            self.assertEqual(
                actual,
                expected,
                "unit_size for {} - {}, expected {}".format(
                    file_size, actual, expected)
            )


class MediaFireUploadHashingTests(unittest.TestCase):
    """Tests for compute_hash_info"""

    def test_missing_unit_size(self):
        """Test that hasher works with no unit_size"""

        fd = io.BytesIO(b"hello world")
        result = compute_hash_info(fd)

        self.assertEqual(
            result.file,
            'b94d27b9934d3e08a52e52d7da7dabfa'
            'c484efe37a5380ee9088f7ace2efcde9'
        )

        self.assertListEqual(result.units, [])

    def test_unit_size_hashing(self):
        """Test that hasher returns units hashes as well"""
        MEBIBYTE = 2 ** 20
        # 4 MiB and 1 byte for leftover testing
        DATA_SIZE = 4 * MEBIBYTE + 1

        data = b'\0' * DATA_SIZE
        fd = io.BytesIO(data)

        unit_size = compute_resumable_upload_unit_size(DATA_SIZE)
        self.assertEqual(unit_size, MEBIBYTE)

        result = compute_hash_info(fd, unit_size)

        self.assertEqual(
            result.file,
            '95e441ca65cd41fa01b2a71799e79fd6'
            '0db59ed34f13af32a91e85f90378676c'
        )

        self.assertNotEqual(result.units, [])

        print(math.ceil(1.0 * DATA_SIZE/unit_size))
        self.assertEqual(
            len(result.units),
            math.ceil(1.0 * DATA_SIZE / unit_size)
        )

        MIB_ZERO_HASH = ('30e14955ebf1352266dc2ff8067e6810'
                         '4607e750abb9d3b36582b8af909fcb58')

        ZERO_BYTE_HASH = ('6e340b9cffb37a989ca544e6bb780a2c'
                          '78901d3fb33738768511a30617afa01d')

        for i in range(4):
            self.assertEqual(result.units[i], MIB_ZERO_HASH)

        self.assertEqual(result.units[4], ZERO_BYTE_HASH)


if __name__ == "__main__":
    import logging
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    unittest.main()
