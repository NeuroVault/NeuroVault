import urllib, json, tarfile, requests, os
from StringIO import StringIO
import xml.etree.cElementTree as e
from django.db import IntegrityError
from neurovault.apps.statmaps.models import Collection, User, BaseStatisticMap,\
    StatisticMap
from django.core.files.uploadedfile import SimpleUploadedFile
from neurovault.apps.statmaps.forms import StatisticMapForm, CollectionForm

username = "ANIMA"
email = "a.reid@fz-juelich.de"
try:
    anima_user = User.objects.create_user(username, email)
    anima_user.save()
except IntegrityError:
    anima_user = User.objects.get(username=username, email=email)

Collection.objects.filter(owner=anima_user).delete()

url = "http://anima.modelgui.org/api/archives"
response = urllib.urlopen(url);
datasets = json.loads(response.read())
for url in datasets:
    print url
    response = requests.get(url)
    results = tarfile.open(mode="r:gz", fileobj=StringIO(response.content))
    for member in results.getmembers():
        f = results.extractfile(member)
        if member.name.endswith(".study"):
            content = f.read().replace("PubMed ID", "PubMedID")
            xml_obj = e.fromstring(content)

            study_description = xml_obj.find(".//Element[@name='Description']").text.strip()
            study_description += " This dataset was automatically imported from the ANIMA <http://anima.modelgui.org/> database."
            study_name = xml_obj.find(".").attrib['name']
            tags = xml_obj.find(".//Element[@name='Keywords']").text.strip().split(";")
            tags.append("ANIMA")
            doi = xml_obj.find(".//Element[@name='DOI']")
            pubmedid = xml_obj.find(".//Element[@name='PubMedID']")

            print study_name, study_description, "\n"

            post_dict = {
                'name': study_name,
                'description': study_description,
                'full_dataset_url': "http://anima.modelgui.org/studies/" + os.path.split(url)[1].replace(".tar.gz", "")
            }
            if doi != None:
                post_dict['DOI'] = doi.text.strip()
            elif pubmedid != None:
                pubmedid = pubmedid.text.strip()
                url = "http://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids=%s&format=json" % pubmedid
                response = urllib.urlopen(url);
                parsed = json.loads(response.read())
                if 'doi' in parsed['records'][0]:
                    post_dict['DOI'] = parsed['records'][0]['doi']

            collection = Collection(owner=anima_user)
            form = CollectionForm(post_dict, instance=collection)
            form.is_valid()
            print form.errors
            collection = form.save()

            for study_element in xml_obj.findall(".//StudyElement[@type='VolumeFile']"):
                image_name = study_element.attrib['name'].strip()
                image_filename = study_element.attrib['file']
                image_fileobject = results.extractfile(xml_obj.find(".").attrib['directory'] + "/" + image_filename)
                image_description = study_element.find("./Metadata/Element[@name='Caption']").text.strip()

                print image_name, image_filename, image_description, image_fileobject.size, "\n"

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
                    'description': image_description,
                    'modality': StatisticMap.fMRI_BOLD,
                    'map_type': map_type,
                    'analysis_level': BaseStatisticMap.M,
                    'collection': collection.pk,
                    'ignore_file_warning': True,
                    'cognitive_paradigm_cogatlas': 'None',
                    'tags': ", ".join(tags)
                }
                file_dict = {'file': SimpleUploadedFile(image_filename, image_fileobject.read())}
                form = StatisticMapForm(post_dict, file_dict)
                form.is_valid()
                print post_dict
                print form.errors.keys()
                print form.errors
                form.save()

            break
