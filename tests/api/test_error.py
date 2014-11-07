import unittest
import responses

from tests.api.base import MediaFireApiTestCase

from mediafire.api import MediaFireApiError


class TestErrorResponse(MediaFireApiTestCase):

    def __init__(self, *args, **kwargs):
        super(MediaFireApiTestCase, self).__init__(*args, **kwargs)
        self.url = self.build_url('system/get_status')

    @responses.activate
    def test_json_error(self):
        """Test error handling for json response"""
        body = """
        {"response": {
            "result": "Error",
            "message": "This is a fun error",
            "error": "102"}}
        """

        responses.add(responses.POST, self.url, body=body, status=900,
                      content_type="application/json")

        with self.assertRaises(MediaFireApiError):
            self.api.system_get_status()

    @responses.activate
    def test_json_in_xml_error(self):
        """Test that json-in-xml (api bug) still detects error"""
        body = """
        {"response": {
            "result": "Error",
            "message": "This is even funnier",
            "error": "103"}}
        """

        responses.add(responses.POST, self.url, body=body, status=900,
                      content_type="text/xml")

        with self.assertRaises(MediaFireApiError):
            self.api.system_get_status()

if __name__ == "__main__":
    unittest.main()
