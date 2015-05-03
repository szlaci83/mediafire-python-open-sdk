"""MediaFireUploader - API encapsulating Upload magic"""

from __future__ import unicode_literals

import os
import hashlib
import logging
import time

from collections import namedtuple

from mediafire.subsetio import SubsetIO

# Use resumable upload if file is larger than 4Mb
UPLOAD_SIMPLE_LIMIT = 4 * 1024 * 1024

# Retry resumable uploads 5 times
UPLOAD_RETRY_COUNT = 5

# Upload polling interval in seconds
UPLOAD_POLL_INTERVAL = 5

# Length of upload key
UPLOAD_KEY_LENGTH = 11

logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


# pylint: disable=too-few-public-methods,too-many-arguments
class _UploadInfo(object):
    """Structure containing upload details"""

    def __init__(self, fd=None, name=None, folder_key=None, path=None,
                 hash_=None, size=None, filedrop_key=None,
                 action_on_duplicate=None):
        self.fd = fd
        self.name = name
        self.folder_key = folder_key
        self.path = path
        self.hash_ = hash_
        self.size = size
        self.filedrop_key = filedrop_key
        self.action_on_duplicate = action_on_duplicate


class _UploadUnitInfo(object):
    """Structure containing upload unit details"""
    def __init__(self, upload_info=None, fd=None, uid=None, hash_=None):
        self.upload_info = upload_info
        self.fd = fd
        self.uid = uid
        self.hash_ = hash_


UploadResult = namedtuple('UploadResult', [
    'action', 'quickkey', 'hash_', 'filename', 'size', 'created', 'revision'
])


# pylint: enable=too-few-public-methods,too-many-arguments
class UploadSession(object):  # pylint: disable=too-few-public-methods
    """Allocate/deallocate action token automatically"""

    def __init__(self, api):
        """Initialize context manager

        api -- MediaFireApi instance
        """
        self.action_token = None
        self._api = api

    def __enter__(self):
        """Allocate action token"""
        self.action_token = self._api.user_get_action_token(
            type_="upload", lifespan=1440)['action_token']

        self._api.set_action_token(type_="upload",
                                   action_token=self.action_token)

    def __exit__(self, *exc_details):
        """Destroys action token"""
        self._api.user_destroy_action_token(action_token=self.action_token)


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


