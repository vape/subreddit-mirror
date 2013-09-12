#!/usr/bin/env python

from urllib2 import urlopen, HTTPError, URLError
import pyimgur
import re
import os
from boto.s3.connection import S3Connection
from pyimgur import Imgur, Gallery_album
from boto.s3.key import Key
import yaml
import time

import shutil

from bs4 import BeautifulSoup


def get_album_images(url):
    album_id = os.path.splitext(os.path.basename(url))[0]
    im = Imgur(os.environ['IMGURCLIENTID'])
    album = im.get_album(album_id)
    album_images = [image.link for image in album.images]

    return album_images


def initialize_config():
    if [k for k in ['S3KEY', 'S3SECRET', 'IMGURCLIENTID', 'IMGURSECRET'] if k in os.environ.keys()]:
        print('all keys exist')
        return

    if not os.path.exists('env.yaml'):
        raise Exception('env.yaml required for s3 parameter initialization')

    with open('env.yaml', 'r') as config_file:
        config = yaml.load(config_file)
        os.environ['S3KEY'] = config['s3config']['key']
        os.environ['S3SECRET'] = config['s3config']['secret']
        os.environ['IMGURCLIENTID'] = config['imgurconfig']['clientid']
        os.environ['IMGURSECRET'] = config['imgurconfig']['secret']


def upload_file(bucket, url):
    print "uploading main image ", os.path.basename(url)
    main_img_key = Key(bucket)
    main_img_key.key = os.path.basename(url)
    main_img_key.set_contents_from_filename(os.path.join(files_dir, os.path.basename(url)), reduced_redundancy=True)
    main_img_key.make_public()

    thumb_img_key = Key(bucket)
    thumb_img_key.key = os.path.basename(re.sub(image_extension_regex, r't.\1', url))
    thumb_img_key.set_contents_from_filename(os.path.join(files_dir, os.path.basename(re.sub(image_extension_regex, r't.\1', url))), reduced_redundancy=True)
    thumb_img_key.make_public()


def download_file(url):
    try:
        print('downloading ' + url)
        thumb_url = re.sub(image_extension_regex, r't.\1', url)

        image_source = urlopen(url)
        thumb_source = urlopen(thumb_url)

        dest_image = os.path.join(files_dir, os.path.basename(url))
        with open(dest_image, 'wb') as image_file:
            image_file.write(image_source.read())

        dest_thumb = os.path.join(files_dir, os.path.basename(thumb_url))
        with open(dest_thumb, 'wb') as thumb_file:
            thumb_file.write(thumb_source.read())

        print('finished ' + os.path.basename(url))

    except HTTPError, e:
        print "HTTP Error:", e.code, url
    except URLError, e:
        print "URL Error:", e.reason, url
    except:
        print 'awesome error ', url

initialize_config()
print os.environ['S3KEY']
print os.environ['S3SECRET']

files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")
if not os.path.exists(files_dir):
    os.mkdir(files_dir)

#imgur_single_image_regex = re.compile("^https?:\/\/(?:i\.|m\.|edge\.|www\.)*imgur\.com\/(?!gallery)(?!removalrequest)(?!random)(?!memegen)([A-Za-z0-9]{5}|[A-Za-z0-9]{7})[sbtmlh]?(\.(?:jpe?g|gif|png))?$", re.IGNORECASE)
imgur_image_regex = re.compile("^(https?:\/\/(?:i\.|m\.|edge\.|www\.)*imgur\.com\/(?!gallery)(?!removalrequest)(?!random)(?!memegen)(a/)?([A-Za-z0-9]{5}|[A-Za-z0-9]{7})[sbtmlh]?(\.(?:jpe?g|gif|png))?)(\?.*)?$", re.IGNORECASE)
image_extension_regex = re.compile("\.(jpe?g|gif|png)$", re.IGNORECASE)
gallery_url_regex = re.compile("/a/", re.IGNORECASE)

html = None
if not os.path.exists('aww.txt') or os.stat('aww.txt').st_size == 0:
    print 'aww.txt does not exist or is empty. going to reddit'
    page = urlopen('http://www.reddit.com/r/aww?limit=100', timeout=20)
    html = page.read()
    with open('aww.txt', 'w') as file:
        try:
            file.write(html)
        except UnicodeDecodeError, e:
            print "UnicodeDecodeError: ", e.reason
else:
    print "opening cached file"
    html = open('aww.txt', 'r').read()

soup = BeautifulSoup(html)
entries = soup.select("div.entry a.title")
links = []
for entry in entries:
    mtc = imgur_image_regex.match(entry['href'])
    if not mtc:
        continue
    links.append(mtc.group(1))

images = []

print("collecting gallery images")
gallery_collect_start = time.time()
for i, link in enumerate(links):
    if gallery_url_regex.search(link):
        [images.append(img) for img in get_album_images(link)]
    elif not image_extension_regex.search(link):
        images.append(link + '.jpg')
    else:
        images.append(link)
gallery_collect_end = time.time()

print(links)
print(images)

print "got {0} links and {1} images in {2} seconds".format(len(links), len(images), gallery_collect_end - gallery_collect_start)

download_start_timestamp = time.time()
for img in images:
    download_file(img)
download_end_timestamp = time.time()

print "downloaded {0} images in {1} seconds".format(len(images), download_end_timestamp - download_start_timestamp)


#s3conn = S3Connection(os.environ['S3KEY'], os.environ['S3SECRET'])
#bucket = s3conn.create_bucket('ta-subreddit-mirror-images')
#bucket.set_acl('public-read')
#
#for l in links[0:1]:
#    upload_file(bucket, l)


#shutil.rmtree(files_dir)


