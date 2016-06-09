
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


def calculate_gene_expression_similarity(reduced_stat_map_data):
    store_file = "/ahba_data/store_max1_reduced.h5"

    results_dfs = []
    with pd.HDFStore(store_file, 'r') as store:
        for donor_id in store.keys():
            print "Loading expression data (%s)" % donor_id
            expression_data = store.get(donor_id.replace(".", "_"))

            print "Getting statmap values (%s)" % donor_id
            nifti_values = reduced_stat_map_data[expression_data.columns]

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
        del results_dfs

    t, p = ttest_1samp(results_df, 0.0, axis=1)
    group_results_df = pd.DataFrame({"t": t, "p": p}, columns=['t', 'p'], index=expression_data.index)
    _, group_results_df["p (FDR corrected)"], _, _ = multipletests(group_results_df.p, method='fdr_bh')
    group_results_df["variance explained (mean)"] = (results_df.xs('slope', axis=1, level=1) ** 2 * 100).mean(axis=1)
    group_results_df["variance explained (std)"] = (results_df.xs('slope', axis=1, level=1) ** 2 * 100).std(axis=1)
    del results_df
    probe_info = pd.read_csv("/ahba_data/probe_info_max1.csv", index_col=0).drop(['chromosome', "gene_id"], axis=1)
    group_results_df = group_results_df.join(probe_info)
    group_results_df = group_results_df[["gene_symbol", "entrez_id.1", "gene_name","t", "p", "p (FDR corrected)",
                                         "variance explained (mean)", "variance explained (std)"]]

    return group_results_df
