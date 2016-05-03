from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models.query_utils import Q

from neurovault.apps.statmaps.models import Collection

template = """<p>Dear {username},<br \>
Twice a year data from NeuroVault are deposited in Stanford Digital
Repository (SDR). The mission of SDR is to preserve important scientific dataset for decades. They increase chances of
long-term data accessibility by mirroring datasets at multiple data centers distributed across the globe. In two weeks
we will be depositing a snapshot of NeuroVault data in SDR. Only public collections with a DOI of a corresponding paper
will be included in the deposition. It seems that you currently have {collection_noun} that are either private or do not
have a DOI of a corresponding paper:</p>
<ul>
{collections}
</ul>
<p>If it was work in progress and since you uploaded the maps a corresponding paper was published please log in and edit
the collection metadata providing the DOI. It is also a great opportunity to upload maps, atlases, and parcellations
from your other papers. Depositing data in NeuroVault increases the exposure of your research and makes it easier for
other researchers to build upon thus increasing your citation rates.</p>

<p>Best regards,<br />
NeuroVault Team</p>"""

for user in User.objects.all():
    collections = Collection.objects.filter(owner=user).filter(Q(DOI__isnull=True) | Q(private=True))
    collections = [col for col in collections if col.basecollectionitem_set.count() > 0]
    if collections:
        if user.first_name:
            email = template.replace("{username}", user.first_name.capitalize())
        else:
            email = template.replace("{username}", "NeuroVault User")

        if len(collections) == 1:
            email = email.replace("{collection_noun}", "a collection")
        else:
            email = email.replace("{collection_noun}", "collections")

        collections_text = "\n".join(["<li><a href='http://neurovault.org%s'>%s</a></li>" % (col.get_absolute_url(), col.name)
                                      for col in collections])
        email = email.replace("{collections}", collections_text)
        send_mail("Time to update your NeuroVault maps", email, "team@neurovault.org",
                  "krzysztof.gorgolewski@gmail.com", html_message=True)