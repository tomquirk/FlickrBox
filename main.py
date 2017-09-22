import flickr_api
import os
import pathlib

flickr_api.set_keys(api_key="30d0fda199841b928cc05ead611b3bdb",
                    api_secret="89d4e570479dc866")

flickr_api.set_auth_handler(".auth.txt")
FLICKR_DIR = str(pathlib.Path.home()) + "/Flickr"


class Flickd:
    """
    In-memory representaion of Flickr library
    """

    def __init__(self):
        self.user = flickr_api.test.login()
        if not os.path.exists(FLICKR_DIR):
            os.makedirs(FLICKR_DIR)

        self.local = {
            d: os.listdir(FLICKR_DIR + "/" + d)
            for d in os.listdir(FLICKR_DIR)
            if os.path.isdir(FLICKR_DIR + "/" + d)
        }

        self.photosets = {
            p.title: {
                "photoset": p,
                "photos": [i.title for i in p.getPhotos()]
            }
            for p in self.user.getPhotosets()
        }

        self.sync()

    def sync(self):
        for photoset in self.photosets.items():
            if photoset[0] not in self.local:
                os.makedirs(FLICKR_DIR + "/" + photoset[0])


flickd = Flickd()
