"""Session token tests"""

from tests.api.base import MediaFireApiTestCase


class SessionTokenTests(MediaFireApiTestCase):
    """Session token tests"""

    def test_set_good_token(self):
        """Test that we can set token"""

        token = {
            "session_token": "1234",
            "time": "1234",
            "secret_key": "1234"
        }

        self.api.set_session_token(token)

    def test_set_bad_token_raises_concern(self):
        """Test that we won't save token that does not look like one"""

        token = "I am a string"

        with self.assertRaises(ValueError):
            self.api.set_session_token(token)

    def test_unset_token_works(self):
        """Test that unsetting the token does not fail"""

        self.api.set_session_token(None)
