import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurovault.settings")
django.setup()

from neurovault.apps.statmaps.models import Image
from neurovault.apps.statmaps.utils import detect_afni4D

if __name__ == '__main__':
    afni = []
    bad = []
    notafni = []

    for n,image in enumerate(Image.objects.all()):
        if os.path.exists(image.file.path):
            try:
                if detect_afni4D(image.file.path):
                    afni.append(image.file.path)
                else:
                    notafni.append(image.file.path)
            except:
                bad.append('unable to parse file %s' % image.file.path)
        else:
            bad.append('found bad path: %s' % image.file.path)

    for af in afni:
        print 'found afni4d: %s' % af
    print '\nalso found issues:'
    for bd in bad:
        print bd
    print '\n\n'
    #for notaf in notafni:
    #    print 'not afni: %s' % image.file.path

