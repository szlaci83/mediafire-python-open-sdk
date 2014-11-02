# coding: utf-8

"""Upload tests"""

from __future__ import unicode_literals

import io
import responses
import unittest

from tests.api.base import MediaFireApiTestCaseWithSessionToken


class TestUploadSimple(MediaFireApiTestCaseWithSessionToken):
    """upload/check tests"""

    def setUp(self):
        self.action = "upload/simple"
        super(TestUploadSimple, self).setUp()

    @responses.activate
    def test_header_encoding(self):
        """upload/simple filename encoding test"""

        body = r"""
            {"response":{
            "action":"upload\/simple",
            "doupload":{"result":"0","key":"53u05frn7sm"},
            "server":"live","result":"Success","new_key":"yes",
            "current_api_version":"1.1"}}
        """

        responses.add(responses.POST, self.url, body=body, status=200,
                      content_type="application/json")

        fd = io.StringIO("I am the payload. Hi!")
        file_size = len(fd.read())
        fd.seek(0)

        self.client.upload_simple(
            fd, "тест.bin", file_size=file_size, file_hash='0')

        request = responses.calls[0].request

        x_filename = request.headers['x-filename']

        self.assertEqual(x_filename, "тест.bin".encode('utf-8'))

if __name__ == "__main__":
    unittest.main()
