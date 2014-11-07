#!/usr/bin/env python3

# These examples use MEDIAFIRE_EMAIL, MEDIAFIRE_PASSWORD environment variables

import os
import pprint

from mediafire import MediaFireApi

APP_ID = '42511'

MEDIAFIRE_EMAIL = os.environ["MEDIAFIRE_EMAIL"]
MEDIAFIRE_PASSWORD = os.environ["MEDIAFIRE_PASSWORD"]

pp = pprint.PrettyPrinter(indent=2)

api = MediaFireApi()
session = api.user_get_session_token(
    app_id=APP_ID, email=MEDIAFIRE_EMAIL, password=MEDIAFIRE_PASSWORD)

api.session = session

response = api.file_zip(keys="49v457pmu1wacb1,2c16gp40ad8orca")

pp.pprint(response.headers)

written_bytes = 0

with open("/tmp/mediafire.zip", "wb") as out_fd:
    for line in response.iter_content(chunk_size=4096):
        written_bytes += out_fd.write(line)

assert written_bytes == int(response.headers['Content-Length'])
response.close()
