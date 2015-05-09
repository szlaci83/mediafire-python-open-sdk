#!/usr/bin/python3

import logging

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

from mediafire.media import ConversionServerClient

APP_ID = '42511'

conversion = ConversionServerClient()

print("Use 'conversion' object to interact with Image/Document Conversion API")
