#!/usr/bin/env python
import shutil

from urllib2 import urlopen, HTTPError, URLError
import time

import re
import os
import pypyodbc
from pyimgur import Imgur
from boto.s3.key import Key
from boto.s3.connection import S3Connection
import yaml
from bs4 import BeautifulSoup

from config import initialize_config

def get_album_images(url):
    album_id = os.path.splitext(os.path.basename(url))[0]
    im = Imgur(os.environ['IMGURCLIENTID'])
    album = im.get_album(album_id)
    album_images = [image.link for image in album.images]

    return album_images


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
        try_count = 0
        valid_response = False
        while try_count <= 5:
            try_count += 1
            image_source = urlopen(url)
            if not image_source.info().gettype().lower().startswith("image"):
                print "got {0} response from imgur. will retry.".format(image_source.info().gettype())
                time.sleep(1)
                continue
            else:
                valid_response = True
                break

        if not valid_response and try_count == 5:
            raise Exception("Failed to download {0} in {1} attempts.", url, try_count)

        time.sleep(0.5)
        dest_image = os.path.join(files_dir, os.path.basename(url))
        with open(dest_image, 'wb') as image_file:
            image_file.write(image_source.read())

        print('finished ' + os.path.basename(url))

    except HTTPError, e:
        print "HTTP Error:", e.code, url
    except URLError, e:
        print "URL Error:", e.reason, url
    except Exception, e:
        print 'awesome error ', e
    except:
        print 'awesome error ', url


def initialize_files_dir():
    files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")

    if os.path.exists(files_dir):
        shutil.rmtree(files_dir)

    time.sleep(2)
    os.mkdir(files_dir)
    return files_dir


def get_subreddit_html():
    page_html = ""
    while True:
        try:
            if not os.path.exists('aww.txt') or os.stat('aww.txt').st_size == 0:
                print 'aww.txt does not exist or is empty. going to reddit'
                page = urlopen('http://www.reddit.com/r/aww?limit=100', timeout=20)
                page_html = page.read()
                with open('aww.txt', 'w') as input_file:
                    try:
                        input_file.write(page_html)
                        break
                    except UnicodeDecodeError, e:
                        print "UnicodeDecodeError: ", e.reason
            else:
                print "opening cached file"
                page_html = open('aww.txt', 'r').read()
                break
        except HTTPError:
            print "http error. trying again."
            time.sleep(3)
            continue

    return page_html


def get_subreddit_image_links(html):
    """
    as described here [http://api.imgur.com/models/image], imgur file names are 5-7 characters in length and have one of these characters [sbtmlh] at the end to specify image size.
    since we manually append size 't' for thumbnails, we need to obtain the imgur url 'without' the size specifier.
    imgur_image_regex has two groups that we use, one for the image name up to (but not including) the size specifier, and another for the file extension.
    e.g. for http://i.imgur.com/dFuYFdJh.jpg, group 1 is: "http://i.imgur.com/dFuYFdJ" (no h at the end) and group 4 is ".jpg"
    for http://i.imgur.com/dFuYFdJ.jpg (no size specifier), group 1 is again "http://i.imgur.com/dFuYFdJ" and group 4 is ".jpg"
    for gallery urls like http://imgur.com/a/IPhHW group 4 will be empty and we will only use group 1

    :param html: subreddit html
    :return: list of imgur single image and gallery links
    """
    soup = BeautifulSoup(html)
    entries = soup.select("div.entry a.title")
    links = []
    for entry in entries:
        mtc = imgur_image_regex.match(entry['href'])
        if not mtc:
            continue

        links.append(mtc.group(1) + (mtc.group(4) or "")) # group(4) (file extension) is empty for gallery urls and single image page urls http://imgur.com/dFuYFdJ

    return links


def get_all_imgur_images(links):
    print("collecting gallery images")
    images = []
    gallery_collect_start = time.time()
    for link in links:
        if gallery_url_regex.search(link):
            [images.append(img) for img in get_album_images(link)]
        elif not image_extension_regex.search(link):
            images.append(link + '.jpg')
        else:
            images.append(link)
    gallery_collect_end = time.time()

    return images, (gallery_collect_end - gallery_collect_start)


def download_all_images(images):
    download_start_timestamp = time.time()
    for img in images:
        download_file(img) # download image (asd123.jpg)
        download_file(re.sub(image_extension_regex, r't.\1', img)) # download thumbnail (asd123t.jpg)
    download_end_timestamp = time.time()
    return download_end_timestamp - download_start_timestamp


def upload_all_images(images):
    upload_start_timestamp = time.time()
    s3conn = S3Connection(os.environ['S3KEY'], os.environ['S3SECRET'])
    bucket = s3conn.create_bucket(os.environ['S3BUCKETNAME'])
    bucket.set_acl('public-read')

    for i in images:
        try:
            upload_file(bucket, i)
        except:
            continue

    upload_end_timestamp = time.time()

    return upload_end_timestamp - upload_start_timestamp


def update_image_database(images):
    def get_insert_param(list):
        total = 0
        for l in list:
            total += 1
            yield (os.path.basename(l), 'GETDATE()', total)

    params = ["('{0}', {1}, {2})".format(*i) for i in list(get_insert_param(images))]
    insert_statement = "insert into images (image_id, created_date, display_order) values " + ", ".join(params)

    db_start_timestamp = time.time()
    conn = pypyodbc.connect(driver='{SQL Server}', server=os.environ['DBSERVER'], database=os.environ['DBNAME'], uid=os.environ['DBUSER'], pwd=os.environ['DBPASS'])
    cur = conn.cursor()
    cur.execute("truncate table images").commit()
    cur.execute(insert_statement).commit()
    db_end_timestamp = time.time()

    return db_end_timestamp - db_start_timestamp


imgur_image_regex = re.compile("^(https?:\/\/(?:i\.|m\.|edge\.|www\.)*imgur\.com\/(?!gallery)(?!removalrequest)(?!random)(?!memegen)(a/)?([A-Za-z0-9]{5}|[A-Za-z0-9]{7}))[sbtmlh]?(\.(?:jpe?g|gif|png))?(\?.*)?$", re.IGNORECASE)
image_extension_regex = re.compile("\.(jpe?g|gif|png)$", re.IGNORECASE)
gallery_url_regex = re.compile("/a/", re.IGNORECASE)

initialize_config()
files_dir = initialize_files_dir()
html = get_subreddit_html()
links = get_subreddit_image_links(html)

images, gallery_images_elapsed = get_all_imgur_images(links)
print "got {0} links and {1} images in {2} seconds".format(len(links), len(images), gallery_images_elapsed)

image_download_elapsed = download_all_images(images)
print "downloaded {0} images in {1} seconds".format(len(images), image_download_elapsed)

image_upload_elapsed = upload_all_images(images)
print "uploaded {0} images to s3 in {1} seconds".format(len(images), image_upload_elapsed)

db_update_elapsed = update_image_database(images)
print "updated database in {0} seconds".format(db_update_elapsed)

