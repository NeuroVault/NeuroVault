
# coding: utf-8

# In[33]:

from glob import glob
import os
import pandas as pd
import numpy as np
import nibabel as nb
import numpy.linalg as npl
from scipy.stats.stats import pearsonr, ttest_1samp, percentileofscore, linregress, zscore
from statsmodels.sandbox.stats.multicomp import multipletests


def calculate_gene_expression_similarity(stat_map):
    mni_locations_file = "/ahba_data/corrected_mni_coordinates.csv"
    store_file = "/ahba_data/store.h5"

    store = pd.HDFStore(store_file, 'r')
    mni_cordinates_df = pd.read_csv(mni_locations_file, header=0, index_col=0)

    nii = nb.load(stat_map)
    data = nii.get_data()
    mask = np.logical_and(np.logical_not(np.isnan(data)), data != 0)

    def regression(row):
        outputs = linregress(row, nifti_values)
        return pd.Series({'slope': outputs[0],
                          'intercept': outputs[1],
                          'rvalue': outputs[2],
                          'pvalue': outputs[3],
                          'stderr': outputs[4]})

    all_results = []

    with pd.HDFStore(os.path.join(download_dir, 'store_max1_reduced.h5'), 'r') as store:
        stat_map = os.path.join(test_data_root_dir, gene_validator["map"])
        genes = gene_validator["correct"]

        nii = nb.load(stat_map)
        statmap_data = make_resampled_transformation_vector(nii, [4, 4, 4])

        results_dfs = []

        for donor_id in store.keys():
            print "Loading expression data (%s)" % donor_id
            expression_data = store.get(donor_id.replace(".", "_"))
            expression_data.drop(probe_info_df.index[~probe_info_df.gene_symbol.isin(genes)],
                                 axis=0, inplace=True)

            print "Getting statmap values (%s)" % donor_id
            nifti_values = statmap_data[expression_data.columns]

            print "Removing missing values (%s)" % donor_id
            na_mask = np.isnan(nifti_values)
            nifti_values = np.array(nifti_values)[np.logical_not(na_mask)]
            expression_data.drop(expression_data.columns[na_mask], axis=1, inplace=True)

            print "z scoring (%s)" % donor_id
            expression_data = pd.DataFrame(zscore(expression_data, axis=1), columns=expression_data.columns,
                                           index=expression_data.index)
            nifti_values = zscore(nifti_values)

            print "Calculating linear regressions (%s)" % donor_id
            regression_results = np.linalg.lstsq(np.c_[nifti_values, np.ones_like(nifti_values)], expression_data.T)
            results_df = pd.DataFrame({"slope": regression_results[0][0]}, index=expression_data.index)

            results_df.columns = pd.MultiIndex.from_tuples([(donor_id[1:], c,) for c in results_df.columns],
                                                           names=['donor_id', 'parameter'])

            results_dfs.append(results_df)

        print "Concatenating results"
        results_df = pd.concat(results_dfs, axis=1)

    # group_results_df = results_df.xs('slope', axis=1, level=1).apply(onesample, axis=1)
    # group_results_df["variance explained (mean)"] = (results_df.xs('slope', axis=1, level=1) ** 2 * 100).mean(axis=1)
    # group_results_df["correlation (mean)"] = (results_df.xs('slope', axis=1, level=1)).mean(axis=1)
    # group_results_df["correlation (variance)"] = (results_df.xs('slope', axis=1, level=1)).var(axis=1)
    group_results_df = results_df.join(probe_info_df)

    # In[119]:

    def onesample(row):
        t, p = ttest_1samp(row, 0.0)
        return pd.Series({'t': t,
                          'p': p})

    group_results_df = results_df.xs('slope', axis=1, level=1).apply(onesample, axis=1)
    _, group_results_df["p (FDR corrected)"], _, _ = multipletests(group_results_df.p, method='fdr_bh')
    group_results_df["variance explained (mean)"] = (results_df.xs('slope', axis=1, level=1) ** 2 * 100).mean(axis=1)
    group_results_df["correlation (mean)"] = (results_df.xs('slope', axis=1, level=1)).mean(axis=1)
    group_results_df["correlation (variance)"] = (results_df.xs('slope', axis=1, level=1)).var(axis=1)
    group_results_df = group_results_df.join(pd.read_csv("/ahba_data/probe_info.csv", index_col=0))
    group_results_df.sort_values(by=["p"], ascending=True, inplace=True)

    return group_results_df
