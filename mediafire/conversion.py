"""MediaFire Conversion API"""
# Technically, this is called "Multimedia API"
# Audio and Video transcoding URL is sent in response to file/get_links
# and only Image and Document conversion use conversion_server.php endpoint

from __future__ import unicode_literals

import requests
import logging

from six.moves.urllib.parse import urlencode

from mediafire.api import QueryParams

logger = logging.getLogger(__name__)

API_ENDPOINT = 'https://www.mediafire.com/conversion_server.php'


class MediaFireConversionApi(object):
    """Conversion API client"""

    def __init__(self):
        self.http = requests.Session()

    def request(self, hash_, quickkey, page=None, doc_type=None,
                output=None, size_id=None, metadata=None,
                request_conversion_only=None):
        """Query conversion server"""

        if len(hash_) > 4:
            hash_ = hash_[:4]

        query = QueryParams({
            'quickkey': quickkey,
            'doc_type': doc_type,
            'page': page,
            'output': output,
            'size_id': size_id,
            'metadata': metadata,
            'request_conversion_only': request_conversion_only
        })

        url = API_ENDPOINT + '?' + hash_ + '&' + urlencode(query)

        return self.http.get(url, stream=True)
