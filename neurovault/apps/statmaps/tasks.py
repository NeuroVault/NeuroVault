

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
import urllib.request, urllib.parse, urllib.error, json, tarfile, requests, os
from io import StringIO
import xml.etree.cElementTree as e
from django.db import IntegrityError
from django.core.files.uploadedfile import SimpleUploadedFile
import re
from django.conf import settings


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
    response = urllib.request.urlopen(url);
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
        study_description += " This dataset was automatically imported from the ANIMA <http://anima.fz-juelich.de/> database. Version: %s"%version
        study_name = xml_obj.find(".").attrib['name']
        
        tags = xml_obj.find(".//Element[@name='Keywords']").text.strip().split(";")
        tags.append("ANIMA")
        doi = xml_obj.find(".//Element[@name='DOI']")
        pubmedid = xml_obj.find(".//Element[@name='PubMedID']")
    
        post_dict = {
            'name': study_name,
            'description': study_description,
            'full_dataset_url': "http://anima.fz-juelich.de/studies/" + os.path.split(url)[1].replace(".study", "")
        }
        if doi != None:
            post_dict['DOI'] = doi.text.strip()
        elif pubmedid != None:
            pubmedid = pubmedid.text.strip()
            url = "http://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids=%s&format=json" % pubmedid
            response = urllib.request.urlopen(url);
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
                    if quantity in list(quantity_dict.keys()):
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


@shared_task
def process_map(image_pk):
    generate_glassbrain_image(image_pk)
    generate_surface_image(image_pk)

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

# SURFACE IMAGE GENERATION ###########################################################################

@shared_task
def generate_surface_image(image_pk):
    from neurovault.apps.statmaps.models import Image
    from scipy.io import loadmat
    from scipy.interpolate import interpn

    img = Image.objects.get(pk=image_pk)
    if img.target_template_image in ['GenericMNI', 'MNI152NLin2009cAsym'] and \
            img.data_origin == 'volume':
        img_vol = nib.load(img.file.path)
        data_vol = img_vol.get_data()
        if data_vol.ndim > 3:
            data_vol = data_vol[:, :, :, 0]  #number of time points
        this_path = os.path.abspath(os.path.dirname(__file__))

        for hemi in ['lh', 'rh']:
            ras_coor = loadmat(os.path.abspath(os.path.join(this_path, "static", "anatomical",
                                                                "%s.avgMapping_allSub_RF_ANTs_MNI2fs.mat" % hemi)))['ras']

            vox_coor = nib.affines.apply_affine(numpy.linalg.inv(img_vol.affine), ras_coor.T).T
            img_surf = nib.gifti.GiftiImage()

            if img.polymorphic_ctype.model == 'atlas' or (hasattr(img, 'map_type') and img.map_type in ['Pa', 'R']):
                method = 'nearest'
            else:
                method = 'linear'

            data_surf = interpn(points=[list(range(data_vol.shape[0])), list(range(data_vol.shape[1])), list(range(data_vol.shape[2]))],
                                values=data_vol,
                                xi=vox_coor.T,
                                method=method,
                                bounds_error=False,
                                fill_value=0)
            # without turning nan's to zeros Connectome Workbench behaves weird
            data_surf[numpy.isnan(data_surf)] = 0

            # ASCII is the only encoding that produces outputs compatible with Connectome Workbench
            data_surf_gifti = nib.gifti.GiftiDataArray(data_surf, 'NIFTI_INTENT_NONE',
                                                       'NIFTI_TYPE_FLOAT32', 'ASCII')
            img_surf.add_gifti_data_array(data_surf_gifti)
            img_surf.meta.data.insert(0, nib.gifti.GiftiNVPairs('AnatomicalStructurePrimary',
                                                                {'lh': 'CortexLeft',
                                                                 'rh': 'CortexRight'}[hemi]))

            f = BytesIO()
            fmap = {'image': nib.FileHolder(fileobj=f), 'header': nib.FileHolder(fileobj=f)}
            img_surf.to_file_map(fmap)
            f.seek(0)
            content_file = ContentFile(f.read())
            if hemi == 'lh':
                img.surface_left_file.save("%s.%s.func.gii" % (img.pk, {'lh': 'L', 'rh': 'R'}[hemi]), content_file)
            else:
                img.surface_right_file.save("%s.%s.func.gii" % (img.pk, {'lh': 'L', 'rh': 'R'}[hemi]), content_file)
        img.save()
        print("Surface image generation done.")


# IMAGE TRANSFORMATION ################################################################################

# Save 4mm, brain masked image vector in pkl file in image folder
@shared_task
def save_resampled_transformation_single(pk1, resample_dim=[4, 4, 4]):
    from neurovault.apps.statmaps.models import Image
    from six import BytesIO
    import numpy as np

    img = get_object_or_404(Image, pk=pk1)
    nii_obj = nib.load(img.file.path)   # standard_mask=True is default
    image_vector = make_resampled_transformation_vector(nii_obj,resample_dim)

    f = BytesIO()
    np.save(f, image_vector)
    f.seek(0)
    content_file = ContentFile(f.read())
    img.reduced_representation.save("transform_%smm_%s.npy" %(resample_dim[0],img.pk), content_file)

    return img


# SIMILARITY CALCULATION ##############################################################################

@shared_task
def run_voxelwise_pearson_similarity(pk1):
    from neurovault.apps.statmaps.models import Image
    from neurovault.apps.statmaps.utils import get_images_to_compare_with

    imgs_pks = get_images_to_compare_with(pk1, for_generation=True)
    if imgs_pks:
        image = Image.objects.get(pk=pk1)
        # added for improved performance
        if not image.reduced_representation or not os.path.exists(image.reduced_representation.path):
            image = save_resampled_transformation_single(pk1)

        # exclude single subject maps from analysis
        for pk in imgs_pks:
            save_voxelwise_pearson_similarity.apply_async([pk, pk1])  # Default uses reduced_representaion, reduced_representation = True

