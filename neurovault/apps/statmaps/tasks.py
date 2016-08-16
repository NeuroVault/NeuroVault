from __future__ import absolute_import

import nilearn
from django.core.files.base import ContentFile
from django.http import Http404
from django.shortcuts import get_object_or_404
from pybraincompare.compare.maths import calculate_correlation, calculate_pairwise_correlation
from pybraincompare.compare.mrutils import resample_images_ref, make_binary_deletion_mask, make_binary_deletion_vector
from pybraincompare.mr.datasets import get_data_directory
from pybraincompare.mr.transformation import make_resampled_transformation_vector


nilearn.EXPAND_PATH_WILDCARDS = False
from nilearn.plotting import plot_glass_brain
from celery import shared_task, Celery
from six import BytesIO
import nibabel as nib
import pylab as plt
import numpy
import urllib, json, tarfile, requests, os
from StringIO import StringIO
import xml.etree.cElementTree as e
from django.db import IntegrityError
from django.core.files.uploadedfile import SimpleUploadedFile
import re
from django.conf import settings
import pickle
import numpy as np

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'neurovault.settings')
app = Celery('neurovault')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task(name='crawl_anima')
def crawl_anima():
    import neurovault.apps.statmaps.models as models
    from neurovault.apps.statmaps.forms import StatisticMapForm, CollectionForm
    username = "ANIMA"
    email = "a.reid@fz-juelich.de"
    try:
        anima_user = models.User.objects.create_user(username, email)
        anima_user.save()
    except IntegrityError:
        anima_user = models.User.objects.get(username=username, email=email)
    
    url = "http://anima.fz-juelich.de/api/studies"
    response = urllib.urlopen(url);
    datasets = json.loads(response.read())
    
    # results = tarfile.open(mode="r:gz", fileobj=StringIO(response.content))
    #     for member in results.getmembers():
    #         f = results.extractfile(member)
    #         if member.name.endswith(".study"):
                
    for url in datasets:
        response = requests.get(url)
        content = response.content.replace("PubMed ID", "PubMedID")
        xml_obj = e.fromstring(content)
        
        version = xml_obj.find(".").find(".//Element[@name='Version']").text.strip()
        study_description = xml_obj.find(".//Element[@name='Description']").text.strip()
        study_description += " This dataset was automatically imported from the ANIMA <http://anima.modelgui.org/> database. Version: %s"%version
        study_name = xml_obj.find(".").attrib['name']
        
        tags = xml_obj.find(".//Element[@name='Keywords']").text.strip().split(";")
        tags.append("ANIMA")
        doi = xml_obj.find(".//Element[@name='DOI']")
        pubmedid = xml_obj.find(".//Element[@name='PubMedID']")
    
        post_dict = {
            'name': study_name,
            'description': study_description,
            'full_dataset_url': "http://anima.fz-juelich.de/api/studies/" + os.path.split(url)[1].replace(".study", "")
        }
        if doi != None:
            post_dict['DOI'] = doi.text.strip()
        elif pubmedid != None:
            pubmedid = pubmedid.text.strip()
            url = "http://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids=%s&format=json" % pubmedid
            response = urllib.urlopen(url);
            parsed = json.loads(response.read())
            post_dict['DOI'] = parsed['records'][0]['doi']
        
        try:
            col = models.Collection.objects.get(DOI=post_dict['DOI'])
        except models.Collection.DoesNotExist:
            col = None
        
        if col and not col.description.endswith(version):
            col.DOI = None
            old_version = re.search(r"Version: (?P<version>\w)", col.description).group("version")
            col.name = study_name + " (version %s - deprecated)"%old_version
            col.save()
        
        if not col or not col.description.endswith(version):
            collection = models.Collection(owner=anima_user)
            form = CollectionForm(post_dict, instance=collection)
            form.is_valid()
            collection = form.save()
            
            arch_response = requests.get(url.replace("library", "library/archives").replace(".study", ".tar.gz"))
            arch_results = tarfile.open(mode="r:gz", fileobj=StringIO(arch_response.content))
        
            for study_element in xml_obj.findall(".//StudyElement[@type='VolumeFile']"):
                image_name = study_element.attrib['name'].strip()
                image_filename = study_element.attrib['file']
                try:
                    image_fileobject = arch_results.extractfile(xml_obj.find(".").attrib['directory'] + "/" +
                                                                image_filename)
                except KeyError:
                    image_fileobject = arch_results.extractfile(
                        xml_obj.find(".").attrib['directory'] + "/" + xml_obj.find(".").attrib['directory'] + "/" +
                        image_filename)
        
                map_type = models.BaseStatisticMap.OTHER
        
                quantity_dict = {"Mask": models.BaseStatisticMap.M,
                                 "F-statistic": models.BaseStatisticMap.F,
                                 "T-statistic": models.BaseStatisticMap.T,
                                 "Z-statistic": models.BaseStatisticMap.Z,
                                 "Beta": models.BaseStatisticMap.U}
        
                quantity = study_element.find("./Metadata/Element[@name='Quantity']")
                if quantity != None:
                    quantity = quantity.text.strip()
                    if quantity in quantity_dict.keys():
                        map_type = quantity_dict[quantity]
        
                post_dict = {
                    'name': image_name,
                    'modality': models.StatisticMap.fMRI_BOLD,
                    'map_type': map_type,
                    'analysis_level': models.BaseStatisticMap.M,
                    'collection': collection.pk,
                    'ignore_file_warning': True,
                    'cognitive_paradigm_cogatlas': 'None',
                    'tags': ", ".join(tags)
                }
                
                image_description = study_element.find("./Metadata/Element[@name='Caption']").text
                if image_description:
                    post_dict["description"] = image_description.strip()
                
                file_dict = {'file': SimpleUploadedFile(image_filename, image_fileobject.read())}
                form = StatisticMapForm(post_dict, file_dict)
                form.is_valid()
                form.save()


