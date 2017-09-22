import flickr_api as flickr
import os
import pathlib

flickr.set_keys(api_key="30d0fda199841b928cc05ead611b3bdb",
                api_secret="89d4e570479dc866")

flickr.set_auth_handler(".auth.txt")
FLICKR_DIR = str(pathlib.Path.home()) + "/Flickr"


class Flickd:
    """
    In-memory representaion of Flickr library
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

    def add_photoset(self, title, photos):
        """
        Adds a photoset and adds photos if given
        """
        if self.photosets[title]:
            return None

        photoset = flickr.Photoset.create(title=title)
        if photos is not None:
            for p in photos:
                self.add_photo(p, title)

    def add_photo(self, photo, photoset_title):
        """
        Adds a given photo to a given photoset
        """
        photoset.addPhoto(photo=self._get_photo_path(photo, photoset_title))

    def delete_photo(self, photo, photoset_title):
        """
        Deletes a given photo from a given photoset
        """
        photoset.removePhoto(photo=self._get_photo_path(photo, photoset_title))

    def _get_photo_path(self, photo, photoset_title):
        return "%s/%s/%s" % (FLICKR_DIR, photoset_title, photo)


if __name__ == "__main__":
    flickd = Flickd()
