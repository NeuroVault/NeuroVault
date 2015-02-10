from django.test import TestCase
from neurovault.apps.statmaps.tasks import generate_glassbrain_image, make_correlation_df
from django.shortcuts import get_object_or_404
from neurovault.apps.statmaps.models import Image

# This needs to be refined to test whatever actual celery implementation is done
# I will leave manual notes here for now
# in one terminal window: 
# activate always: source /opt/nv_env/bin/activate
# start redis: sudo /etc/init.d/redis_6379 start
# python manage.py celeryd -l INFO

# in second, use python console:
# cd /opt/nv_env/NeuroVault
# python manage.py shell
# sudo service uwsgi restart must be done each time, as well as

class Test_celery_tasks(pk):
    def setUp(self):
      image = get_object_or_404(Image,pk=pk)

    def test_generate_glass_brain(self):
      generate_glassbrain_image.delay(pk)

    def test_make_correlation_df(self):
      # Testing image pairwise matrix generation  
      # defaults: pkl_path = "/opt/image_data/matrices/pearson_corr.pkl"
      # defaults: resample_dim = [4,4,4]
      make_correlation_df()
