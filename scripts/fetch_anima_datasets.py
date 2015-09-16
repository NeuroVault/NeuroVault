import urllib, json, tarfile, requests, os
from StringIO import StringIO
import xml.etree.cElementTree as e
from django.db import IntegrityError
from neurovault.apps.statmaps.models import Collection, User, BaseStatisticMap,\
    StatisticMap
from django.core.files.uploadedfile import SimpleUploadedFile
from neurovault.apps.statmaps.forms import StatisticMapForm, CollectionForm
import re

username = "ANIMA"
email = "a.reid@fz-juelich.de"
try:
    anima_user = User.objects.create_user(username, email)
    anima_user.save()
except IntegrityError:
    anima_user = User.objects.get(username=username, email=email)

url = "http://anima.modelgui.org/api/studies"
response = urllib.urlopen(url);
datasets = json.loads(response.read())

# results = tarfile.open(mode="r:gz", fileobj=StringIO(response.content))
#     for member in results.getmembers():
#         f = results.extractfile(member)
#         if member.name.endswith(".study"):
            
for url in datasets:
    print url
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

    print study_name, study_description, "\n"

    post_dict = {
        'name': study_name,
        'description': study_description,
        'full_dataset_url': "http://anima.modelgui.org/studies/" + os.path.split(url)[1].replace(".study", "")
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
        col = Collection.objects.get(DOI=post_dict['DOI'])
    except Collection.DoesNotExist:
        col = None
    
    if col and not col.description.endswith(version):
        col.DOI = None
        old_version = re.search(r"Version: (?P<version>\w)", col.description).group("version")
        col.name = study_name + " (version %s - deprecated)"%old_version
        col.save()
    
    if not col or not col.description.endswith(version):
        collection = Collection(owner=anima_user)
        form = CollectionForm(post_dict, instance=collection)
        form.is_valid()
        print form.errors
        collection = form.save()
        
        arch_response = requests.get(url.replace("library", "library/archives").replace(".study", ".tar.gz"))
        arch_results = tarfile.open(mode="r:gz", fileobj=StringIO(arch_response.content))
    
        for study_element in xml_obj.findall(".//StudyElement[@type='VolumeFile']"):
            image_name = study_element.attrib['name'].strip()
            image_filename = study_element.attrib['file']
            image_fileobject = arch_results.extractfile(xml_obj.find(".").attrib['directory'] + "/" + image_filename)
            
    
            print image_name, image_filename, image_fileobject.size, "\n"
    
            map_type = BaseStatisticMap.OTHER
    
            quantity_dict = {"Mask": BaseStatisticMap.M,
                             "F-statistic": BaseStatisticMap.F,
                             "T-statistic": BaseStatisticMap.T,
                             "Z-statistic": BaseStatisticMap.Z,
                             "Beta": BaseStatisticMap.U}
    
            quantity = study_element.find("./Metadata/Element[@name='Quantity']")
            if quantity != None:
                quantity = quantity.text.strip()
                print quantity
                if quantity in quantity_dict.keys():
                    map_type = quantity_dict[quantity]
    
            post_dict = {
                'name': image_name,
                'modality': StatisticMap.fMRI_BOLD,
                'map_type': map_type,
                'analysis_level': BaseStatisticMap.M,
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
            print post_dict
            print form.errors.keys()
            print form.errors
            form.save()
