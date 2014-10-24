"""MediaFire Client"""

import os
import hashlib
import logging
import time
import requests
import posixpath

from urllib.parse import urlparse

from mediafire.api import MediaFireApi, MediaFireApiError
from mediafire.subsetio import SubsetIO

KB = 1024
MB = 1024 * KB

UPLOAD_SIMPLE_LIMIT = 4 * MB

UPLOAD_RETRY_COUNT = 5

# These are educated guesses
QUICK_KEY_LENGTH = 15
FOLDER_KEY_LENGTH = 13


logger = logging.getLogger(__name__)


class Upload(object):
    """Class encapsulating upload"""
    def __init__(self, fd=None, name=None, size=None, hash_=None,
                 folder_key=None, path=None):
        """Initialize Upload object"""
        self.fd = fd
        self.name = name
        self.size = size
        self.hash_ = hash_
        self.folder_key = folder_key
        self.path = path


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


class UploadSession(object):
    """Allocate/deallocate action token automatically"""

    def __init__(self, client):
        """Initialize context manager"""
        self.action_token = None
        self.client = client

    def __enter__(self):
        """Allocate action token"""
        self.action_token = self.client.api.user_get_action_token(
            type_="upload", lifespan=1440)['action_token']

        self.client.api.set_action_token(type_="upload",
                                         action_token=self.action_token)

    def __exit__(self, *exc_details):
        """Destroys action token"""
        self.client.api.user_destroy_action_token(
            action_token=self.action_token)


def str_to_bool(value):
    return True if value == 'yes' else False


def decode_resumable_upload_bitmap(bitmap_node, number_of_units):
    """Decodes bitmap_node to hash of unit_id: is_uploaded

    bitmap_node -- bitmap node of resumable_upload with
                   'count' number and 'words' containing array
    number_of_units -- number of units we are uploading to
                       define the number of bits for bitmap
    """
    bitmap = 0
    for token_id in range(int(bitmap_node['count'])):
        value = int(bitmap_node['words'][token_id])
        bitmap = bitmap | (value << (0xf * token_id))

    result = {}

    for unit_id in range(number_of_units):
        mask = 1 << unit_id
        result[unit_id] = (bitmap & mask) == mask

    return result


