from django.db import models
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
# from django.db.models.signals import post_save
# from django.dispatch import receiver
from neurosynth.base import imageutils
import os

class Study(models.Model):
    name = models.CharField(max_length=200, unique = True, null=False)
    DOI = models.CharField(max_length=200, unique=True, blank=True, null=True, default=None)
    description = models.CharField(max_length=200, blank=True)
    owner = models.ForeignKey(User)
    add_date = models.DateTimeField('date published', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    def get_absolute_url(self):
        return reverse('study_details', args=[str(self.id)])
    
    def __unicode__(self):
        return self.name

def upload_to(instance, filename):
    return "statmaps/%s/%s"%(instance.study.name, filename)
    
class StatMap(models.Model):
    study = models.ForeignKey(Study)
    name = models.CharField(max_length=200, null=False, blank=False)
    description = models.CharField(max_length=200, blank=True)
    file = models.FileField(upload_to=upload_to, null=False, blank=False)
    json_path = models.CharField(max_length=200, null=False, blank=True)
    add_date = models.DateTimeField('date published', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        unique_together = ("study", "name")

    def save(self):

        # Save the file before the rest of the data so we can convert it to json
        if self.file and not os.path.exists(self.file.path):
            self.file.save(self.file.name, self.file, save = False)
        # Convert binary image to JSON using neurosynth
        try:
            if os.path.exists(self.file.path):
                json_file = self.file.path + '.json'
                try:
                    imageutils.img_to_json(self.file.path, swap=True, save=json_file)
                    self.json_path = self.file.url + '.json'
                except Exception, e:
                    pass
        except Exception, e:
            pass
        super(StatMap, self).save()

