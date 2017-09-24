"""
Flickd
"""

import os
import pathlib
import time

import flickr_api as flickr
from watchdog.observers import Observer
import watchdog.events
import flickr_keys

flickr.set_keys(api_key=flickr_keys.API_KEY,
                api_secret=flickr_keys.API_SECRET)
flickr.set_auth_handler(".auth.txt")
flickr.enable_cache()

FLICKR_DIR = str(pathlib.Path.home()) + "/Flickr"


class Flickd:
    """
    In-memory representation of Flickr library
    """

    def __init__(self):
        print("Logging in...")
        self._user = flickr.test.login()
        if not os.path.exists(FLICKR_DIR):
            os.makedirs(FLICKR_DIR)

        # The source-of-truth for photosets. Reflects remote state
        print("Fetching data from Flickr...")
        self._photosets = {
            p.title: {
                "photoset": p,
                "photos": p.getPhotos()
            }
            for p in self._user.getPhotosets()
        }

        self.sync()

    def sync(self):
        """
        Syncs down from remote Flickr library, then back up
        """
        print("Syncing Flickr library...")
        local = {
            d: os.listdir(self.get_path(d))
            for d in os.listdir(FLICKR_DIR)
            if os.path.isdir(self.get_path(d))
        }

        # update local to reflect remote
        for photoset in self._photosets.items():
            photoset_title = photoset[0]
            if photoset_title not in local:
                os.makedirs(FLICKR_DIR + "/" + photoset_title)
                local[photoset_title] = []

            remote_photos = []
            for photo in photoset[1]["photos"]:
                remote_photos.append(photo.title)
                if photo.title + ".jpg" in local[photoset[0]]:
                    continue

                # TODO: somehow get original file extension
                filename = self.get_path(
                    photoset[0], photo.title, ".jpg")

                print("\tsaving: " + photo.title)
                photo.save(filename, size_label='Original')
                local[photoset_title].append(photo.title)

            for photo in local[photoset[0]]:
                photo_parsed = os.path.splitext(photo)
                if photo_parsed[0] in remote_photos or photo_parsed[0] == ".DS_Store":
                    continue

                self.upload_photo(
                    photo_parsed[0], photo_parsed[1], photoset[0])

        for photoset in local.items():
            if photoset[0] in self._photosets:
                continue

            for photo in photoset[1]:
                photo_parsed = os.path.splitext(photo)
                if photo_parsed[0] == ".DS_Store":
                    continue
                self.upload_photo(
                    photo_parsed[0], photo_parsed[1], photoset[0])

        print("Sync Complete!\n\nWatching ~/Flickr for changes...")

    def add_photoset(self, photoset_title, primary_photo):
        """
        Adds a photoset
        """

        photoset = {
            "photoset": flickr.Photoset.create(title=photoset_title, primary_photo=primary_photo),
            "photos": []
        }

        self._photosets[photoset_title] = photoset
        return self._photosets[photoset_title]

    def upload_photo(self, photo_title, file_extension, photoset_title):
        """
        Uploads a given photo to a given photoset. Photo is set to private for all users
        """

        if photo_title == ".DS_Store":
            return

        print("\tuploading photo: ", photo_title)

        photo_file = self.get_path(
            photoset_title, photo_title, file_extension)
        photo_obj = flickr.upload(
            photo_file=photo_file, is_public=0, is_friend=0, is_family=0, hidden=2)

        if photoset_title not in self._photosets:
            self.add_photoset(photoset_title, photo_obj)
        else:
            self._photosets[photoset_title]["photoset"].addPhoto(
                photo=photo_obj)

        self._photosets[photoset_title]["photos"].append(photo_obj)

        print("\tupload complete")

    def delete_photo(self, photo_title, photoset_title):
        """
        Deletes a given photo from a given photoset
        """
        if photo_title == ".DS_Store":
            return
        print("Deleting %s from %s" % (photo_title, photoset_title))

        photoset = self._photosets[photoset_title]
        photo = next(p for p in photoset["photos"] if p.title == photo_title)
        photo.delete()
        photoset["photos"].remove(photo)

        # if the directory is empty, it is no longer considered a valid photoset
        if not photoset["photos"]:
            del self._photosets[photoset_title]

        print("Deleted")

    def edit_photo_title(self, old_photo_title, old_photoset_title, new_photo_title, new_photoset_title):
        """
        Deletes a given photo from a given photoset
        """
        photoset = self._photosets[old_photoset_title]
        photo = next(p for p in photoset["photos"]
                     if p.title == old_photo_title)

        photoset["photos"].remove(photo)

        photo = flickr.Photo(id=photo.id, title=new_photo_title)
        photo.setMeta(title=new_photo_title)

        if old_photoset_title != new_photoset_title:
            photoset.removePhoto(photo)
            if new_photo_title not in self._photosets:
                photoset = self.add_photoset(new_photoset_title, photo)
                photoset["photoset"].addPhoto(photo)

        photoset["photos"].append(photo)

        print("Edited photo name")

    def edit_photoset_title(self, old_photoset_title, new_photoset_title):
        """
        Deletes a given photo from a given photoset
        """

        photoset = self._photosets[old_photoset_title]
        photoset.setMeta(title=new_photoset_title)

        print("Edited photoset name")

    @staticmethod
    def get_path(photoset_title, photo_title="", file_ext=""):
        """
        Returns the absolute path based on given arguments
        """
        return "%s/%s/%s%s" % (FLICKR_DIR, photoset_title, photo_title, file_ext)


class FlickdEventHandler(watchdog.events.FileSystemEventHandler):
    """
    Watchdog event handler for relevant Flickd events
    """

    def __init__(self, _flickd):
        self._flickd = _flickd

    def on_created(self, event):
        # TODO: check whether dir or file was created
        params = self.parse_filepath(event.src_path)
        # ignore any photos that aren't in a sub-directory
        if params["photoset"] == "Flickr":
            return
        self._flickd.upload_photo(
            params["photo"], params["ext"], params["photoset"])

    def on_deleted(self, event):
        # only delete files
        if not isinstance(event, watchdog.events.FileDeletedEvent) or event.src_path == ".DS_Store":
            return

        params = self.parse_filepath(event.src_path)
        self._flickd.delete_photo(params["photo"], params["photoset"])

    def on_moved(self, event):
        old_params = self.parse_filepath(event.src_path)
        new_params = self.parse_filepath(event.dest_path)

        if isinstance(event, watchdog.events.FileMovedEvent):
            self._flickd.edit_photo_title(
                old_params["photo"], old_params["photoset"], new_params["photo"], new_params["photoset"])

    @staticmethod
    def parse_filepath(file_path):
        """
        Returns a dictionary containing the photoset title and photo title of a given filepath
        """
        parsed = file_path.split('/')
        photo_parsed = os.path.splitext(parsed[-1])
        return {
            "photoset": parsed[-2],
            "photo": photo_parsed[0],
            "ext": photo_parsed[1]
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
