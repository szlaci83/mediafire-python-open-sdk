#!/usr/bin/python

"""An example of providing hash information to the uploader

You will want to use this method if the file you are uploading
is large enough for the hashing to take considerable time.

Since uploads sometimes fail, recomputing the hash on 16GiB file
every time is not fun at all.

Usage:

    export MEDIAFIRE_EMAIL=email@example.com
    export MEDIAFIRE_PASSWORD=mediafire-password
    # get hash information
    hashing-upload.py /path/to/file > /path/to/hash_info

    # upload with stored hash
    hashing-upload.py /path/to/file /path/to/hash_info


MediaFireHashInfo fields:

 * file - sha256 hexdigest of the whole file
 * units[] - array of sha256 hexdigest of the separate file units
 * size - size of the file at the time when hash was computed.
          in case of mismatch, the file has definitely changed
          and the hash_info structure is no longer valid

"""


import json
import logging
import os
import sys

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

from mediafire import (MediaFireApi, MediaFireUploader)

from mediafire.uploader import (compute_hash_info,
                                compute_resumable_upload_unit_size,
                                UPLOAD_SIMPLE_LIMIT_BYTES,
                                MediaFireHashInfo)

APP_ID = '42511'
MEDIAFIRE_EMAIL = os.environ['MEDIAFIRE_EMAIL']
MEDIAFIRE_PASSWORD = os.environ['MEDIAFIRE_PASSWORD']


def hash_info_to_json(hash_info):
    """Convert HashInfo to JSON string"""
    return json.dumps(hash_info._asdict())


def json_to_hash_info(json_doc):
    """Convert JSON string to HashInfo"""
    hash_info_doc = json.loads(json_doc)

    return MediaFireHashInfo(**hash_info_doc)


def compute_hash_and_return_json(path):
    """Convert HashInfo to JSON string"""
    stat_result = os.stat(path)
    size = stat_result.st_size

    if size > UPLOAD_SIMPLE_LIMIT_BYTES:
        unit_size = compute_resumable_upload_unit_size(size)
    else:
        unit_size = None

    with open(path, 'rb') as fd:
        # save the hash_info somewhere on a persistent media
        hash_info = compute_hash_info(fd, unit_size)

    return hash_info_to_json(hash_info)


def upload_with_hash_info_json(path, hash_info_json_file):
    """Upload file using stored hash information"""

    with open(hash_info_json_file, 'rb') as fh:
        hash_info_json = fh.read()
        hash_info = json_to_hash_info(hash_info_json)

    api = MediaFireApi()

    session = api.user_get_session_token(
        app_id=APP_ID, email=MEDIAFIRE_EMAIL,
        password=MEDIAFIRE_PASSWORD
    )

    api.session = session

    uploader = MediaFireUploader(api)

    logging.getLogger().setLevel(logging.DEBUG)

    with open(path, 'rb') as fd:
        result = uploader.upload(
            fd, os.path.basename(path), hash_info=hash_info)

    return result


def main(path, hash_info_file):
    if hash_info_file is None:
        print(compute_hash_and_return_json(path))
    else:
        print(upload_with_hash_info_json(path, hash_info_file))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    path = sys.argv[1]

    if len(sys.argv) > 2:
        hash_info = sys.argv[2]
    else:
        hash_info = None

    main(path, hash_info)
