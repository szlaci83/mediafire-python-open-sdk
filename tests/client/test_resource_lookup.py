"""Resource lookup tests"""

from __future__ import unicode_literals

import unittest

from mediafire.client import (MediaFireClient, ResourceNotFoundError,
                              NotAFolderError)


class DummyMediaFireApi(object):
    """Dummy MediaFireApi class

    A MediaFireApi implementation that serves canned responses.
    Interpreting the actual HTTP payload at this level is tedious.
    """

    def folder_get_content(self, folder_key, content_type=None, chunk=None):
        """folder/get_content"""

        mock_responses = {
            None: {
                "files": {
                    "folder_content": {
                        "files": [{
                            "filename": "hi.txt",
                            "quickkey": "h" * 15
                        }],
                        "more_chunks": "no"
                    }
                },
                "folders": {
                    "folder_content": {
                        "folders": [{
                            "name": "a",
                            "folderkey": "a" * 13
                        }],
                        "more_chunks": "no"
                    }
                }
            },
            "a" * 13: {
                "files": {
                    "folder_content": {
                        "files": [],
                        "more_chunks": "no"
                    }
                },
                "folders": {
                    "folder_content": {
                        "folders": [{
                            "name": "b",
                            "folderkey": "b" * 13
                        }],
                        "more_chunks": "no"
                    }
                }
            },
            "b" * 13: {
                "files": {
                    "folder_content": {
                        "files": [{
                            "filename": "hi.txt",
                            "quickkey": "i" * 15
                        }],
                        "more_chunks": "no"
                    }
                },
                "folders": {
                    "folder_content": {
                        "folders": [],
                        "more_chunks": "no"
                    }
                }
            }
        }

        return mock_responses[folder_key][content_type]

    def folder_get_info(self, folder_key=None):
        """folder/get_info"""
        mock_responses = {
            None: {
                "folder_info": {
                    "folderkey": "blah"
                }
            },
            "b" * 13: {
                "folder_info": {
                    "folderkey": "b" * 13,
                    "name": "b"
                }
            }
        }

        return mock_responses[folder_key]

    def file_get_info(self, quick_key):
        """folder/get_info"""

        mock_responses = {
            "i" * 15: {
                "file_info": {
                    "quickkey": "i" * 15,
                    "name": "hi.txt"
                }
            }
        }

        return mock_responses[quick_key]


class MediaFireResourceLookupTests(unittest.TestCase):
    """Tests for get_resource_by_*"""

    def setUp(self):
        # we can operate w/o login
        self.client = MediaFireClient(_api=DummyMediaFireApi)

    def test_get_resource_by_path_root(self):
        """Test that get_resource_by_path works on root"""
        result = self.client.get_resource_by_path('/')
        self.assertEqual(result["folderkey"], "blah")

    def test_get_folder_by_path(self):
        """Test that multilevel folder is resolved"""
        result = self.client.get_resource_by_path('/a/b')
        self.assertEqual(result["folderkey"], "b" * 13)

    def test_intermediate_file_raises_error(self):
        """Test that a file in the middle throws NotAFolderError"""
        with self.assertRaises(NotAFolderError):
            self.client.get_resource_by_path('/hi.txt/b')

    def test_get_file_by_path(self):
        """Test that multilevel file is resolved"""
        result = self.client.get_resource_by_path('/a/b/hi.txt')
        self.assertEqual(result["quickkey"], "i" * 15)
