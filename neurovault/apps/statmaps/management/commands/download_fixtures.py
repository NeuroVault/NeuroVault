from django.core.management.base import BaseCommand, CommandError
import os.path
from neurovault.apps import statmaps
import urllib
import zipfile
import subprocess
import tempfile
import shutil


def copyTree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(d):
            shutil.rmtree(d)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy(s, d)


class Command(BaseCommand):
    args = '<fixture_name fixture_name ...>'
    help = 'downloads fixtures'

    def handle(self, *args, **options):
        statmapsPath = os.path.abspath(statmaps.__path__[0])
        fixturesDir = os.path.join(statmapsPath, 'fixtures')
        if not os.path.exists(fixturesDir):
            os.makedirs(fixturesDir)
        print args
        if args:
            temp1 = tempfile.mkdtemp()
            for fixtureName in args:
                fileName = fixtureName + '.zip'
                url = 'https://github.com/jbwexler/neurovault_data/trunk/fixtures/%s' % fileName
                (path, _) = urllib.urlretrieve(url)
                with zipfile.ZipFile(path, "r") as z:
                    # extract everything except for _MACOSX folder, which contains redundant data
                    z.extractall(temp1, [x for x in z.namelist() if not x.startswith('__MACOSX')])
            for folder in os.listdir(temp1):
                copyTree(os.path.join(temp1, folder), fixturesDir)
            shutil.rmtree(temp1)

        else:
            temp1 = tempfile.mkdtemp()
            temp2 = tempfile.mkdtemp()
            command = "svn export https://github.com/erramuzpe/neurovault_data/trunk/fixtures %s --force" % temp1
            p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
            (output, err) = p.communicate()
            for fileName in os.listdir(temp1):
                # print os.path.join(temp1, fileName)
                with zipfile.ZipFile(os.path.join(temp1, fileName), "r") as z:
                    # extract everything except for _MACOSX folder, which contains redundant data
                    z.extractall(temp2, [x for x in z.namelist() if not x.startswith('__MACOSX')])
            for folder in os.listdir(temp2):
                copyTree(os.path.join(temp2, folder), fixturesDir)
            shutil.rmtree(temp1, temp2)
