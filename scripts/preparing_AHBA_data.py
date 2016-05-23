import urllib
import os
import shutil
import pandas as pd
import zipfile
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

# Dowloading MNI coordinates
urllib.urlretrieve(
    "https://raw.githubusercontent.com/chrisfilo/alleninf/master/alleninf/data/corrected_mni_coordinates.csv",
    os.path.join(download_dir, "corrected_mni_coordinates.csv"))

#Downloading gene selections list
urllib.urlretrieve(
    "http://science.sciencemag.org/highwire/filestream/631209/field_highwire_adjunct_files/2/Richiardi_Data_File_S2.xlsx",
    os.path.join(download_dir, "Richiardi_Data_File_S2.xlsx"))

donors = ["H0351.2001", "H0351.2002", "H0351.1009", "H0351.1012", "H0351.1015", "H0351.1016"]

# Dropping probes without entrez_id
with zipfile.ZipFile(os.path.join(download_dir, "donor1.zip")) as z:
    with z.open("Probes.csv") as f:
        probe_info_df = pd.read_csv(f)
richardi_df = pd.read_excel(os.path.join(download_dir, "Richiardi_Data_File_S2.xlsx"))
richardi_df.rename(columns={'Entrez_id': 'entrez_id'}, inplace=True)
probe_info_df = pd.merge(probe_info_df, richardi_df, left_on="probe_name", right_on="probe_id",
                         suffixes=("_original", "_richardi"), how="outer")

# concatenating data from all donors
dfs = []
for i, donor_id in enumerate(donors):
    with zipfile.ZipFile(os.path.join(download_dir, "donor%d.zip" % (i + 1))) as z:
        with z.open("MicroarrayExpression.csv") as f:
            df = pd.read_csv(f, header=None, index_col=0)

        # Dropping probes without entrez_id
        df.drop(probe_info_df['probe_id_original'][probe_info_df['entrez_id_richardi'].isnull()], inplace=True)

        with z.open("SampleAnnot.csv") as f:
            sample_annot_df = pd.read_csv(f, index_col=0)
        df.columns = pd.MultiIndex.from_tuples([(donor_id, c,) for c in list(sample_annot_df["well_id"])],
                                               names=['donor_id', 'well_id'])
        dfs.append(df)

all_dfs = pd.concat(dfs, copy=False, axis=1)
del dfs

# cleaning up the probe information file
probe_info_df.drop(probe_info_df.index[probe_info_df['entrez_id_richardi'].isnull()], inplace=True)
probe_info_df.to_csv(os.path.join(download_dir, 'probe_info.csv'), index=False)

assert(all_dfs.index[0] in list(probe_info_df.probe_id_original))

# saving the reduced expression data to HDF5 file for efficient readout and querying
with pd.HDFStore(os.path.join(download_dir, 'store.h5')) as store:
    for donor_id in donors:
        store.append(donor_id, all_dfs[donor_id])

# Removing downloaded files
for i, url in enumerate(urls):
    os.remove(os.path.join(download_dir, "donor%d.zip" % (i + 1)))
