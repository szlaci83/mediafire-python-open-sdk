"""Conversion Server API"""
# Audio and Video transcoding URL is sent in response to file/get_links
# and only Image and Document conversion use conversion_server.php endpoint

from __future__ import unicode_literals

import requests
import logging

from six.moves.urllib.parse import urlencode

from mediafire.api import QueryParams

logger = logging.getLogger(__name__)

API_ENDPOINT = 'https://www.mediafire.com/conversion_server.php'


class ConversionServerClient(object):
    """Conversion Server client"""

    def __init__(self):
        self.http = requests.Session()

    def request(self, hash_, quickkey, page=None, doc_type=None,
                output=None, size_id=None, metadata=None,
                request_conversion_only=None):
        """Query conversion server

        hash_: 4 characters of file hash
        quickkey: file quickkey
        page: The page to convert. If page is set to 'initial', the first
              10 pages of the document will be provided. (document)
        doc_type: "i" for image, "d" for documents
        output: "pdf", "img", or "swf" (document)
        size_id: 0,1,2 (document)
                 0-9, a-f, z (image)
        metadata: '1' for JSON encoded data about the document and
                  conversion stats
        request_conversion_only: Request conversion but don't wait for result
        """

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
