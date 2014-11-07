=========================
MediaFire Python Open SDK
=========================


This is a Python implementation of `MediaFire Core API`_ client.

.. _MediaFire Core Api: http://www.mediafire.com/developers/core_api/

.. image:: https://travis-ci.org/roman-yepishev/mediafire-python-open-sdk.svg?branch=master
    :target: https://travis-ci.org/roman-yepishev/mediafire-python-open-sdk

==================
What should I use?
==================

You may want to stick to ``MediaFireApi`` and ``MediaFireUploader`` as these are
covered by tests.

If you don't mind having breaking changes introduced here and there as the
high-level API is being shaped, then use ``MediaFireClient``.

======================
mediafire.MediaFireApi
======================

API Client library provides an interface to MediaFire API. It handles
requests, responses, signatures and errors.

Usage:

.. code-block:: python

    from mediafire import MediaFireApi

    api = MediaFireApi()
    session = api.user_get_session_token(
        email='your.email@example.net',
        password='password',
        app_id='42511')

    # API client does not know about the token
    # until explicitly told about it:
    api.session = session

    response = api.user_get_info()
    print(response['user_info']['display_name'])

    # Or directly for methods that are not yet wrapped
    response = api.request("upload/add_web_upload", {
        "url": "http://www.mediafire.com/images/brand-assets/mf-logo.png",
        "filename": "mf-logo.png"})

    response = api.request("upload/get_web_uploads",
                           {"key": response['upload_key']})


API Client library supports operation w/o session_token. In this case all
operations that do require session_token will fail with Access denied error:

.. code-block:: python

    from mediafire import MediaFireApi

    api = MediaFireApi()
    response = api.system_get_info()
    print(response)  # prints system info

    response = api.user_get_info()  # fails with "Session token is missing"

Once set, session token can be unset:

.. code-block:: python

    api.session = None
    # or
    del api.session

For information on wrapped methods, see ``pydoc mediafire.api``. For
documentation on actual values expected, see `MediaFire Core API`_
documentation.

All wrapped methods follow the same naming convention, ``category_action``, so
upload/instant is ``upload_instant``.

You can construct the call yourself easily:

.. code-block:: python

    response = api.request("user/set_avatar",
                           {"quick_key": "123456789012345"})

Downloading
-----------

API client does not handle regular file downloads because these are simple HTTP requests
to URLs returned by "file/get_links". Here's how you can do that yourself:

.. code-block:: python

    response = api.file_get_links('c94lcpx3vax6xp3')
    normal_download_url = response['links'][0]['normal_download']

    response = requests.get(normal_download_url, stream=True)
    with io.open("/tmp/green.jpg", 'wb') as fd:
        for chunk in response.iter_content(chunk_size=4096):
            fd.write(chunk)

In case response is a file download, e.g. ``file/zip``, the response returned
is a `requests.Response`_ object, which you can read from:

.. code-block:: python

    ...
    response = api.request("file/zip", {"keys": "c94lcpx3vax6xp3"})
    with io.open("/tmp/green.zip", 'wb') as fd:
        for chunk in response.iter_content(chunk_size=4096):
            fd.write(chunk)
    ...

.. _requests.Response: http://docs.python-requests.org/en/latest/api/#requests.Response

See Download_ documentation for more information.

.. _Download: http://www.mediafire.com/developers/core_api/1.2/download/

===========================
mediafire.MediaFireUploader
===========================

MediaFire supports several upload methods and `MediaFireUploader` exposes a
single `upload` method to make things easier:

.. code-block:: python

    from mediafire import (MediaFireApi, MediaFireUploader)

    api = MediaFireApi()
    uploader = MediaFireUploader(api)

    # ... authenticate ...

    fd = open('/path/to/file', 'rb')

    result = uploader.upload(fd, 'Some filename.txt',
                             folder_key='1234567890123')

    pprint(api.file_get_info(result.quickkey))

``result`` is a ``mediafire.uploader.UploadResult`` instance.

FileDrop
--------

For FileDrop uploads (i.e. when filedrop_key is used) only ``upload/instant``
result has quickkey. ``upload/instant`` and ``upload/resumable`` return
``None`` for all the fields, since ``upload/poll`` `does not support`_
encrypted upload key.

.. _does not support: http://forum.mediafiredev.com/showthread.php?293-FileDrop-upload-instant-w-o-session-succeeds-and-fails-at-the-same-time&p=478&viewfull=1#post478

================================
mediafire.client.MediaFireClient
================================

High-level client library wraps API calls and presents simplified interface.

Supported operations:

* File upload
* File download (direct download link)
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

Requirements
------------

* python 2.7 or 3.4
* six
* requests
* requests\_toolbelt
* responses (for testing)

Installing
----------

.. code-block:: bash

    $ pip install mediafire

Tests
-----

Test suite is located under ``tests/``

.. code-block:: bash


    git clone https://github.com/MediaFire/mediafire-python-open-sdk.git
    cd mediafire-python-open-sdk
    # Run tests with python 3 interpreter
    PYTHONPATH=. python3 -munittest
    # Run tests with python 2 interpreter
    PYTHONPATH=. python -munittest discover

================
Reporting issues
================

Please use the `MediaFire/mediafire-python-open-sdk`_ project issue tracker
to report issues with the implementation.

.. _MediaFire/mediafire-python-open-sdk: https://github.com/MediaFire/mediafire-python-open-sdk

Note that MediaFire server API is evolving as well, so you may to check
`MediaFire Developers Forum / REST API section`_ for known API issues.

.. _MediaFire Developers Forum / REST API section: http://forum.mediafiredev.com/forumdisplay.php?8-Using-the-REST-API-with-your-application

=================
About and License
=================

Copyright (c) 2014, Roman Yepishev. All rights reserved. Website: http://www.keypressure.com

This project was forked by MediaFire with explicit permission from Roman Yepishev on 10.24.2014

This project is made under BSD license. See LICENSE file for more information.

MediaFire® is a registered trademark of the MediaFire, LLC.
