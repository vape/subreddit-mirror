#!/usr/bin/env python

from urllib2 import urlopen, HTTPError, URLError
import re
import os
import shutil

from bs4 import BeautifulSoup

def download_file(url):
    try:
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


files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")
if not os.path.exists(files_dir):
    os.mkdir(files_dir)

imgur_single_image_regex = re.compile("^https?:\/\/(?:i\.|m\.|edge\.|www\.)*imgur\.com\/(?!gallery)(?!removalrequest)(?!random)(?!memegen)([A-Za-z0-9]{5}|[A-Za-z0-9]{7})[sbtmlh]?(\.(?:jpe?g|gif|png))?$", re.IGNORECASE)
#imgur_image_regex = re.compile("^https?:\/\/(?:i\.|m\.|edge\.|www\.)*imgur\.com\/(?!gallery)(?!removalrequest)(?!random)(?!memegen)(a/)?([A-Za-z0-9]{5}|[A-Za-z0-9]{7})[sbtmlh]?(\.(?:jpe?g|gif|png))?(\?.*)?$", IGNORECASE)
image_extension_regex = re.compile("\.(jpe?g|gif|png)$", re.IGNORECASE)

#page = urllib2.urlopen('http://www.reddit.com/r/aww')
file = open('aww.txt', 'r')
soup = BeautifulSoup(file.read())
#file.write(soup.prettify().encode('utf-8'))
#file.flush()
#file.close()
entries = soup.select("div.entry a.title")

links = [entry['href'] for entry in entries if imgur_single_image_regex.match(entry['href'])]

for i, link in enumerate(links):
    if not image_extension_regex.search(link):
        links[i] = link + '.jpg'

print(links)

for l in links[0:2]:
    download_file(l)

#shutil.rmtree(files_dir)


