#!/usr/bin/python3

import logging

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

from mediafire.conversion import MediaFireConversionApi

APP_ID = '42511'

conversion = MediaFireConversionApi()

print("Use 'conversion' object to interact with Image/Document Conversion API")
