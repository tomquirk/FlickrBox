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
                    filename = self._get_photo_path(
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

        photoset = flickr.Photoset.create(title=title)
        if photos is not None:
            for p in photos:
                self.upload_photo(p, title)

    def upload_photo(self, photo_title, photoset_title):
        """
        Uploads a given photo to a given photoset. Photo is set to private for all users
        """
        print("\tuploading photo: ", photo_title)
        photo_obj = flickr.upload(photo_file=self._get_photo_path(
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

    def _get_photo_path(self, photo_title, photoset_title):
        return "%s/%s/%s" % (FLICKR_DIR, photoset_title, photo_title)


class FlickdEventHandler(FileSystemEventHandler):
    def __init__(self, _flickd):
        self._flickd = _flickd

    def on_created(self, event):
        # TODO: check whether dir or file was created
        params = self._parse_filepath(event.src_path)
        self._flickd.upload_photo(params["photo"], params["photoset"])

    def on_deleted(self, event):
        params = self._parse_filepath(event.src_path)
        self._flickd.delete_photo(params["photo"], params["photoset"])

    def _parse_filepath(self, file_path):
        parsed = file_path.split('/')
        return {
            "photoset": parsed[-2],
            "photo": parsed[-1]
        }


if __name__ == "__main__":
    flickd = Flickd()

    observer = Observer()
    observer.schedule(FlickdEventHandler(flickd), FLICKR_DIR, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
