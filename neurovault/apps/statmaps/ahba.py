
# coding: utf-8

# In[33]:

from glob import glob
import os
import pandas as pd
import numpy as np
import nibabel as nb
import numpy.linalg as npl
from scipy.stats.stats import pearsonr, ttest_1samp, percentileofscore, linregress

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


# In[26]:

def get_values_at_locations(nifti_file, locations, radius, mask, nii, data):
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


# In[32]:

def approximate_random_effects(data, labels, group):

    correlation_per_donor = {}
    for donor_id in set(data[group]):
        correlation_per_donor[donor_id], _, _, _, _ = linregress(list(data[labels[0]][data[group] == donor_id]),
                                                       list(data[labels[1]][data[group] == donor_id]))
    average_slope = np.array(correlation_per_donor.values()).mean()
    t, p_val = ttest_1samp(correlation_per_donor.values(), 0)
    print "Averaged slope across donors = %g (t=%g, p=%g)"%(average_slope, t, p_val)
    sns.violinplot([correlation_per_donor.values()], inner="points", names=["donors"])
    plt.ylabel("Linear regression slopes between %s and %s"%(labels[0],labels[1]))
    plt.axhline(0, color="red")
    
    sns.lmplot(labels[0], labels[1], data, hue=group, col=group, col_wrap=3)
    plt.show()
    
    return average_slope, t, p_val


# In[118]:

mni_locations_file = "D:\\ahba_downloads\corrected_mni_coordinates.csv"
store_file = "D:\\ahba_downloads\store.h5"
#stat_map = "C:\\Users\\filo\\workspace\\NeuroVault\\neurovault\\apps\\statmaps\\tests\\test_data\\statmaps\\all.nii.gz"
stat_map = "D:\\WAY_HC36_mean.nii.gz"

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
    print "Loading expression data"
    expression_data = store.get(donor_id)
    
    print "Getting statmap values"
    mni_coordinates = list(mni_cordinates_df.ix[expression_data.columns].itertuples(index=False))
    nifti_values = get_values_at_locations(
        stat_map, mni_coordinates, 4, mask, nii, data)
    
    print "Removing missing values"
    na_mask = np.isnan(nifti_values)
    nifti_values = np.array(nifti_values)[np.logical_not(na_mask)]
    expression_data.drop(expression_data.columns[na_mask], axis=1, inplace=True)
    
    print "Calculating linear regressions"
    results_df = expression_data.apply(regression, axis=1)
    
    results_df.columns = pd.MultiIndex.from_tuples([(donor_id[1:], c,) for c in results_df.columns],
                                               names=['donor_id', 'parameter'])
    
    results_dfs.append(results_df)
    
print "Concatenating results"
results_df = pd.concat(results_dfs, axis=1)


# In[119]:

def onesample(row):
    t, p = ttest_1samp(row, 0.0)
    return pd.Series({'t': t,
                      'p': p})
group_results_df = results_df.xs('slope', axis=1, level=1).apply(onesample, axis=1)
_, group_results_df["p (FDR corrected)"], _, _ = multipletests(group_results_df.p, method='fdr_bh')
group_results_df["variance explained (mean)"] = (results_df.xs('rvalue', axis=1, level=1)**2*100).mean(axis=1)
group_results_df.join(pd.read_csv("D:\\ahba_downloads\\probe_info.csv", index_col=0))
group_results_df = group_results_df.join(pd.read_csv("D:\\ahba_downloads\\probe_info.csv", index_col=1))
group_results_df.sort_values(by=["p"], ascending=True)


# In[123]:

for gene_name in list(group_results_df.gene_symbol_richardi):
    if "HTR1" in gene_name:
        print gene_name


# In[125]:

group_results_df[group_results_df.gene_symbol_richardi == "HTR1A"]


# In[80]:

multipletests(group_results_df.p, method='fdr_bh')


# In[90]:




# In[105]:

group_results_df.join(pd.read_csv("D:\\ahba_downloads\\probe_info.csv", index_col=1))


# In[ ]:



