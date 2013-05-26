from django.db import models
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
# from django.db.models.signals import post_save
# from django.dispatch import receiver
from neurosynth.base import imageutils
import os
from neurovault.apps.statmaps.storage import NiftiGzStorage
from taggit.managers import TaggableManager
from taggit.models import GenericTaggedItemBase, TagBase
import urllib2
from xml.etree import ElementTree
import datetime

class Study(models.Model):
    name = models.CharField(max_length=200, unique = True, null=False)
    DOI = models.CharField(max_length=200, unique=True, blank=True, null=True, default=None)
    authors = models.CharField(max_length=200, blank=True, null=True)
    url = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User)
    add_date = models.DateTimeField('date published', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    def get_absolute_url(self):
        return reverse('study_details', args=[str(self.id)])
    
    def __unicode__(self):
        return self.name
    
    def save(self):

        # Save the file before the rest of the data so we can convert it to json
        if self.DOI:
            try:
                self.name, self.authors, self.url, _ = getPaperProperties(self.DOI)
            except:
                pass
            
        super(Study, self).save()
        
def getPaperProperties(doi):
    xmlurl = 'http://doi.crossref.org/servlet/query'
    xmlpath = xmlurl + '?pid=k.j.gorgolewski@sms.ed.ac.uk&format=unixref&id=' + urllib2.quote(doi)
    xml_str = urllib2.urlopen(xmlpath).read()
    doc = ElementTree.fromstring(xml_str)
    if len(doc.getchildren()) == 0 or len(doc.findall('.//crossref/error')) > 0:
        raise Exception("DOI %s was not found" % doi)
    title = doc.findall('.//title')[0].text
    authors = [author.findall('given_name')[0].text + " " + author.findall('surname')[0].text for author in doc.findall('.//contributors/person_name')]
    if len(authors) > 1:
        authors = ", ".join(authors[:-1]) + " and " + authors[-1]
    url = doc.findall('.//doi_data/resource')[0].text
    date_node = doc.findall('.//publication_date')[0]
    if len(date_node.findall('day')) > 0:
        publication_date = datetime.date(int(date_node.findall('year')[0].text),
                                         int(date_node.findall('month')[0].text),
                                         int(date_node.findall('day')[0].text))
    elif len(date_node.findall('month')) > 0:
        publication_date = datetime.date(int(date_node.findall('year')[0].text),
                                         int(date_node.findall('month')[0].text),
                                         1)
    else:
        publication_date = datetime.date(int(date_node.findall('year')[0].text),
                                         1,
                                         1)
    return title, authors, url, publication_date

def upload_to(instance, filename):
    return "statmaps/%s/%s"%(instance.study.name, filename)

class LowerCaseTag(TagBase):
    value = models.CharField(max_length=200, blank=True)

class ValueTaggedItem(GenericTaggedItemBase):
    tag = models.ForeignKey(LowerCaseTag, related_name="tagged_items")

class StatMap(models.Model):
    study = models.ForeignKey(Study)
    name = models.CharField(max_length=200, null=False, blank=False)
    description = models.CharField(max_length=200, blank=True)
    file = models.FileField(upload_to=upload_to, null=False, blank=False, storage=NiftiGzStorage())
    hdr_file = models.FileField(upload_to=upload_to, blank=True, storage=NiftiGzStorage())
    json_path = models.CharField(max_length=200, null=False, blank=True)
    add_date = models.DateTimeField('date published', auto_now_add=True)
    modify_date = models.DateTimeField('date modified', auto_now=True)
    tags = TaggableManager(through=ValueTaggedItem, blank=True)
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        unique_together = ("study", "name")

    def save(self):

        # Save the file before the rest of the data so we can convert it to json
        if self.file and not os.path.exists(self.file.path):
            self.file.save(self.file.name, self.file, save = False)
        if self.hdr_file and not os.path.exists(self.hdr_file.path):
            self.file.save(self.hdr_file.name, self.hdr_file, save = False)
        # Convert binary image to JSON using neurosynth
#         try:
        if os.path.exists(self.file.path):
            json_file = self.file.path + '.json'
#                 try:
            imageutils.img_to_json(self.file.path, swap=True, save=json_file)
            self.json_path = self.file.url + '.json'
#                 except Exception, e:
#                     pass
#         except Exception, e:
#             pass
        super(StatMap, self).save()

