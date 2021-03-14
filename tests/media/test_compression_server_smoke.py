"""Integration tests for ConversionServerClient"""

import os
import unittest
from mediafire.media.conversion_server_client import (ConversionServerClient,
                                                      ConversionServerError)

# Getting Started With MediaFire.pdf
DOCUMENT_QUICKKEY = 'm1qlyt9ywc5qdwt'
DOCUMENT_HASH = '810bbfecf8f2a087ef94d52dbf6eaa2d3153e2bb'

# Sample - Butterfly.jpg
IMAGE_QUICKKEY = '1zzovvyw7x24ws9'
IMAGE_HASH = '38cd11c3663e0714a2e879bd4b924a253336b8c0'


@unittest.skipIf('CI' not in os.environ, "Running outside CI environment")
class ConversionServerClientSmokeTest(unittest.TestCase):
    """Basic Conversion Server Smoke Test"""

    def setUp(self):
        self.conv = ConversionServerClient()

    def test_notype_error(self):
        """Test that missing type causes bad request error"""
        with self.assertRaises(Exception):
            self.conv.request(IMAGE_HASH, IMAGE_QUICKKEY, None)

    # No document tests since the API seems to be broken ATM


if __name__ == '__main__':
    unittest.main()
