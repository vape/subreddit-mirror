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


def get_album_images(url):
    album_id = os.path.splitext(os.path.basename(url))[0]
    im = Imgur(os.environ['IMGURCLIENTID'])
    album = im.get_album(album_id)
    album_images = [image.link for image in album.images]

    return album_images


def initialize_config():
    if [k for k in ['S3KEY', 'S3SECRET', 'S3BUCKETNAME', 'IMGURCLIENTID', 'IMGURSECRET', 'DBSERVER', 'DBNAME', 'DBUSER', 'DBPASS', 'DBPORT'] if k in os.environ.keys()]:
        print('all keys exist')
        return

    if not os.path.exists('env.yaml'):
        raise Exception('env.yaml required for config initialization')

    with open('env.yaml', 'r') as config_file:
        config = yaml.load(config_file)
        os.environ['S3KEY'] = config['s3config']['key']
        os.environ['S3SECRET'] = config['s3config']['secret']
        os.environ['S3BUCKETNAME'] = config['s3config']['bucketname']

        os.environ['IMGURCLIENTID'] = config['imgurconfig']['clientid']
        os.environ['IMGURSECRET'] = config['imgurconfig']['secret']

        os.environ['DBSERVER'] = config['dbconfig']['dbserver']
        os.environ['DBNAME'] = config['dbconfig']['dbname']
        os.environ['DBUSER'] = config['dbconfig']['username']
        os.environ['DBPASS'] = config['dbconfig']['password']
        os.environ['DBPORT'] = str(config['dbconfig']['port'])


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


def initialize_files_dir():
    files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")

    if os.path.exists(files_dir):
        shutil.rmtree(files_dir)

    time.sleep(2)
    os.mkdir(files_dir)
    return files_dir


def get_subreddit_html():
    if not os.path.exists('aww.txt') or os.stat('aww.txt').st_size == 0:
        print 'aww.txt does not exist or is empty. going to reddit'
        page = urlopen('http://www.reddit.com/r/aww?limit=100', timeout = 20)
        html = page.read()
        with open('aww.txt', 'w') as file:
            try:
                file.write(html)
            except UnicodeDecodeError, e:
                print "UnicodeDecodeError: ", e.reason
    else:
        print "opening cached file"
        html = open('aww.txt', 'r').read()

    return html


def get_subreddit_image_links(html):
    soup = BeautifulSoup(html)
    entries = soup.select("div.entry a.title")
    links = []
    for entry in entries:
        mtc = imgur_image_regex.match(entry['href'])
        if not mtc:
            continue
        links.append(mtc.group(1))

    return links


def get_all_imgur_images(links):
    print("collecting gallery images")
    images = []
    gallery_collect_start = time.time()
    for i, link in enumerate(links):
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
        download_file(img)
    download_end_timestamp = time.time()
    return download_end_timestamp - download_start_timestamp


def upload_all_images(images):
    upload_start_timestamp = time.time()
    s3conn = S3Connection(os.environ['S3KEY'], os.environ['S3SECRET'])
    bucket = s3conn.create_bucket(os.environ['S3BUCKETNAME'])
    bucket.set_acl('public-read')

    for i in images:
        upload_file(bucket, i)

    upload_end_timestamp = time.time()

    return upload_end_timestamp - upload_start_timestamp


def update_image_database(images):
    def get_insert_param(list):
        total = 0
        for l in list:
            total += 1
            yield (os.path.splitext(os.path.basename(l))[0], 'GETDATE()', total)

    params = ["('{0}', {1}, {2})".format(*i) for i in list(get_insert_param(images))]
    insert_statement = "insert into images (image_id, created_date, display_order) values " + ", ".join(params)

    db_start_timestamp = time.time()
    conn = pypyodbc.connect(driver='{SQL Server}', server='srmirrordb.cdos5ymus8o5.us-east-1.rds.amazonaws.com', database='srmirrordb', uid='srmirrordbuser', pwd='hedehodo2013')
    cur = conn.cursor()
    cur.execute("truncate table images").commit()
    cur.execute(insert_statement).commit()
    db_end_timestamp = time.time()

    return db_end_timestamp - db_start_timestamp


imgur_image_regex = re.compile("^(https?:\/\/(?:i\.|m\.|edge\.|www\.)*imgur\.com\/(?!gallery)(?!removalrequest)(?!random)(?!memegen)(a/)?([A-Za-z0-9]{5}|[A-Za-z0-9]{7})[sbtmlh]?(\.(?:jpe?g|gif|png))?)(\?.*)?$", re.IGNORECASE)
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




