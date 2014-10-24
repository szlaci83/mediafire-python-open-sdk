"""Tests for SubsetIO filehandle wrapper"""
import os
import io
import unittest
import tempfile

from requests_toolbelt import MultipartEncoder
from requests.utils import super_len

from mediafire.subsetio import SubsetIO


class SubsetIOTest(unittest.TestCase):
    """Base class for ChunkedFileWrapper tests"""
    def setUp(self):
        """Set up the test"""
        fd = tempfile.TemporaryFile()
        fd.write(b'01234567890' * 2048)
        fd.seek(0, os.SEEK_SET)

        self.fd = fd

    def tearDown(self):
        self.fd.close()


class TestSubsetIOBasics(SubsetIOTest):
    """Test ChunkedFileWrapper"""

    def test_boundaries(self):
        """Test seek boundaries"""
        with SubsetIO(self.fd, 0, 10) as fd:
            data = fd.read()
            self.assertEqual(b'0123456789', data)

            fd.seek(0, os.SEEK_SET)
            data = fd.read(1024)
            self.assertEqual(len(data), 10)

    def test_offset(self):
        """Test offset map"""
        with SubsetIO(self.fd, 1, 5) as fd:
            self.assertEqual(super_len(fd), 5)
            data = fd.read()
            self.assertEqual(b'12345', data)

    def test_len(self):
        """Test __len__"""
        with SubsetIO(self.fd, 1, 10) as chunked_fd:
            self.assertEqual(super_len(chunked_fd), 10)

    def test_seek(self):
        """Test seeks"""
        with SubsetIO(self.fd, 0, 10) as chunked_fd:
            self.assertEqual(chunked_fd.read(1), b'0')

            chunked_fd.seek(-1, os.SEEK_END)
            self.assertEqual(chunked_fd.read(1), b'9')

            with self.assertRaises(ValueError):
                chunked_fd.seek(11)


class TestSubsetIOStringIO(unittest.TestCase):
    """Test SubsetIO with StringIO"""

    def test_stringio(self):
        """Test StringIO wrapper"""
        parent_fd = io.StringIO("0123456789" * 1024)
        parent_fd.seek(0)

        with SubsetIO(parent_fd, 1, 10) as chunked_fd:
            self.assertEqual(super_len(chunked_fd), 10)

            data = chunked_fd.read()

            self.assertEqual(data, "1234567890")


class TestSubsetIOFileEncoder(SubsetIOTest):
    """Test ChunkeFileEncoder when consumed by MultipartEncoder"""

    def test_encoding(self):
        """Test MultipartEncoder encoding"""
        with SubsetIO(self.fd, 1, 64) as fd:
            encoder = MultipartEncoder(
                fields={'file': (
                    "filename", fd, 'application/octet-stream'
                )}
            )

            data = encoder.read()
            self.assertTrue(len(data) > 0)


if __name__ == "__main__":
    unittest.main()
