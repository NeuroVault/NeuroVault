
from future import standard_library
standard_library.install_aliases()
from builtins import str
import json, requests
import os, errno
import urllib.request, urllib.parse, urllib.error

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

collections = []
next_url_url = "https://neurovault.org/api/collections/?format=json"
target_folder = "/media/rwblair/backup_1/neurovault_backup"

while next_url_url:
    print("fetching %s"%next_url_url)
    resp = requests.get(url=next_url_url)
    data = json.loads(resp.text)
    collections += [res for res in data['results'] if res['DOI'] != None]
    next_url_url = data['next']

print("Fetched metadata of %d collections"%len(collections))

images_url_template = "http://neurovault.org/api/collections/%d/images/"

for collection in collections:
    next_url = images_url_template%collection['id']
    images = []
    while next_url:
        print("fetching %s"%next_url)
        resp = requests.get(url=next_url)
        data = json.loads(resp.text)
        images += data['results']
        next_url = data['next']
    if len(images) == 0:
        collections.remove(collection)
        continue

    mkdir_p(target_folder + "/%d"%collection['id'])
    json.dump(images, open(target_folder + "/%d/images.json"%collection['id'], "w"), indent=4, sort_keys=True)
    for image in images:
        print("fetching %s"%image['file'])
        try:
            urllib.request.urlretrieve(image['file'], target_folder + "/%d/"%collection['id'] + str(image['id']) + ".nii.gz")
        except:
            print("failed to download %s"%image['file'])

json.dump(collections, open(target_folder + "/collections.json", "w"), indent=4, sort_keys=True)
