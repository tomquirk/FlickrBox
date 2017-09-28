"""
Flickrbox unit tests
"""

import unittest
import os
from flickrbox import Flickrbox

TEST_DIRNAME = 'flickbox_test'


class PhotoTest(unittest.TestCase):
    """Tests photos...?"""

    @classmethod
    def setUpClass(cls):
        cls.flickrbox = Flickrbox(dirname=TEST_DIRNAME, path=".")

    @classmethod
    def tearDownClass(cls):
        os.removedirs(cls.flickrbox.path)

    def test_dir_creation(self):
        """Test that the root Flickr directory is created"""
        self.assertTrue(os.path.exists(self.flickrbox.path)
                        and os.path.isdir(self.flickrbox.path))


if __name__ == '__main__':
    unittest.main()
