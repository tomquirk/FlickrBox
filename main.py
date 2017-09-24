"""
Flickd
"""

import os
import pathlib
import time

import flickr_api as flickr
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

flickr.set_keys(api_key="30d0fda199841b928cc05ead611b3bdb",
                api_secret="89d4e570479dc866")

flickr.set_auth_handler(".auth.txt")
flickr.enable_cache()
FLICKR_DIR = str(pathlib.Path.home()) + "/Flickr"


class Flickd:
    """
    In-memory representation of Flickr library
    """

    def __init__(self):
        print("Logging in...")
        self.user = flickr.test.login()
        if not os.path.exists(FLICKR_DIR):
            os.makedirs(FLICKR_DIR)

        # The source-of-truth for photosets. Reflects remote state
        print("Fetching data from Flickr...")
        self.photosets = {
            p.title: {
                "photoset": p,
                "photos": p.getPhotos()
            }
            for p in self.user.getPhotosets()
        }

        self.sync()

    def sync(self):
        """
        Syncs down from remote Flickr library
        """
        print("Syncing Flickr library...")
        local = {
            d: [os.path.splitext(f)[0]
                for f in os.listdir(FLICKR_DIR + "/" + d)]
            for d in os.listdir(FLICKR_DIR)
            if os.path.isdir(FLICKR_DIR + "/" + d)
        }

        # update local to reflect remote
        for photoset in self.photosets.items():
            if photoset[0] not in local:
                os.makedirs(FLICKR_DIR + "/" + photoset[0])

            for photo in photoset[1]["photos"]:
                if photo.title not in local[photoset[0]]:
                    # TODO: somehow get original file extension
                    filename = self.get_photo_path(
                        "%s.%s" % (photo.title, "jpg"), photoset[0])
                    print("\tsaving: " + photo.title)
                    photo.save(filename, size_label='Original')

        print("Sync Complete!\n\nWatching ~/Flickr for changes...")

    def add_photoset(self, title, photos):
        """
        Adds a photoset and adds photos if given
        """
        if self.photosets[title]:
            return None

        flickr.Photoset.create(title=title)
        if photos is not None:
            for photo in photos:
                self.upload_photo(photo, title)

    def upload_photo(self, photo_title, photoset_title):
        """
        Uploads a given photo to a given photoset. Photo is set to private for all users
        """
        print("\tuploading photo: ", photo_title)
        photo_obj = flickr.upload(photo_file=self.get_photo_path(
            photo_title, photoset_title), is_public=0, is_friend=0, is_family=0, hidden=2)

        self.photosets[photoset_title]["photoset"].addPhoto(photo=photo_obj)
        print("\tupload complete")

    def delete_photo(self, photo_title, photoset_title):
        """
        Deletes a given photo from a given photoset
        """
        photo = next(
            p for p in self.photosets[photoset_title]["photos"] if p.title == photo_title)
        photo.delete()

    @staticmethod
    def get_photo_path(photo_title, photoset_title):
        """
        Returns the full path of a given photo within a given photoset
        """
        return "%s/%s/%s" % (FLICKR_DIR, photoset_title, photo_title)


class FlickdEventHandler(FileSystemEventHandler):
    """
    Watchdog event handler for relevant Flickd events
    """

    def __init__(self, _flickd):
        self._flickd = _flickd

    def on_created(self, event):
        # TODO: check whether dir or file was created
        params = self.parse_filepath(event.src_path)
        self._flickd.upload_photo(params["photo"], params["photoset"])

    def on_deleted(self, event):
        params = self.parse_filepath(event.src_path)
        self._flickd.delete_photo(params["photo"], params["photoset"])

    @staticmethod
    def parse_filepath(file_path):
        """
        Returns a dictionary containing the photoset title and photo title of a given filepath
        """
        parsed = file_path.split('/')
        return {
            "photoset": parsed[-2],
            "photo": parsed[-1]
        }


if __name__ == "__main__":
    FLICKD = Flickd()

    OBSERVER = Observer()
    OBSERVER.schedule(FlickdEventHandler(FLICKD), FLICKR_DIR, recursive=True)
    OBSERVER.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        OBSERVER.stop()
    OBSERVER.join()
