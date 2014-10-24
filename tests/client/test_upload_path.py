import io
import unittest

import posixpath

from mediafire.client import (MediaFireClient, ResourceNotFoundError,
                              Folder, File, NotAFolderError)


class TestUploadPath(unittest.TestCase):
    """Upload path tests"""

    def test_existing_file_overwrite(self):
        source = "/tmp/f.txt"
        dest_uri = "mf:/a/f.txt"
        folder_key = 'a' * 13
        quick_key = 'b' * 15

        def mock_get_resource_by_uri(uri):
            if uri == dest_uri:
                return File({
                    'parent_folderkey': folder_key,
                    'quickkey': quick_key,
                    'name': 'f.txt'
                })

        client = MediaFireClient()
        client.get_resource_by_uri = mock_get_resource_by_uri

        result = client._prepare_upload(source, dest_uri)
        self.assertEqual(result.name, 'f.txt')
        self.assertEqual(result.folder_key, folder_key)

    def test_upload_to_folder(self):
        source = '/tmp/j.txt'
        dest_uri = 'mf:/b/'

        folder_key = 'c' * 13

        def mock_get_resource_by_uri(uri):
            if uri == dest_uri:
                return Folder({
                    'folderkey': folder_key,
                    'name': 'a'
                })
            elif uri == 'mf:/b/j.txt':
                raise ResourceNotFoundError()

        client = MediaFireClient()
        client.get_resource_by_uri = mock_get_resource_by_uri

        result = client._prepare_upload(source, dest_uri)
        self.assertEqual(result.name, 'j.txt')
        self.assertEqual(result.folder_key, folder_key)

    def test_upload_to_folder_target_name_is_folder(self):
        source = '/tmp/j.txt'
        dest_uri = 'mf:/b/'

        folder_key = 'd' * 13

        def mock_get_resource_by_uri(uri):
            if uri == dest_uri:
                return Folder({
                    'folderkey': folder_key,
                    'name': 'b'
                })
            elif uri == 'mf:/b/j.txt':
                return Folder({
                    'folderkey': 'e' * 13,
                    'name': 'j.txt'
                })

        client = MediaFireClient()
        client.get_resource_by_uri = mock_get_resource_by_uri

        with self.assertRaises(ValueError):
            result = client._prepare_upload(source, dest_uri)

    def test_upload_target_parent_folder_does_not_exist(self):
        source = '/tmp/k.txt'
        dest_uri = 'mf:/c/k.txt'

        def mock_get_resource_by_uri(uri):
            if uri == dest_uri:
                raise ResourceNotFoundError(uri)
            elif uri == 'mf:/c':
                raise ResourceNotFoundError(uri)

        client = MediaFireClient()
        client.get_resource_by_uri = mock_get_resource_by_uri

        with self.assertRaises(ResourceNotFoundError):
            result = client._prepare_upload(source, dest_uri)

    def test_upload_target_file_doest_not_exist(self):
        source = '/tmp/l.txt'
        dest_uri = 'mf:/d/l.txt'

        folder_key = 'e' * 13

        def mock_get_resource_by_uri(uri):
            if uri == dest_uri:
                raise ResourceNotFoundError(uri)
            elif uri == 'mf:/d':
                return Folder({
                    'folderkey': folder_key,
                    'name': 'd'
                })

        client = MediaFireClient()
        client.get_resource_by_uri = mock_get_resource_by_uri

        result = client._prepare_upload(source, dest_uri)

        self.assertEqual(result.name, 'l.txt')
        self.assertEqual(result.folder_key, folder_key)

    def test_upload_target_file_parent_folder_is_file(self):
        source = '/tmp/m.txt'
        dest_uri = 'mf:/e/m.txt'

        def mock_get_resource_by_uri(uri):
            if uri == dest_uri:
                raise ResourceNotFoundError(uri)
            elif uri == 'mf:/e':
                return File({
                    'quickkey': 'f' * 15,
                    'name': 'e'
                })

        client = MediaFireClient()
        client.get_resource_by_uri = mock_get_resource_by_uri

        with self.assertRaises(NotAFolderError):
            result = client._prepare_upload(source, dest_uri)

    def test_upload_fh_existing_overwrite(self):
        source = io.StringIO("blah")
        dest_uri = 'mf:/f/m.txt'
        quick_key = 'j' * 15
        folder_key = 'h' * 13

        def mock_get_resource_by_uri(uri):
            if uri == dest_uri:
                return File({
                    'quickkey': quick_key,
                    'name': 'm.txt',
                    'parent_folderkey': folder_key
                })

        client = MediaFireClient()
        client.get_resource_by_uri = mock_get_resource_by_uri

        result = client._prepare_upload(source, dest_uri)

        self.assertEqual(result.folder_key, folder_key)
        self.assertEqual(result.name, 'm.txt')

    def test_upload_fh_to_folder(self):
        source = io.StringIO("blah")
        dest_uri = 'mf:/g/'

        def mock_get_resource_by_uri(uri):
            if uri == dest_uri:
                return Folder({
                    'folderkey': 'i' * 13,
                    'name': 'g'
                })

        client = MediaFireClient()
        client.get_resource_by_uri = mock_get_resource_by_uri

        with self.assertRaises(ValueError):
            client._prepare_upload(source, dest_uri)

    def test_upload_target_parent_folder_does_not_exist(self):
        source = io.StringIO("blah")
        dest_uri = 'mf:/h/k.txt'

        def mock_get_resource_by_uri(uri):
            if uri == dest_uri:
                raise ResourceNotFoundError(uri)
            elif uri == 'mf:/h':
                raise ResourceNotFoundError(uri)

        client = MediaFireClient()
        client.get_resource_by_uri = mock_get_resource_by_uri

        with self.assertRaises(ResourceNotFoundError):
            result = client._prepare_upload(source, dest_uri)


if __name__ == '__main__':
    unittest.main()
