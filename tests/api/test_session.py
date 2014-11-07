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

        self.api.session = token

        self.assertEqual(self.api.session['session_token'], "1234")

    def test_set_bad_token_raises_concern(self):
        """Test that we won't save token that does not look like one"""

        token = "I am a string"

        with self.assertRaises(ValueError):
            self.api.session = token

        self.assertIsNone(self.api.session)

    def test_unset_token_works(self):
        """Test that unsetting the token does not fail"""

        self.api.session = None
        self.assertIsNone(self.api.session)

    def test_delete_session_works(self):
        """Test that property removal works"""

        session = {
            "session_token": "1",
            "time": "2",
            "secret_key": "3"
        }

        self.api.session = session
        self.assertEqual(self.api.session['session_token'], "1")

        del self.api.session

        self.assertIsNone(self.api.session)