@shared_task
def save_voxelwise_pearson_similarity(pk1,pk2,resample_dim=[4,4,4],reduced_representaion=True):
    if reduced_representaion == False:
        save_voxelwise_pearson_similarity_resample(pk1,pk2,resample_dim)
    else:
        save_voxelwise_pearson_similarity_reduced_representation(pk1,pk2)


# Calculate pearson correlation from pickle files with brain masked vectors of image values
def save_voxelwise_pearson_similarity_reduced_representation(pk1, pk2):
    from neurovault.apps.statmaps.models import Similarity, Comparison
    import numpy as np
    # We will always calculate Comparison 1 vs 2, never 2 vs 1
    if pk1 != pk2:
        try:
            sorted_images = get_images_by_ordered_id(pk1, pk2)
        except Http404:
            # files have been deleted in the meantime
            return
        image1 = sorted_images[0]
        image2 = sorted_images[1]
        pearson_metric = Similarity.objects.get(similarity_metric="pearson product-moment correlation coefficient",
                                                transformation="voxelwise")
    
        # Make sure we have a transforms for pks in question
        if not image1.reduced_representation or not os.path.exists(image1.reduced_representation.path):
            image1 = save_resampled_transformation_single(pk1) # cannot run this async

        if not image2.reduced_representation or not os.path.exists(image1.reduced_representation.path):
            image2 = save_resampled_transformation_single(pk2) # cannot run this async

        # Load image pickles
        image_vector1 = np.load(image1.reduced_representation.file)
        image_vector2 = np.load(image2.reduced_representation.file)

        # Calculate binary deletion vector mask (find 0s and nans)
        mask = make_binary_deletion_vector([image_vector1,image_vector2])

        # Calculate pearson
        pearson_score = calculate_pairwise_correlation(image_vector1[mask==1],
                                                       image_vector2[mask==1],
                                                       corr_type="pearson")   

        # Only save comparison if is not nan
        if not numpy.isnan(pearson_score):     
            Comparison.objects.update_or_create(image1=image1, image2=image2,
                                                defaults={'similarity_metric': pearson_metric,
                                                          'similarity_score': pearson_score})
            return image1.pk,image2.pk,pearson_score
        else:
            print("Comparison returned NaN.")
    else:
        raise Exception("You are trying to compare an image with itself!")


def save_voxelwise_pearson_similarity_resample(pk1, pk2,resample_dim=[4,4,4]):
    from neurovault.apps.statmaps.models import Similarity, Comparison
    # We will always calculate Comparison 1 vs 2, never 2 vs 1
    if pk1 != pk2:
        try:
            sorted_images = get_images_by_ordered_id(pk1, pk2)
        except Http404:
            # files have been deleted in the meantime
            return
        image1 = sorted_images[0]
        image2 = sorted_images[1]
        pearson_metric = Similarity.objects.get(
                           similarity_metric="pearson product-moment correlation coefficient",
                           transformation="voxelwise")

        # Get standard space brain
        mr_directory = get_data_directory()
        reference = "%s/MNI152_T1_2mm_brain_mask.nii.gz" %(mr_directory)
        image_paths = [image.file.path for image in [image1, image2]]
        images_resamp, _ = resample_images_ref(images=image_paths, 
                                               reference=reference, 
                                               interpolation="continuous",
                                               resample_dim=resample_dim)
        # resample_images_ref will "squeeze" images, but we should keep error here for now
        for image_nii, image_obj in zip(images_resamp, [image1, image2]):
            if len(numpy.squeeze(image_nii.get_data()).shape) != 3:
                raise Exception("Image %s (id=%d) has incorrect number of dimensions %s"%(image_obj.name, 
                                                                                          image_obj.id, 
                                                                                          str(image_nii.get_data().shape)))

        # Calculate correlation only on voxels that are in both maps (not zero, and not nan)
        image1_res = images_resamp[0]
        image2_res = images_resamp[1]
        binary_mask = make_binary_deletion_mask(images_resamp)
        binary_mask = nib.Nifti1Image(binary_mask,header=image1_res.header,affine=image1_res.affine)

        # Will return nan if comparison is not possible
        pearson_score = calculate_correlation([image1_res,image2_res],mask=binary_mask,corr_type="pearson")

        # Only save comparison if is not nan
        if not numpy.isnan(pearson_score):     
            Comparison.objects.update_or_create(image1=image1, image2=image2,
                                                defaults={'similarity_metric': pearson_metric,
                                                          'similarity_score': pearson_score})

            return image1.pk,image2.pk,pearson_score
        else:
            raise Exception("You are trying to compare an image with itself!")


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
        print("%s of %s" %(t,len(tasks.json))) 
        if tasks.json[t]["name"]:
            task, _ = CognitiveAtlasTask.objects.update_or_create(cog_atlas_id=task["id"],defaults={"name":task["name"]})
            task.save()
            if tasks.json[t]["id"]:
                task_details = get_task(id=tasks.json[t]["id"])
                if task_details.json["contrasts"]:
                    print("Found %s contrasts!" %(len(task_details.json["contrasts"])))
                    for contrast in task_details.json["contrasts"]:
                        contrast, _ = CognitiveAtlasContrast.objects.update_or_create(cog_atlas_id=contrast["id"], 
                                                                                      defaults={"name":contrast["name"],
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
