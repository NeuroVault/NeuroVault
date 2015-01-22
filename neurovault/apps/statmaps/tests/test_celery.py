# in one terminal window: 
# activate always: source /opt/nv_env/bin/activate
# start redis: sudo /etc/init.d/redis_6379 start
# python manage.py celeryd -l INFO

# in second, use python console:
# cd /opt/nv_env/NeuroVault
# python manage.py shell
# sudo service uwsgi restart must be done each time, as well as
from neurovault.apps.statmaps.tasks import generate_glassbrain_image, make_correlation_df
from django.shortcuts import get_object_or_404
from neurovault.apps.statmaps.models import Image

pks = [1,2,3,4,5]
for pk in pks:
  try:
    image = get_object_or_404(Image,pk=pk)
    generate_glassbrain_image.delay(image.file.path,pk)
  except:
    print "Cannot do pk %s" %(pk)

# How do I get a collection?
cid=1
keyargs = {'pk':cid}
collection = Collection.objects.get(**keyargs)

# Testing image pairwise matrix generation  
# defaults: pkl_path = "/opt/image_data/matrices/pearson_corr.pkl"
# defaults: resample_dim = [4,4,4]
make_correlation_df()

