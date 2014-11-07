"""MediaFire Client"""

from __future__ import unicode_literals

import os
import hashlib
import logging
import requests
import posixpath

from six.moves.urllib.parse import urlparse

from mediafire.api import (MediaFireApi, MediaFireApiError)
from mediafire.uploader import (MediaFireUploader, UploadSession)

# These are educated guesses
QUICK_KEY_LENGTH = 15
FOLDER_KEY_LENGTH = 13


logger = logging.getLogger(__name__)


class ApiBugWarning(Warning):
    """Warns when remote API bug is encountered"""
    pass


class MediaFireError(Exception):
    """Base class for MediaFire errors"""
    pass


class ResourceNotFoundError(MediaFireError):
    """Raised when resource referenced cannot be found"""
    pass


class NotAFolderError(MediaFireError):
    """Raised when operation expects a folder but got something else"""
    pass


class Resource(dict):
    """Base class for MediFire resources"""
    pass


class File(Resource):
    """MediaFire File resource"""
    pass


class Folder(Resource):
    """MediaFire Folder resource"""
    pass


class MediaFireClient(object):
    """Less-user-hostile MediaFire Client"""

    def __init__(self, session_token=None):
        """Initialize MediaFireClient"""

        # pass-through to HTTP client
        self.api = MediaFireApi()

        if session_token:
            self.api.session = session_token

    def login(self, email=None, password=None, app_id=None, api_key=None):
        """Try to obtain session token"""
        session_token = self.api.user_get_session_token(
            app_id=app_id, email=email, password=password, api_key=api_key)
        logger.debug("result: %s", session_token)

        # install session token back into api client
        self.api.session = session_token

    def get_resource_by_uri(self, uri):
        """Resolve remote path by mediafire uri

        uri -- One of:
            mf:(quickkey|folderkey[/path/to/resource]|/path/to/resource)
            /path/to/resource
        """

        tokens = urlparse(uri)
        if tokens.path.startswith("/"):
            # Use path lookup only, root=myfiles
            result = self.get_resource_by_path(tokens.path)
        elif tokens.scheme == 'mf':
            if '/' in tokens.path:
                resource_key = tokens.path.split('/')[0]
                # get root first
                parent_folder = self.get_resource_by_key(resource_key)
                if type(parent_folder) is not Folder:
                    raise NotAFolderError(resource_key)
                path = '/'.join(tokens.path.split('/')[1:])
                # perform additional lookup by path
                result = self.get_resource_by_path(
                    path, folder_key=parent_folder['folderkey'])
            else:
                result = self.get_resource_by_key(tokens.path)
        else:
            raise ValueError("MediaFire URI must start with 'mf:' or '/'")

        return result

    def get_resource_by_key(self, resource_key):
        """Get file or folder by quick_key/folder_key

        key -- quick_key or folder_key
        """

        # search for quick_key by default
        lookup_order = ["quick_key", "folder_key"]

        if len(resource_key) == FOLDER_KEY_LENGTH:
            lookup_order = ["folder_key", "quick_key"]

        resource = None

        for lookup_key in lookup_order:
            try:
                if lookup_key == "folder_key":
                    info = self.api.folder_get_info(folder_key=resource_key)
                    resource = Folder(info['folder_info'])
                elif lookup_key == "quick_key":
                    info = self.api.file_get_info(quick_key=resource_key)
                    resource = File(info['file_info'])
            except MediaFireApiError:
                # TODO: Check response code
                pass

            if resource:
                break

        if not resource:
            raise ResourceNotFoundError(resource_key)

        return resource

    def get_resource_by_path(self, path, folder_key=None):
        """Get resource by remote path

        path -- remote path
        """
        logger.debug("resolving %s", path)

        # remove empty path components
        path = posixpath.normpath(path)
        tokens = [t for t in path.split(posixpath.sep) if t != '']

        if not len(tokens):
            # request for root
            return Folder(
                self.api.folder_get_info(folder_key)['folder_info']
            )

        search_token = tokens.pop(0)

        resource = None
        node = None
        while resource is None:
            if node is not None:
                folder_key = node['folderkey']

            folders_result = self.api.folder_get_content(folder_key=folder_key)
            folders = folders_result['folder_content']['folders']
            name_map = {i['name']: i for i in folders}

            if search_token in name_map:
                if not tokens:
                    # last component resolved
                    resource = name_map[search_token]
                    break
                else:
                    # continue searching
                    node = name_map[search_token]
                    search_token = tokens.pop(0)
                    continue

            if tokens:
                # intermediate folder not found, nothing to see here
                break

            # no more tokens, we are at the last component
            files_result = self.api.folder_get_content(folder_key=folder_key,
                                                       content_type='files')
            files = files_result['folder_content']['files']
            name_map = {i['filename']: i for i in files}

            if search_token in name_map:
                resource = name_map[search_token]
                break

            if not tokens:
                break

        if resource is None:
            raise ResourceNotFoundError(path)

        if "quickkey" in resource:
            file_info = self.api.file_get_info(
                resource['quickkey'])['file_info']
            result = File(file_info)
        elif "folderkey" in resource:
            folder_info = self.api.folder_get_info(
                resource['folderkey'])['folder_info']
            result = Folder(folder_info)

        return result

    def get_folder_contents_iter(self, uri):
        """Get directory listing iterator

        uri -- mediafire URI
        """

        resource = self.get_resource_by_uri(uri)

        if type(resource) is not Folder:
            raise NotAFolderError(uri)

        folder_key = resource['folderkey']

        lookup_params = [
            {'content_type': 'folders', 'node': 'folders', 'type': Folder},
            {'content_type': 'files', 'node': 'files', 'type': File}
        ]

        for param in lookup_params:
            chunk = 0
            while True:
                chunk += 1
                content = self.api.folder_get_content(
                    content_type=param['content_type'], chunk=chunk,
                    folder_key=folder_key)['folder_content']
                if not content[param['node']]:
                    break

                for resource_info in content[param['node']]:
                    yield param['type'](resource_info)

    def create_folder(self, uri, recursive=False):
        """Create folder

        uri -- mediafire URI
        """

        uri = uri.rstrip('/')

        folder_name = posixpath.basename(uri)
        parent_uri = posixpath.dirname(uri)

        try:
            parent_node = self.get_resource_by_uri(parent_uri)
            if type(parent_node) is not Folder:
                raise NotAFolderError(parent_uri)
            parent_key = parent_node['folderkey']
        except ResourceNotFoundError:
            if recursive:
                result = self.create_folder(parent_uri, recursive=True)
                parent_key = result['folder_key']
            else:
                raise

        # We specify exact location, so don't allow duplicates
        result = self.api.folder_create(
            folder_name, parent_key=parent_key, allow_duplicate_name='no')

        logger.info("Created folder '%s' [mf:%s]",
                    result['name'], result['folder_key'])

        return self.get_resource_by_key(result['folder_key'])

    def delete_folder(self, uri, purge=False):
        """Delete folder

        uri -- MediaFire folder URI
        """

        resource = self.get_resource_by_uri(uri)

        if type(resource) is not Folder:
            raise ValueError("Folder expected, got {}".format(type(resource)))

        if purge:
            func = self.api.folder_purge
        else:
            func = self.api.folder_delete

        try:
            result = func(resource['folderkey'])
        except MediaFireApiError as err:
            if err.code == 100:
                logger.debug(
                    "Delete folder returns error 900 but folder is deleted: "
                    "http://forum.mediafiredev.com/showthread.php?129")

                result = {}
            else:
                raise

        return result

    def delete_file(self, uri, purge=False):
        """Delete file

        uri -- MediaFire file URI
        """
        resource = self.get_resource_by_uri(uri)

        if type(resource) is not File:
            raise ValueError("File expected, got {}".format(type(resource)))

        if purge:
            func = self.api.file_purge
        else:
            func = self.api.file_delete

        return func(resource['quickkey'])

    def delete_resource(self, uri, purge=False):
        """Remove file or folder

        uri -- mediafire URI
        """
        resource = self.get_resource_by_uri(uri)

        if type(resource) is File:
            result = self.delete_file(uri, purge)
        elif type(resource) is Folder:
            result = self.delete_folder(uri, purge)
        else:
            raise ValueError('Unsupported resource: {}'.format(type(resource)))

        return result

    def upload_session(self):
        """Returns upload session context manager"""
        return UploadSession(self.api)

    def _prepare_upload_info(self, source, dest_uri):
        """Prepare Upload object, resolve paths"""

        try:
            dest_resource = self.get_resource_by_uri(dest_uri)
        except ResourceNotFoundError:
            dest_resource = None

        is_fh = hasattr(source, 'read')

        folder_key = None
        name = None

        if dest_resource:
            if type(dest_resource) is File:
                folder_key = dest_resource['parent_folderkey']
                name = dest_resource['name']
            elif type(dest_resource) is Folder:
                if is_fh:
                    raise ValueError("Cannot determine target file name")
                basename = posixpath.basename(source)
                dest_uri = posixpath.join(dest_uri, basename)
                try:
                    result = self.get_resource_by_uri(dest_uri)
                    if type(result) is Folder:
                        raise ValueError("Target is a folder (file expected)")
                    folder_key = result['parent_folderkey']
                    name = result['filename']
                except ResourceNotFoundError:
                    # ok, neither a file nor folder, proceed
                    folder_key = dest_resource['folderkey']
                    name = basename
            else:
                raise Exception("Unknown resource type")
        else:
            # get parent resource
            parent_uri = '/'.join(dest_uri.split('/')[0:-1])
            result = self.get_resource_by_uri(parent_uri)
            if type(result) is not Folder:
                raise NotAFolderError("Parent component is not a folder")

            folder_key = result['folderkey']
            name = posixpath.basename(dest_uri)

        return folder_key, name

    def upload_file(self, source, dest_uri):
        """Upload src_path to dest_uri

        source -- file-like object or path to local file
        dest_uri -- MediaFire Resource URI
        """

        folder_key, name = self._prepare_upload_info(source, dest_uri)

        is_fh = hasattr(source, 'read')

        try:
            if is_fh:
                # Re-using filehandle
                fd = source
            else:
                # Handling fs open/close
                fd = open(source, 'rb')

            return MediaFireUploader(self.api).upload(fd, name,
                                                      folder_key=folder_key)
        finally:
            # Close filehandle if we opened it
            if fd and not is_fh:
                fd.close()

    def download_file(self, src_uri, target):
        """Download file

        src_uri -- mediafire file URI to download
        target -- download location
        """
        resource = self.get_resource_by_uri(src_uri)
        if type(resource) is not File:
            raise MediaFireError("Only files can be downloaded")

        quick_key = resource['quickkey']
        result = self.api.file_get_links(quick_key=quick_key,
                                         link_type='direct_download')
        direct_download = result['links'][0]['direct_download']

        logger.info(direct_download)

        name = resource['filename']

        target_is_filehandle = True if hasattr(target, 'write') else False

        if not target_is_filehandle:
            if (os.path.exists(target) and os.path.isdir(target)) or \
                    target.endswith("/"):
                target = os.path.join(target, name)

            if not os.path.isdir(os.path.dirname(target)):
                os.makedirs(os.path.dirname(target))

            logger.info("Downloading %s to %s", src_uri, target)

        response = requests.get(direct_download, stream=True)
        try:
            if target_is_filehandle:
                out_fd = target
            else:
                out_fd = open(target, 'wb')

            checksum = hashlib.sha256()
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    out_fd.write(chunk)
                    checksum.update(chunk)

            checksum_hex = checksum.hexdigest().lower()
            if checksum_hex != resource['hash']:
                raise RuntimeError("Hash mismatch ({} != {})".format(
                    resource['hash'], checksum_hex))

            logger.info("Download completed successfully")
        finally:
            if not target_is_filehandle:
                out_fd.close()

    def update_file_metadata(self, uri, filename=None, description=None,
                             mtime=None, privacy=None):
        """Update resource metadata

        uri -- MediaFire file URI
        filename -- rename file
        description -- set file description string
        mtime -- set file modification time
        privacy -- set file privacy - 'private' or 'public'
        """

        resource = self.get_resource_by_uri(uri)

        if type(resource) is not File:
            raise ValueError('Expected File, got {}'.format(type(resource)))

        result = self.api.file_update(resource['quickkey'], filename=filename,
                                      description=description,
                                      mtime=mtime, privacy=privacy)

        return result

    def update_folder_metadata(self, uri, foldername=None, description=None,
                               mtime=None, privacy=None,
                               privacy_recursive=None):
        """Update resource metadata

        uri -- MediaFire file URI
        filename -- rename file
        description -- set file description string
        mtime -- set file modification time
        privacy -- set file privacy - 'private' or 'public'
        recursive -- update folder privacy recursively
        """

        resource = self.get_resource_by_uri(uri)

        if type(resource) is not Folder:
            raise ValueError('Expected Folder, got {}'.format(type(resource)))

        result = self.api.folder_update(resource['folderkey'],
                                        foldername=foldername,
                                        description=description,
                                        mtime=mtime,
                                        privacy=privacy,
                                        privacy_recursive=privacy_recursive)

        return result
