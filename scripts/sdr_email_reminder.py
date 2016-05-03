from django.contrib.auth.models import User
from django.db.models.query_utils import Q

from neurovault.apps.statmaps.models import Collection

for user in User.object.all():
    collections = Collection.objects.filter(owner=user).filter(Q(DOI__isnull=True) | Q(private=True))
    collections = [col for col in collections if col.basecollectionitem_set.count() > 0]
    if collections:
        print user.username
        for col in collections:
            print col.name + " " + col.get_absolute_url()

        print "\n"