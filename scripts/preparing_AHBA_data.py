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

donors = ["H0351.2001", "H0351.2002", "H0351.1009", "H0351.1012", "H0351.1015", "H0351.1016"]

# Dropping probes without entrez_id
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
            sample_annot_df = pd.read_csv(f, index_col=0)
        df.columns = pd.MultiIndex.from_tuples([(donor_id, c,) for c in list(sample_annot_df["well_id"])],
                                               names=['donor_id', 'well_id'])
        dfs.append(df)

all_dfs = pd.concat(dfs, copy=False, axis=1)
del dfs

# adding multiindex with gene grouping
multiindex = []
for index in all_dfs.index:
    entrez_id = int(probe_info_df.loc[index]["entrez_id"])
    multiindex.append((entrez_id, index,))

all_dfs.index = pd.MultiIndex.from_tuples(multiindex, names=['entrez_id', 'probe_id'])

# Aggregation of probes within genes. For each gene a probe with max mean expression across all donors/wells is selected.
means = all_dfs.mean(axis=1)
idx_maxs = means.groupby(level=0).idxmax()
all_dfs = all_dfs.reindex(idx_maxs)

# cleaning up the probe information file
probe_info_df.drop(probe_info_df.index[probe_info_df['entrez_id'].isnull()], inplace=True)
multiindex = []
for index in probe_info_df.index:
    entrez_id = int(probe_info_df.loc[index]["entrez_id"])
    multiindex.append((entrez_id, index,))


probe_info_df.index = pd.MultiIndex.from_tuples(multiindex, names=['entrez_id', 'probe_id'])
probe_info_df = probe_info_df.reindex(idx_maxs)
probe_info_df.index = probe_info_df.index.droplevel()
probe_info_df.to_csv(os.path.join(download_dir, 'probe_info.csv'))

# saving the reduced expression data to HDF5 file for efficient readout and querying
with pd.HDFStore(os.path.join(download_dir, 'store.h5')) as store:
    all_dfs.index = all_dfs.index.droplevel(1)
    for donor_id in donors:
        store.append(donor_id, all_dfs[donor_id])

# Removing downloaded files
for i, url in enumerate(urls):
    shutil.rmtree(os.path.join(download_dir, "donor%d.zip" % (i + 1)))
