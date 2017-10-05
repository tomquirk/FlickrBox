"""
FlickrBox
"""

import os
from pathlib import Path
import time
import logging
import _thread

import flickr_api as flickr
from watchdog.observers import Observer
import watchdog.events

flickr.set_auth_handler(".auth")
flickr.enable_cache()

logging.basicConfig(format='- %(message)s', level=logging.DEBUG)


class Flickrbox:
    """
    In-memory representation of Flickr library
    """
    valid_extensions = [".jpg", ".png"]

    def __init__(self, dirname="FlickrBox", path=Path.home(), sync=False):
        self.dirname = dirname
        self.path = "%s/%s" % (path, dirname)

        self._upload_tickets = {}
        self._user = None
        self._photosets = None
        self._syncing = True

        self.sync(sync)

    def sync(self, sync):
        """
        Syncs down from remote Flickr library, then back up
        """
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        logging.info("Logging in...")
        self._user = flickr.test.login()

        if not sync:
            return

        # The source-of-truth for photosets. Reflects remote state
        logging.info("Fetching data from Flickr...")
        self._photosets = {
            p.title: {
                "photoset": p,
                "photos": p.getPhotos()
            }
            for p in self._user.getPhotosets()
        }

        logging.info("Syncing Flickr library...")
        local = {
            d: os.listdir(self.get_path(d))
            for d in os.listdir(self.path)
            if os.path.isdir(self.get_path(d))
        }

        _thread.start_new_thread(self.poll_upload_tickets, ())

        # update local to reflect remote
        for photoset in self._photosets.items():
            photoset_title = photoset[0]
            if photoset_title not in local:
                os.makedirs(self.get_path(photoset_title))
                local[photoset_title] = []

            remote_photos = []
            for photo in photoset[1]["photos"]:
                remote_photos.append(photo.title)
                if photo.title + ".jpg" in local[photoset[0]]:
                    continue

                # TODO: somehow get original file extension
                filename = self.get_path(
                    photoset[0], photo.title, ".jpg")

                logging.info("\tsaving: " + photo.title)
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

        self._syncing = False

        logging.info(
            "Sync Complete!\n\nWatching %s for changes..." % self.path)

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

    def poll_upload_tickets(self):
        """
        Checks the upload status of all uploading tickets.
        Once complete, adds the photo to it's repsective photoset
        """
        while self._syncing:
            tickets = flickr.Photo.checkUploadTickets(
                self._upload_tickets.keys())

            for ticket in tickets:
                if ticket["complete"] == 1:
                    photo = flickr.Photo(id=ticket["photoid"])

                    self.add_to_photoset(
                        photo, self._upload_tickets[ticket["id"]])

                    del self._upload_tickets[ticket["id"]]

            time.sleep(1)

    def add_to_photoset(self, photo_obj, photoset_title):
        """
        Adds a given photo to a given photoset
        """
        try:
            if photoset_title not in self._photosets:
                self.add_photoset(photoset_title, photo_obj)
            else:
                self._photosets[photoset_title]["photoset"].addPhoto(
                    photo=photo_obj)

            self._photosets[photoset_title]["photos"].append(photo_obj)

        except Exception as e:
            print("error adding to photoset")

    def upload_photo(self, photo_title, file_extension, photoset_title):
        """
        Uploads a given photo to a given photoset. Photo is set to private for all users
        """

        if photo_title == ".DS_Store" or file_extension.lower() not in self.valid_extensions:
            return

        photo_file = self.get_path(
            photoset_title, photo_title, file_extension)
        upload_ticket = flickr.upload(
            photo_file=photo_file,
            is_public="0", is_friend="0", is_family="0", hidden="2", async="1")

        self._upload_tickets[upload_ticket["id"]] = photoset_title

        logging.info("\tuploading photo: %s" % photo_title)

    def delete_photo(self, photo_title, photoset_title):
        """
        Deletes a given photo from a given photoset
        """
        if photo_title == ".DS_Store":
            return

        logging.info("Deleting %s from %s" % (photo_title, photoset_title))

        photoset = self._photosets[photoset_title]
        photo = next(p for p in photoset["photos"] if p.title == photo_title)
        photo.delete()
        photoset["photos"].remove(photo)

        # if the directory is empty, it is no longer considered a valid photoset
        if not photoset["photos"]:
            del self._photosets[photoset_title]

        logging.info("Deleted")

    def edit_photo_title(self, old_photo_title, old_photoset_title, new_photo_title,
                         new_photoset_title):
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

        logging.info("Edited photo name")

    def edit_photoset_title(self, old_photoset_title, new_photoset_title):
        """
        Deletes a given photo from a given photoset
        """

        photoset = self._photosets[old_photoset_title]
        photoset.setMeta(title=new_photoset_title)

        logging.info("Edited photoset name")

    def get_path(self, photoset_title, photo_title="", file_ext=""):
        """
        Returns the absolute path based on given arguments
        """
        return "%s/%s/%s%s" % (self.path, photoset_title, photo_title, file_ext)


class FlickrboxEventHandler(watchdog.events.FileSystemEventHandler):
    """
    Watchdog event handler for relevant Flickrbox events
    """

    def __init__(self, _flickrbox):
        self._flickrbox = _flickrbox

    def on_created(self, event):
        if not isinstance(event, watchdog.events.FileCreatedEvent):
            return

        params = self.parse_filepath(event.src_path)
        # ignore any photos that aren't in a sub-directory
        if params["photoset"] == FLICKRBOX:
            return
        self._flickrbox.upload_photo(
            params["photo"], params["ext"], params["photoset"])

    def on_deleted(self, event):
        # only delete files
        if not isinstance(event, watchdog.events.FileDeletedEvent) or event.src_path == ".DS_Store":
            return

        params = self.parse_filepath(event.src_path)
        self._flickrbox.delete_photo(params["photo"], params["photoset"])

    def on_moved(self, event):
        old_params = self.parse_filepath(event.src_path)
        new_params = self.parse_filepath(event.dest_path)

        if isinstance(event, watchdog.events.FileMovedEvent):
            self._flickrbox.edit_photo_title(
                old_params["photo"], old_params["photoset"],
                new_params["photo"], new_params["photoset"])

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
    FLICKRBOX = Flickrbox(sync=True)

    OBSERVER = Observer()
    OBSERVER.schedule(FlickrboxEventHandler(FLICKRBOX),
                      FLICKRBOX.path, recursive=True)
    OBSERVER.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        OBSERVER.stop()
    OBSERVER.join()
