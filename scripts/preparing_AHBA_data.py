import urllib
import zipfile
import os
import numpy as np
import nibabel as nb
import numpy.linalg as npl
import pandas as pd
from pybraincompare.mr.datasets import get_standard_mask

# Downloading microarray data
urls = ["http://human.brain-map.org/api/v2/well_known_file_download/178238387",
        "http://human.brain-map.org/api/v2/well_known_file_download/178238373",
        "http://human.brain-map.org/api/v2/well_known_file_download/178238359",
        "http://human.brain-map.org/api/v2/well_known_file_download/178238316",
        "http://human.brain-map.org/api/v2/well_known_file_download/178238266",
        "http://human.brain-map.org/api/v2/well_known_file_download/178236545"]

donor_ids = [""]
download_dir = "/ahba_data"
os.makedirs(download_dir)

for i, url in enumerate(urls):
    print "Downloading %s" % url
    urllib.urlretrieve(url, os.path.join(download_dir, "donor%d.zip" % (i + 1)))
    zipfile.ZipFile(os.path.join(download_dir, "donor%d.zip" % (i + 1)))

# Dowloading MNI coordinates
urllib.urlretrieve(
    "https://raw.githubusercontent.com/chrisfilo/alleninf/master/alleninf/data/corrected_mni_coordinates.csv",
    os.path.join(download_dir, "corrected_mni_coordinates.csv"))

samples = pd.read_csv(os.path.join(download_dir, "corrected_mni_coordinates.csv"), index_col=0)

mni = get_standard_mask(voxdim=4)

reduced_coord = []

for coord_mni in samples[['corrected_mni_x', 'corrected_mni_y', 'corrected_mni_z']].values:
    sample_counts = np.zeros(mni.shape, dtype=int)
    coord_data = [int(round(i)) for i in nb.affines.apply_affine(npl.inv(mni.get_affine()), coord_mni)]
    sample_counts[coord_data[0],
                  coord_data[1],
                  coord_data[2]] = 1
    out_vector = sample_counts[mni.get_data()!=0]
    idx = out_vector.argmax()
    if idx == (out_vector == 1.0).sum() == 0:
        idx = np.nan
    reduced_coord.append(idx)

samples["reduced_coordinate"] = reduced_coord

#Downloading gene selections list
urllib.urlretrieve(
    "http://science.sciencemag.org/highwire/filestream/631209/field_highwire_adjunct_files/2/Richiardi_Data_File_S2.xlsx",
    os.path.join(download_dir, "Richiardi_Data_File_S2.xlsx"))

donors = ["H0351.2001", "H0351.2002", "H0351.1009", "H0351.1012", "H0351.1015", "H0351.1016"]

with zipfile.ZipFile(os.path.join(download_dir, "donor1.zip")) as z:
    with z.open("Probes.csv") as f:
        probe_info_df = pd.read_csv(f, index_col=0)

# concatenating data from all donors
dfs = []
for i, donor_id in enumerate(donors):
    with zipfile.ZipFile(os.path.join(download_dir, "donor%d.zip" % (i + 1))) as z:
        with z.open("MicroarrayExpression.csv") as f:
            df = pd.read_csv(f, header=None, index_col=0)

        # Dropping probes without entrez_id
        df.drop(probe_info_df.index[probe_info_df['entrez_id'].isnull()], inplace=True)

        with z.open("SampleAnnot.csv") as f:
            sample_annot_df = pd.read_csv(f, index_col="well_id").join(samples, how="inner")

        df.columns = list(sample_annot_df["reduced_coordinate"])
        # removing out side of the brain coordinates
        df.drop(sample_annot_df.index[sample_annot_df.reduced_coordinate.isnull()], axis=1, inplace=True)
        # averaging measurements from similar locations
        df = df.groupby(level=0, axis=1).mean()

        df.columns = pd.MultiIndex.from_tuples([(donor_id, c,) for c in list(df.columns)],
                                               names=['donor_id', 'reduced_coordinate'])
        dfs.append(df)

expression_data = pd.concat(dfs, copy=False, axis=1)
del dfs

probe_info_df.drop(probe_info_df.index[probe_info_df['entrez_id'].isnull()], inplace=True)

multiindex = []
for index in expression_data.index:
    entrez_id = int(probe_info_df.loc[index]["entrez_id"])
    multiindex.append((entrez_id, index,))
expression_data.index = pd.MultiIndex.from_tuples(multiindex, names=['entrez_id', 'probe_id'])

means = expression_data.mean(axis=1)
idx_maxs = means.groupby(level=0).idxmax()
expression_data = expression_data.reindex(idx_maxs)

expression_data.index = expression_data.index.droplevel(1)

multiindex = []
for index in probe_info_df.index:
    entrez_id = int(probe_info_df.loc[index]["entrez_id"])
    multiindex.append((entrez_id, index,))
probe_info_df.index = pd.MultiIndex.from_tuples(multiindex, names=['entrez_id', 'probe_id'])
probe_info_df = probe_info_df.reindex(idx_maxs)
probe_info_df.index = probe_info_df.index.droplevel(1)
probe_info_df.to_csv(os.path.join(download_dir, 'probe_info_max1.csv'))

assert (expression_data.index[0] in list(probe_info_df.index))
assert (expression_data.shape == (20787, 3072))

with pd.HDFStore(os.path.join(download_dir, 'store_max1_reduced.h5'), 'w') as store:
    for donor_id in donors:
        store.append(donor_id.replace(".", "_"), expression_data[donor_id])

# Removing downloaded files
for i, url in enumerate(urls):
    os.remove(os.path.join(download_dir, "donor%d.zip" % (i + 1)))
