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

        col_name = 'Yeo et al. (2015) - 14 components'

        user = User.objects.get(username="neurovault")
        try:
            collection = Collection(name=col_name, owner=user)
            collection.save()
        except IntegrityError:
            Collection.objects.get(name=col_name).delete()
            collection = Collection(name=col_name, owner=user)
            collection.save()

        collection.description = "14 components used to decode 83 cognitive task. Task come from the Cognitive Paradigm Ontology (CogPO). Components were derived from the BrainMap database."
        collection.name = col_name
        collection.topic_set = True
        collection.save()

        saved = save_statmap_form(image_path=map_file,
                                  collection=collection,
                                  image_name="14 Component Model")

        collection = Collection.objects.get(name=col_name)
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