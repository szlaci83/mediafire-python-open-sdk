#!/usr/bin/python3

import os
import logging

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

from mediafire.client import MediaFireClient

APP_ID = '42511'
MEDIAFIRE_EMAIL = os.environ['MEDIAFIRE_EMAIL']
MEDIAFIRE_PASSWORD = os.environ['MEDIAFIRE_PASSWORD']

client = MediaFireClient()
client.login(app_id=APP_ID, email=MEDIAFIRE_EMAIL, password=MEDIAFIRE_PASSWORD)

print("Use 'client' object to interact with MediaFireClient")
