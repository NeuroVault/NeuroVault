import urllib, json, tarfile, requests
from StringIO import StringIO
import xml.etree.cElementTree as e

url = "http://anima.modelgui.org/api/studies"
response = urllib.urlopen(url);
datasets = json.loads(response.read())
for url in datasets:
    if "Meta_Insula.tar.gz" in url:
        continue
    print url
    response = requests.get(url)
    results = tarfile.open(mode= "r:gz", fileobj = StringIO(response.content))
    for member in results.getmembers():
        f=results.extractfile(member)
        if member.name.endswith(".study"):
            content=f.read()
            xml_obj = e.fromstring(content)

            study_description = xml_obj.find(".//Element[@name='Description']").text.strip()
            study_name = xml_obj.find(".").attrib['name']
            tags = study_description = xml_obj.find(".//Element[@name='Keywords']").text.strip().split(";")

            print study_name, study_description, "\n"

            for study_element in xml_obj.findall(".//StudyElement[@type='VolumeFile']"):
                image_name = study_element.attrib['name'].strip()
                image_filename = study_element.attrib['file']
                image_fileobject = f = results.extractfile(xml_obj.find(".").attrib['directory'] + "/" + image_filename)
                image_description = study_element.find("./Metadata/Element[@name='Caption']").text.strip()

                print image_name, image_filename, image_description, image_fileobject.size, "\n"

            break
