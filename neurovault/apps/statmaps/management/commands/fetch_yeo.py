from django.core.management.base import BaseCommand, CommandError

from neurovault.apps.statmaps.tests.utils import save_statmap_form
from neurovault.apps.statmaps.models import User, Collection
import urllib
import tempfile
import os
import zipfile
from django.db.utils import IntegrityError

class Command(BaseCommand):

    def handle(self, *args, **options):

        tmpdir = tempfile.mkdtemp()
        dst = os.path.join(tmpdir, "yeo.zip")
        #print "downloading maps"
        urllib.urlretrieve("ftp://surfer.nmr.mgh.harvard.edu/pub/data/Yeo_CerebCortex2015_Brainmap.zip", dst)

        z = zipfile.ZipFile(dst)
        z.namelist()

        map_file = z.extract('YeoBrainmapMNI152/FSL/Yeo_14Comp_PrActGivenComp_FSL_MNI152_2mm.nii.gz',
                                   os.path.join(tmpdir, "14maps.nii.gz"))
        weights_file = z.extract('YeoBrainmapMNI152/FSL/Yeo_14Comp_PrCompGivenTasks.csv',
                                        os.path.join(tmpdir, "14maps.csv"))

        user = User.objects.get(username="neurovault")
        try:
            collection = Collection(name='Yeo et. al 14 components', owner=user)
            collection.save()
        except IntegrityError:
            Collection.objects.get(name='Yeo et. al 14 components').delete()
            collection = Collection(name='Yeo et. al 14 components', owner=user)
            collection.save()



        saved = save_statmap_form(image_path=map_file,
                                  collection=collection,
                                  image_name="14 Component Model")

        collection = Collection.objects.get(name='Yeo et. al 14 components')
        import pandas
        df = pandas.read_csv(weights_file)
        for map in collection.basecollectionitem_set.all():
            print map
            c_id = int(map.name.split("volume ")[1][:-1])
            d = {}
            for j, name in enumerate(df['Tasks']):
                d[name] = float(df['Pr(Comp %d | Task)' % c_id][j])
            d['component number'] = c_id
            map.data = d
            map.save()
            print map.data
        collection.save()

        collection = Collection.objects.get(name='Yeo et. al 14 components')
        for map in collection.basecollectionitem_set.all():
            print map
            c_id = int(map.name.split("volume ")[1][:-1])
            d = {}
            for j, name in enumerate(df['Tasks']):
                d[name] = float(df['Pr(Comp %d | Task)' % c_id][j])
            d['component number'] = c_id
            map.data = d
            map.save()
            print map.data
        collection.save()