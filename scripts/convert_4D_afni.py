import os
import django
import tempfile
import shutil

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurovault.settings")
django.setup()

from neurovault.apps.statmaps.models import Image,ValueTaggedItem
from neurovault.apps.statmaps.utils import detect_4D, split_4D_to_3D,memory_uploadfile


def populate_afni(image):
    try:
        orig_name = image.name
        tmpdir = tempfile.mkdtemp()
        bricks = split_4D_to_3D(image.file.path,tmp_dir=tmpdir)

        for label,brick in bricks:
            brick_fname = os.path.split(brick)[-1]
            mfile = memory_uploadfile(brick, brick_fname, image.file)
            brick_img = Image(name='%s - %s' % (orig_name, label), file=mfile)
            for field in ['collection','description','map_type','tags']:
                setattr(brick_img, field, getattr(image,field))

            if image.tags.exists():
                brick_img.save()  # generate PK before copying tags
                for tag in image.tags.all():
                    tagobj = ValueTaggedItem(content_object=brick_img,tag=tag)
                    tagobj.save()
            brick_img.save()

    finally:
        print('converted afni4d %s to %s sub-brick images.' % (orig_name,len(bricks)))
        shutil.rmtree(tmpdir)
        os.remove(image.file.path)
        image.delete()


if __name__ == '__main__':
    afni = []
    bad_link = []
    error = []

    for n,image in enumerate(Image.objects.all()):
        if os.path.exists(image.file.path):
            try:
                if detect_4D(image.file.path):
                    print('found afni4d: %s' % image.file.path)
                    populate_afni(image)
            except:
                error.append(image.file.path)
        else:
            bad_link.append(image.file.path)

    print('\n other issues:')
    for bd in bad_link:
        print('found bad path: %s' % bd)

    print('\n\n\n')
    for er in error:
        print('unable to parse file %s' % er)
