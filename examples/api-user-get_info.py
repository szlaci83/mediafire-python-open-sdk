# These examples use MEDIAFIRE_EMAIL, MEDIAFIRE_PASSWORD environment variables

import os
import pprint

from mediafire.api import MediaFireApi
from mediafire.cli import APP_ID

pp = pprint.PrettyPrinter(indent=2)

MEDIAFIRE_EMAIL = os.environ["MEDIAFIRE_EMAIL"]
MEDIAFIRE_PASSWORD = os.environ["MEDIAFIRE_PASSWORD"]

api = MediaFireApi()
session = api.user_get_session_token(app_id=APP_ID, email=MEDIAFIRE_EMAIL,
                                     password=MEDIAFIRE_PASSWORD)

pp.pprint(session)

api.set_session_token(session)

result = api.user_get_info()

pp.pprint(result)
