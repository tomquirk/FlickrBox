import flickr_api
flickr_api.set_keys(api_key="30d0fda199841b928cc05ead611b3bdb",
                    api_secret="89d4e570479dc866")

flickr_api.set_auth_handler(".auth.txt")

user = flickr_api.test.login()
photos = user.getPhotos()
