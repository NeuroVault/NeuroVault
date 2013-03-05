from django.db import models
from django.core.urlresolvers import reverse

class Study(models.Model):
    name = models.CharField(max_length=200, unique = True, null=False)
    DOI = models.CharField(max_length=200, unique=True, blank=True, null=True, default=None)
    description = models.CharField(max_length=200, blank=True)
    
    def get_absolute_url(self):
        return reverse('statmaps:study_details', args=[str(self.id)])
    
    def __unicode__(self):
        return self.name


def upload_to(instance, filename):
    return "statmaps/%s/%s"%(instance.study.name, filename)
    
class StatMap(models.Model):
    study = models.ForeignKey(Study)
    name = models.CharField(max_length=200, null=False, blank=False)
    description = models.CharField(max_length=200, blank=True)
    file = models.FileField(upload_to=upload_to, null=False, blank=False)
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        unique_together = ("study", "name")