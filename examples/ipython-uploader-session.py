#!/usr/bin/python3

import os
import logging

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

from mediafire import (MediaFireApi, MediaFireUploader)

APP_ID = '42511'
MEDIAFIRE_EMAIL = os.environ['MEDIAFIRE_EMAIL']
MEDIAFIRE_PASSWORD = os.environ['MEDIAFIRE_PASSWORD']

api = MediaFireApi()
session = api.user_get_session_token(app_id=APP_ID,
                                     email=MEDIAFIRE_EMAIL,
                                     password=MEDIAFIRE_PASSWORD)

api.session = session

uploader = MediaFireUploader(api)

print("""Welcome

Use 'uploader' object to interact with Uploader
Use 'api' object to interact with API client
""")