class MediaFireClient(object):
    """Less-user-hostile MediaFire Client"""

    def __init__(self, session_token=None):
        """Initialize MediaFireClient"""

        # pass-through to HTTP client
        self.api = MediaFireApi()

        if session_token:
            self.api.set_session_token(session_token)

    def login(self, email=None, password=None, app_id=None, api_key=None):
        """Try to obtain session token"""
        session_token = self.api.user_get_session_token(
            app_id=app_id, email=email, password=password, api_key=api_key)
        logger.debug("result: %s", session_token)

        # install session token back into api client
        self.api.set_session_token(session_token)

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
        return UploadSession(self)

    def _prepare_upload_info(self, source, dest_uri):
        """Prepare Upload object, resolve paths"""

        try:
            dest_resource = self.get_resource_by_uri(dest_uri)
        except ResourceNotFoundError:
            dest_resource = None

        is_fh = hasattr(source, 'read')

        upload = Upload()
        if dest_resource:
            if type(dest_resource) is File:
                upload.folder_key = dest_resource['parent_folderkey']
                upload.name = dest_resource['name']
            elif type(dest_resource) is Folder:
                if is_fh:
                    raise ValueError("Cannot determine target file name")
                file_name = posixpath.basename(source)
                dest_uri = posixpath.join(dest_uri, file_name)
                try:
                    result = self.get_resource_by_uri(dest_uri)
                    if type(result) is Folder:
                        raise ValueError("Target is a folder (file expected)")
                except ResourceNotFoundError:
                    # ok, neither a file nor folder, proceed
                    upload.folder_key = dest_resource['folderkey']
                    upload.name = file_name
        else:
            # get parent resource
            parent_uri = '/'.join(dest_uri.split('/')[0:-1])
            result = self.get_resource_by_uri(parent_uri)
            if type(result) is not Folder:
                raise NotAFolderError("Parent component is not a folder")

            upload.folder_key = result['folderkey']
            upload.name = posixpath.basename(dest_uri)

        return upload

    def upload_file(self, source, dest_uri):
        """Upload src_path to dest_uri

        source -- file-like object or path to local file
        dest_uri -- MediaFire Resource URI
        """

        upload_info = self._prepare_upload_info(source, dest_uri)

        is_fh = hasattr(source, 'read')

        try:
            if is_fh:
                # Re-using filehandle
                upload_info.fd = source
            else:
                # Handling fs open/close
                upload_info.fd = open(source, 'rb')

            return self._upload(upload_info)
        finally:
            # Close filehandle if we opened it
            if upload_info.fd and not is_fh:
                upload_info.fd.close()

    def _upload(self, upload_item):
        """Upload from filehandle"""
        in_fd = upload_item.fd
        in_fd.seek(0, os.SEEK_SET)

        # Allow supplying stored hash
        if not upload_item.hash_:
            logger.info("Calculating checksum...")
            checksum = hashlib.sha256()
            for chunk in iter(lambda: in_fd.read(8192), b''):
                checksum.update(chunk)

        in_fd.seek(0, os.SEEK_END)
        upload_item.size = in_fd.tell()
        in_fd.seek(0, os.SEEK_SET)

        upload_item.hash_ = checksum.hexdigest().lower()

        if upload_item.size > UPLOAD_SIMPLE_LIMIT:
            use_resumable = True
        else:
            use_resumable = False

        # Check whether file is present
        check_result = self.api.upload_check(
            upload_item.name, path=upload_item.path,
            size=upload_item.size, folder_key=upload_item.folder_key,
            hash_=upload_item.hash_, resumable=use_resumable)

        # We know precisely what folder_key to use, drop path
        folder_key = check_result.get('folder_key', None)
        if folder_key is not None:
            upload_item.folder_key = folder_key
            upload_item.path = None

        if check_result['hash_exists'] == 'yes':
            # file exists somewhere in the cloud
            if check_result['in_folder'] == 'yes' and \
                    check_result['file_exists'] == 'yes':
                # file exists in this directory
                different_hash = check_result.get('different_hash', 'no')
                if different_hash == 'no':
                    # file is already there
                    return check_result['duplicate_quickkey']

            # different hash or in other folder
            logger.info("Performing instant upload")
            return self._upload_instant(upload_item)

        if use_resumable:
            logger.info("Performing resumable upload")
            quick_key = self._upload_resumable(
                upload_item, check_result=check_result)
        else:
            logger.info("Performing simple upload")
            quick_key = self._upload_simple(upload_item)

        return quick_key

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

            os.makedirs(os.path.dirname(target), exist_ok=True)
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

    def _poll_upload(self, upload_key):
        """Poll upload until quickkey is found"""

        quick_key = None
        while quick_key is None:
            poll_result = self.api.upload_poll(upload_key)
            logger.debug("poll(%s): %s", upload_key, poll_result)

            doupload = poll_result['doupload']
            if int(doupload['result']) != 0:
                logger.warning("result=%d", int(doupload['result']))
                break

            if doupload['fileerror'] != '':
                logger.warning("fileerror=%d", int(doupload['fileerror']))
                break

            if int(doupload['status']) == 99:
                quick_key = doupload['quickkey']
            else:
                logger.debug("status=%d description=%s",
                             int(doupload['status']), doupload['description'])
                time.sleep(5)

        return self.get_resource_by_key(quick_key)

    def _upload_instant(self, upload_item):
        """Instant upload"""

        result = self.api.upload_instant(
            upload_item.name, upload_item.size, upload_item.hash_,
            path=upload_item.path, folder_key=upload_item.folder_key)

        return result

    def _upload_simple(self, upload_item):
        """Simple upload"""

        upload_result = self.api.upload_simple(
            upload_item.fd, upload_item.name,
            folder_key=upload_item.folder_key,
            path=upload_item.path,
            file_size=upload_item.size,
            file_hash=upload_item.hash_)

        logger.debug("upload_result: %s", upload_result)

        upload_key = upload_result['doupload']['key']

        return self._poll_upload(upload_key)

    def _upload_resumable_unit(self, unit_id=None, unit_fd=None,
                               upload_item=None):
        """Upload a single unit"""

        # Get actual unit size
        unit_size = unit_fd.len

        # Calculate checksum of the unit
        checksum = hashlib.sha256()
        for chunk in iter(lambda: unit_fd.read(8192), b''):
            checksum.update(chunk)
        unit_hash = checksum.hexdigest().lower()

        # Rewind unit filehandle after checksum
        unit_fd.seek(0)

        result = self.api.upload_resumable(unit_fd, upload_item.size,
                                           upload_item.hash_,
                                           unit_hash, unit_id, unit_size,
                                           folder_key=upload_item.folder_key,
                                           path=upload_item.path)

        return result

    def _upload_resumable_units(self, upload_item, bitmap=None,
                                number_of_units=None, unit_size=None):
        """Prepare and upload all resumable units"""

        in_fd = upload_item.fd

        upload_key = None

        for unit_id in range(number_of_units):
            upload_status = decode_resumable_upload_bitmap(
                bitmap, number_of_units)

            if upload_status[unit_id]:
                logger.debug("unit#%d/%d already uploaded, skipping",
                             unit_id, number_of_units)
                continue

            logger.info("Uploading part %d of %d",
                        unit_id + 1, number_of_units)

            offset = unit_id * unit_size

            time_start = time.time()

            with SubsetIO(in_fd, offset, unit_size) as chunk_fd:
                # Ignore result for now, re-check after all items are uploaded
                upload_result = self._upload_resumable_unit(
                    unit_id=unit_id, unit_fd=chunk_fd, upload_item=upload_item)

                # upload_key is needed for polling
                if upload_key is None:
                    upload_key = upload_result['doupload']['key']

            logger.info("Uploaded part %d of %d in %ds",
                        unit_id + 1, number_of_units,
                        time.time() - time_start)

        return upload_key

    def _upload_resumable(self, upload_item, check_result=None):
        """Resumable upload"""

        resumable_upload = check_result['resumable_upload']

        unit_size = int(resumable_upload['unit_size'])
        number_of_units = int(resumable_upload['number_of_units'])

        logger.debug("Uploading %d units %d bytes each",
                     number_of_units, unit_size)

        upload_key = None
        retry_count = 0

        all_units_ready = str_to_bool(resumable_upload['all_units_ready'])
        bitmap = resumable_upload['bitmap']

        while not all_units_ready and retry_count < UPLOAD_RETRY_COUNT:
            logger.info("Attempt #%d", retry_count + 1)

            upload_key = self._upload_resumable_units(
                upload_item, bitmap=bitmap, number_of_units=number_of_units,
                unit_size=unit_size)

            check_result = self.api.upload_check(
                upload_item.name, path=upload_item.path, size=upload_item.size,
                hash_=upload_item.hash_, resumable=True)

            resumable_upload = check_result['resumable_upload']
            all_units_ready = str_to_bool(resumable_upload['all_units_ready'])
            bitmap = resumable_upload['bitmap']

            if not all_units_ready:
                logger.debug("Not all units uploaded")
                retry_count += 1

        logger.debug("upload complete. polling for status")

        return self._poll_upload(upload_key)
