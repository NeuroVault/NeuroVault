# cd /opt/nv_env/NeuroVault
# sudo service uwsgi restart must be done each time, as well as
# python manage.py celeryd -l INFO
from neurovault.apps.statmaps.tasks import generate_glassbrain_image
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