# THUMBNAIL IMAGE GENERATION ###########################################################################

@shared_task
def generate_glassbrain_image(image_pk):
    from neurovault.apps.statmaps.models import Image
    import matplotlib as mpl
    mpl.rcParams['savefig.format'] = 'jpg'
    my_dpi = 50
    fig = plt.figure(figsize=(330.0/my_dpi, 130.0/my_dpi), dpi=my_dpi)
    
    img = Image.objects.get(pk=image_pk)    
    f = BytesIO()
    try:
        glass_brain = plot_glass_brain(img.file.path, figure=fig)
        glass_brain.savefig(f, dpi=my_dpi)
    except:
        # Glass brains that do not produce will be given dummy image
        this_path = os.path.abspath(os.path.dirname(__file__))
        f = open(os.path.abspath(os.path.join(this_path,
                                              "static","images","glass_brain_empty.jpg"))) 
        raise
    finally:
        plt.close('all')
        f.seek(0)
        content_file = ContentFile(f.read())
        img.thumbnail.save("glass_brain_%s.jpg" % img.pk, content_file)
        img.save()

# IMAGE TRANSFORMATION ################################################################################

# Save 4mm, brain masked image vector in pkl file in image folder
@shared_task
def save_resampled_transformation_single(pk1, resample_dim=[4,4,4]):
    from neurovault.apps.statmaps.models import Image
    from neurovault.apps.statmaps.utils import is_search_compatible
    from six import BytesIO

    img = get_object_or_404(Image, pk=pk1)
    nii_obj = nib.load(img.file.path)   # standard_mask=True is default
    image_vector = make_resampled_transformation_vector(nii_obj,resample_dim)

    f = BytesIO()
    np.save(f, image_vector)
    f.seek(0)
    content_file = ContentFile(f.read())
    img.reduced_representation.save("transform_%smm_%s.npy" %(resample_dim[0],img.pk), content_file)

    resample_dim_engine = [16,16,16]
    image_vector_engine = make_resampled_transformation_vector(nii_obj, resample_dim_engine)

    f = BytesIO()
    np.save(f, image_vector_engine)
    f.seek(0)
    content_file = ContentFile(f.read())
    img.reduced_representation_engine.save("transform_%smm_%s.npy" % (resample_dim_engine[0], img.pk), content_file)

    # add to the engine
    if is_search_compatible(img.pk):
        insert_vector_engine(img.pk, image_vector_engine)

    return img

# ENGINE FUNCTIONS ####################################################################################


# TODO: Remove this when NearPy upgrades
@shared_task
def delete_vector_engine(data):
    from neurovault.apps.statmaps.utils import is_search_compatible

    if is_search_compatible(data):
        engine = pickle.load(open('/code/neurovault/apps/statmaps/tests/engine.p', "rb"))

        for lshash in engine.lshashes:
            for bucket_key in engine.storage.buckets[lshash.hash_name]:
                engine.storage.buckets[lshash.hash_name][bucket_key] = \
                    [(v, id) for v, id in engine.storage.buckets[lshash.hash_name][bucket_key] if id != data]

        pickle.dump(engine, open('/code/neurovault/apps/statmaps/tests/engine.p', "wb"))


@shared_task
def insert_vector_engine(pk, feature):
    engine = pickle.load(open('/code/neurovault/apps/statmaps/tests/engine.p', "rb"))

    feature[np.isnan(feature)] = 0
    engine.store_vector(feature.tolist(), pk)

    pickle.dump(engine, open('/code/neurovault/apps/statmaps/tests/engine.p', "wb"))

# COGNITIVE ATLAS
###########################################################################
def repopulate_cognitive_atlas(CognitiveAtlasTask=None,CognitiveAtlasContrast=None):
    if CognitiveAtlasTask==None:
        from neurovault.apps.statmaps.models import CognitiveAtlasTask
    if CognitiveAtlasContrast==None:
        from neurovault.apps.statmaps.models import CognitiveAtlasContrast

    from cognitiveatlas.api import get_task
    tasks = get_task()

    # Update tasks
    for t in range(0,len(tasks.json)):
        task = tasks.json[t]
        print "%s of %s" %(t,len(tasks.json)) 
        if tasks.json[t]["name"]:
            task, _ = CognitiveAtlasTask.objects.update_or_create(cog_atlas_id=task["id"],defaults={"name":task["name"]})
            task.save()
            if tasks.json[t]["id"]:
                task_details = get_task(id=tasks.json[t]["id"])
                if task_details.json[0]["contrasts"]:
                    print "Found %s contrasts!" %(len(task_details.json[0]["contrasts"]))
                    for contrast in task_details.json[0]["contrasts"]:
                        contrast, _ = CognitiveAtlasContrast.objects.update_or_create(cog_atlas_id=contrast["id"], 
                                                                                      defaults={"name":contrast["contrast_text"],
                                                                                      "task":task})
                        contrast.save() 

    # Add an "Other" contrast
    task = CognitiveAtlasTask.objects.filter(name="None / Other")[0]
    contrast, _ = CognitiveAtlasContrast.objects.update_or_create(cog_atlas_id="Other", 
                                                                  defaults={"name":"Other",
                                                                  "task":task})
                       
# HELPER FUNCTIONS ####################################################################################

'''Return list of Images sorted by the primary key'''
def get_images_by_ordered_id(pk1, pk2):
    from neurovault.apps.statmaps.models import Image
    image1 = get_object_or_404(Image, pk=pk1)
    image2 = get_object_or_404(Image, pk=pk2)
    return sorted([image1,image2], key=lambda x: x.pk)
