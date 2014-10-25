**************************
MediaFire: Python Open SDK
**************************


Python implementation of `MediaFire Core API`_.

.. _MediaFire Core Api: http://www.mediafire.com/developers/core_api/

This is a work in progress. Expect breaking changes in the high-level client.

==================
API Client library
==================

API Client library provides a low-level interface to MediaFire API. It handles
requests, signatures and errors. Uses python-requests for streaming uploads and does not require the whole file to be loaded in memory.

Usage:

.. code-block:: python

    from mediafire.api import MediaFireApi

    api = MediaFireApi()
    session_result = api.user_get_session_token(
        email='your.email@example.net',
        password='password',
        app_id='42511')

    api.set_session_token(session_result)

    response = api.user_get_info()
    print(response['user_info']['display_name'])

    # Or directly for methods that are not yet wrapped
    response = api.request("upload/add_web_upload", {
        "url": "http://www.mediafire.com/images/brand-assets/mf-logo.png",
        "filename": "mf-logo.png"})

    response = api.request("upload/get_web_uploads",
                        {"key": status['upload_key']})


API Client library supports operation w/o session_token. In this case all
operations that do require session_token will fail with Access denied error.

==================
High-level library
==================

High-level client library wraps API calls and presents simplified interface.

Supported operations:

* Upload (instant, simple, and resumable, can use action tokens)
* Download (direct download link)
* Listing directories
* Creating directories
* Removing files and directories
* Getting info about files and directories

MediaFire resources can be referenced by path or by quickkey/folderkey.

* **path**: ``mf:/Pictures/Sample.jpg`` or ``/Pictures/Sample.jpg``
* **folder_key**: ``mf:6302u1a9p0a9x`` (``folder_key`` is 13 chars long)
* **quick_key**: ``mf:46d3y4p8542kiyp`` (``quick_key`` is 15 chars long)

.. code-block:: python

    from mediafire.client import (MediaFireClient, File, Folder)

    client = MediaFireClient()
    client.login(email='your.email@example.net',
        password='password',
        app_id='42511')

    client.upload_file("flower.jpg", "mf:/Pictures/")
    client.download_file("mf:/Pictures/flower.jpg",
                         "flower-from-mediafire.jpg")

    for item in client.get_folder_contents_iter("mf:/Pictures"):
        if type(item) is File:
            print("File: {}".format(item['filename']))
        elif type(item) is Folder:
            print("Folder: {}".format(item['foldername']))

See ``examples/mediafire-cli.py`` for high-level client usage.

CLI Interface
-------------

Work in progress. Can be used for basic tasks, such as directory listing,
uploads, downloads, getting resource information and removing files and folders
from the command line.

.. code-block:: text


        usage: mediafire-cli [-h] [--debug] [--email EMAIL] [--password PASSWORD]
                         {ls,file-upload,file-download,folder-create,resource-delete,
                          file-update-metadata,folder-update-metadata,debug-get-resource}
                         ...

        Command-line interface to MediaFire Simple File Sharing and Storage

        optional arguments:
        -h, --help            show this help message and exit
        --debug               Enable debug output
        --email EMAIL
        --password PASSWORD

        Actions:
        {ls,file-upload,file-download,folder-create,resource-delete,file-update-metadata,
         folder-update-metadata,debug-get-resource}
        ls                  List directory contents
        file-upload         Upload files
        file-download       Download file
        folder-create       Create folder
        resource-delete     Delete resource
        file-update-metadata
                            Update file metadata
        folder-update-metadata
                            Update folder metadata
        debug-get-resource  Get resource info (debug)


Use --debug option to see API calls and internal debug information.

Requirements
------------

* python3
* requests
* requests\_toolbelt
* responses (for testing)

Installing
----------

I highly suggest installing it per-user or a virtualenv and avoid installing this library systemwide.

Clone it:

.. code-block:: bash

    $ git clone https://github.com/MediaFire/mediafire-python-open-sdk.git
    $ cd python-mediafire-sdk

For user installation, follow https://pip.pypa.io/en/latest/installing.html to get ``get-pip.py``, then:

.. code-block:: bash

    $ PATH=~/.local/bin:$PATH
    $ python3 get-pip.py --user

    $ pip3 install -r requirements.txt -I
    $ python3 setup.py build install --user
    $ mediafire-cli --help

When in virtualenv, run this:

.. code-block:: bash

    $ pip3 install -r requirements.txt
    $ python3 setup.py build install

    # make sure that cli is working
    $ examples/mediafire-cli --help

Tests
-----

Basic test suite is located under ``tests/``

Run it with:

.. code-block:: bash

    cd mediafire-python-open-sdk
    PYTHONPATH=. python3 -munittest

=================
About and License
=================

Copyright (c) 2014, Roman Yepishev. All right reserved. Website : http://rtg.in.ua

This project was forked by MediaFire with explicit permission from Roman Yepishev on 10.24.2014

This project is made under BSD license. See LICENSE file for more information.

MediaFire® is a registered trademark of the MediaFire, LLC.