class MediaFireUploader(object):
    """API encapsulating Upload magic"""

    def __init__(self, api):
        """Initialize MediaFireUploader

        api -- MediaFireApi instance
        """
        self._api = api

    @staticmethod
    def sha256_digest(fd):
        """Get SHA256 digest of flehandle contents

        fd - file-like object (expects exclusive access because of seeking)
        """
        fd.seek(0, os.SEEK_SET)

        sha256sum = hashlib.sha256()
        for chunk in iter(lambda: fd.read(8192), b''):
            sha256sum.update(chunk)

        fd.seek(0, os.SEEK_SET)

        return sha256sum.hexdigest().lower()

    # pylint: disable=too-many-arguments
    def upload(self, fd, name=None, folder_key=None, filedrop_key=None,
               path=None, hash_=None, action_on_duplicate=None):
        """Upload file, returns UploadResult object

        fd -- file-like object to upload from, expects exclusive access
        name -- file name
        folder_key -- folderkey of the target folder
        path -- path to file relative to folder_key
        hash_ -- SHA256 of contents
        filedrop_key -- filedrop to use instead of folder_key
        action_on_duplicate -- skip, keep, replace
        """

        # Allow supplying stored hash
        if hash_ is None:
            logger.debug("Calculating checksum")
            hash_ = self.sha256_digest(fd)

        # Get file handle content length in the most reliable way
        fd.seek(0, os.SEEK_END)
        size = fd.tell()
        fd.seek(0, os.SEEK_SET)

        upload_info = _UploadInfo(fd=fd, name=name, folder_key=folder_key,
                                  hash_=hash_, size=size, path=path,
                                  filedrop_key=filedrop_key,
                                  action_on_duplicate=action_on_duplicate)

        if size > UPLOAD_SIMPLE_LIMIT:
            resumable = True
        else:
            resumable = False

        # Check whether file is present
        check_result = self._api.upload_check(
            filename=upload_info.name,
            size=upload_info.size,
            hash_=upload_info.hash_,
            folder_key=upload_info.folder_key,
            filedrop_key=upload_info.filedrop_key,
            path=upload_info.path,
            resumable=resumable
            )

        upload_result = None

        folder_key = check_result.get('folder_key', None)
        if folder_key is not None:
            # We know precisely what folder_key to use, drop path
            upload_info.folder_key = folder_key
            upload_info.path = None

        if check_result['hash_exists'] == 'yes':
            # file exists somewhere in MediaFire
            if check_result['in_folder'] == 'yes' and \
                    check_result['file_exists'] == 'yes':
                # file exists in this directory
                different_hash = check_result.get('different_hash', 'no')
                if different_hash == 'no':
                    # file is already there
                    upload_result = UploadResult(
                        action=None,
                        quickkey=check_result['duplicate_quickkey'],
                        hash_=upload_info.hash_,
                        filename=name,
                        size=upload_info.size,
                        created=None,
                        revision=None
                    )

            if not upload_result:
                # different hash or in other folder
                upload_result = self._upload_instant(upload_info)

        if not upload_result:
            if resumable:
                # Provide check_result to avoid calling API twice
                upload_result = self._upload_resumable(upload_info,
                                                       check_result)
            else:
                upload_result = self._upload_simple(upload_info)

        return upload_result
    # pylint: enable=too-many-arguments

    def _poll_upload(self, upload_key, action):
        """Poll upload until quickkey is found

        upload_key -- upload_key returned by upload/* functions
        """

        if len(upload_key) != UPLOAD_KEY_LENGTH:
            # not a regular 11-char-long upload key
            # There is no API to poll filedrop uploads
            return UploadResult(
                action=action,
                quickkey=None,
                hash_=None,
                filename=None,
                size=None,
                created=None,
                revision=None
            )

        quick_key = None
        while quick_key is None:
            poll_result = self._api.upload_poll(upload_key)
            logger.debug("poll(%s): %s", upload_key, poll_result)

            doupload = poll_result['doupload']
            if int(doupload['result']) != 0:
                logger.warning("result=%d", int(doupload['result']))
                break

            if doupload['fileerror'] != '':
                # TODO: we may have to handle this a bit more dramatically
                logger.warning("fileerror=%d", int(doupload['fileerror']))
                break

            if int(doupload['status']) == 99:
                quick_key = doupload['quickkey']
            else:
                logger.debug("status=%d description=%s",
                             int(doupload['status']), doupload['description'])

                time.sleep(UPLOAD_POLL_INTERVAL)

        return UploadResult(
            action=action,
            quickkey=doupload['quickkey'],
            hash_=doupload['hash'],
            filename=doupload['filename'],
            size=doupload['size'],
            created=doupload['created'],
            revision=doupload['revision']
        )

    def _upload_instant(self, upload_info):
        """Instant upload and return quickkey

        Can be used when the file is already stored somewhere in MediaFire

        upload_info -- UploadInfo object
        """

        result = self._api.upload_instant(
            upload_info.name,
            upload_info.size,
            upload_info.hash_,
            path=upload_info.path,
            folder_key=upload_info.folder_key,
            filedrop_key=upload_info.filedrop_key,
            action_on_duplicate=upload_info.action_on_duplicate
        )

        return UploadResult(
            action='upload/instant',
            quickkey=result['quickkey'],
            filename=result['filename'],
            revision=result['new_device_revision'],
            hash_=upload_info.hash_,
            size=upload_info.size,
            created=None
        )

    def _upload_simple(self, upload_info):
        """Simple upload and return quickkey

        Can be used for small files smaller than UPLOAD_SIMPLE_LIMIT

        upload_info -- UploadInfo object
        """

        upload_result = self._api.upload_simple(
            upload_info.fd,
            upload_info.name,
            folder_key=upload_info.folder_key,
            filedrop_key=upload_info.filedrop_key,
            path=upload_info.path,
            file_size=upload_info.size,
            file_hash=upload_info.hash_,
            action_on_duplicate=upload_info.action_on_duplicate)

        logger.debug("upload_result: %s", upload_result)

        upload_key = upload_result['doupload']['key']

        return self._poll_upload(upload_key, 'upload/simple')

    def _upload_resumable_unit(self, uu_info):
        """Upload a single unit and return raw upload/resumable result

        uu_info -- UploadUnitInfo instance
        """

        # Get actual unit size
        unit_size = uu_info.fd.len

        if uu_info.hash_ is None:
            # Calculate checksum of the unit
            uu_info.hash_ = self.sha256_digest(uu_info.fd)

        return self._api.upload_resumable(
            uu_info.fd,
            uu_info.upload_info.size,
            uu_info.upload_info.hash_,
            uu_info.hash_,
            uu_info.uid,
            unit_size,
            filedrop_key=uu_info.upload_info.filedrop_key,
            folder_key=uu_info.upload_info.folder_key,
            path=uu_info.upload_info.path,
            action_on_duplicate=uu_info.upload_info.action_on_duplicate)

    def _upload_resumable_all(self, upload_info, bitmap,
                              number_of_units, unit_size):
        """Prepare and upload all resumable units and return upload_key

        upload_info -- UploadInfo object
        bitmap -- bitmap node of upload/check
        number_of_units -- number of units requested
        unit_size -- size of a single upload unit in bytes
        """

        fd = upload_info.fd

        upload_key = None

        for unit_id in range(number_of_units):
            upload_status = decode_resumable_upload_bitmap(
                bitmap, number_of_units)

            if upload_status[unit_id]:
                logger.debug("Unit %d of %d already uploaded, skipping",
                             unit_id + 1, number_of_units)
                continue

            logger.debug("Uploading unit %d of %d",
                         unit_id + 1, number_of_units)

            offset = unit_id * unit_size

            with SubsetIO(fd, offset, unit_size) as unit_fd:

                unit_info = _UploadUnitInfo(upload_info=upload_info,
                                            fd=unit_fd,
                                            uid=unit_id)

                upload_result = self._upload_resumable_unit(unit_info)

                # upload_key is needed for polling
                if upload_key is None:
                    upload_key = upload_result['doupload']['key']

        return upload_key

    def _upload_resumable(self, upload_info, check_result):
        """Resumable upload and return quickkey

        upload_info -- UploadInfo object
        check_result -- dict of upload/check call result
        """

        resumable_upload = check_result['resumable_upload']

        unit_size = int(resumable_upload['unit_size'])
        number_of_units = int(resumable_upload['number_of_units'])

        logger.debug("Uploading %d units %d bytes each",
                     number_of_units, unit_size)

        upload_key = None
        retry_count = 0

        all_units_ready = resumable_upload['all_units_ready'] == 'yes'
        bitmap = resumable_upload['bitmap']

        while not all_units_ready and retry_count < UPLOAD_RETRY_COUNT:
            logger.debug("Attempt #%d", retry_count + 1)

            upload_key = self._upload_resumable_all(upload_info, bitmap,
                                                    number_of_units, unit_size)

            check_result = self._api.upload_check(
                filename=upload_info.name,
                size=upload_info.size,
                hash_=upload_info.hash_,
                folder_key=upload_info.folder_key,
                filedrop_key=upload_info.filedrop_key,
                path=upload_info.path,
                resumable='yes')

            resumable_upload = check_result['resumable_upload']
            all_units_ready = resumable_upload['all_units_ready'] == 'yes'
            bitmap = resumable_upload['bitmap']

            if not all_units_ready:
                logger.debug("Not all units uploaded")
                retry_count += 1

        logger.debug("Upload complete. polling for status")

        return self._poll_upload(upload_key, 'upload/resumable')
