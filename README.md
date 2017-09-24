# Flickd

The Supreme Flickr Backup Tool.

## Why?

Dropbox, Google Drive, OneDrive. All awesome backup tools, but expensive if you need to back up your photos.
Flickr provides 1TB of storage FOR FREE - perfect! But, there is no tool for Flickr backups as good as the aforementioned.

> I want to add, rename and remove photos within a single folder and sync it with my Flickr library, just like Dropbox

**Flickd** is the solution! **Flickd** uses a single directory, `~/Flickd`, and syncs with your Flickr library. Any time you add, remove or update a photo, you change will be instantly reflected on your Flickr account!

## Getting Started

1. Install

2. Get your API keys and get authorized by following [this guide](https://github.com/alexis-mignon/python-flickr-api/wiki/Flickr-API-Keys-and-Authentication) and add them to `flickr_keys.py` like:

```python
API_KEY = "aypeeeyekey"
API_SECRET = "seakret"
```

(From the guide) save auth details to `.auth.txt`

3. Install the things.

```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

4. Fire it up

```
python3 main.py
```

### Usage

*Albums* are represented by *directories*. No photo can exist in the top level - everything must be in a folder!

...Thats it!

## Notes

This project is in its infancy. Please please create Issues for bugs, and contribute!
