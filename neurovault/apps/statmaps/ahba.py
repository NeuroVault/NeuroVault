
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

#code from neurosynth
def get_sphere(coords, r, vox_dims, dims):
    """ # Return all points within r mm of coordinates. Generates a cube
    and then discards all points outside sphere. Only returns values that
    fall within the dimensions of the image."""
    r = float(r)
    xx, yy, zz = [slice(-r / vox_dims[i], r / vox_dims[
                        i] + 0.01, 1) for i in range(len(coords))]
    cube = np.vstack([row.ravel() for row in np.mgrid[xx, yy, zz]])
    sphere = cube[:, np.sum(np.dot(np.diag(
        vox_dims), cube) ** 2, 0) ** .5 <= r]
    sphere = np.round(sphere.T + coords)
    return sphere[(np.min(sphere, 1) >= 0) & (np.max(np.subtract(sphere, dims), 1) <= -1),:].astype(int)


def get_values_at_locations(locations, radius, mask, nii, data):
    values = []

        
    for location in locations:
        coord_data = [round(i) for i in nb.affines.apply_affine(npl.inv(nii.get_affine()), location)]
        sph_mask = (np.zeros(mask.shape) == True)
        if radius:
            sph = tuple(get_sphere(coord_data, vox_dims=nii.get_header().get_zooms(),r=radius, dims=nii.shape).T)
            sph_mask[sph] = True
        else:
            #if radius is not set use a single point
            sph_mask[coord_data[0], coord_data[1], coord_data[2]] = True
        
        roi = np.logical_and(mask, sph_mask)
        
        #If the roi is outside of the statmap mask we should treat it as a missing value
        if np.any(roi):
            val = data[roi].mean()
        else:
            val = np.nan
        values.append(val)
    return values


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

    results_dfs = []
    for donor_id in store.keys():
        # print "Loading expression data"
        expression_data = store.get(donor_id)

        # print "Getting statmap values"
        mni_coordinates = list(mni_cordinates_df.ix[expression_data.columns].itertuples(index=False))
        nifti_values = get_values_at_locations(mni_coordinates, 5, mask, nii, data)

        # print "Removing missing values"
        na_mask = np.isnan(nifti_values)
        nifti_values = np.array(nifti_values)[np.logical_not(na_mask)]
        expression_data.drop(expression_data.columns[na_mask], axis=1, inplace=True)

        # print "z scoring"
        expression_data = pd.DataFrame(zscore(expression_data, axis=1), columns=expression_data.columns,
                                       index=expression_data.index)
        nifti_values = zscore(nifti_values)

        # print "Calculating linear regressions"
        # results_df = expression_data.apply(regression, axis=1)
        regression_results = np.linalg.lstsq(np.c_[nifti_values, np.ones_like(nifti_values)], expression_data.T)
        results_df = pd.DataFrame({"slope": regression_results[0][0]}, index=expression_data.index)

        results_df.columns = pd.MultiIndex.from_tuples([(donor_id[1:], c,) for c in results_df.columns],
                                                       names=['donor_id', 'parameter'])

        results_dfs.append(results_df)

    # print "Concatenating results"
    results_df = pd.concat(results_dfs, axis=1)

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

    store.close()

    return group_results_df
