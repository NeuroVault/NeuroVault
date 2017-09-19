import numpy as np
import pandas as pd

def image_to_words(target, act_probs, term_probs, prior=None, limit=None):
    '''
    Args:
        target (ndarray): The image to decode. A 1-d numpy array.
        act_probs (list of ndarrays): A list of 1-d arrays of topic/component maps.
            Voxel values represent the probability of activation conditional on the topic.
        term_probs (list of dicts): A list of dictionaries, one per topic/component. Each dict
            has terms in keys, probabilities in values.
        prior (ndarray): A specification of the topic/component priors. If None, uniform priors
            will be assumed--i.e., each topic will have probability 1/n_topics. If an ndarray
            is passed it must be a 1-d array with length equal to the number of topics in the
            act_probs and term_probs arrays. Prior should ideally be proper (i.e., all values
            in range [0, 1] and sum to 1), though this will not be enforced.
        limit (int): Max number of terms to return (sorted in descending order).
    '''
  
    # Validations
    if len(term_probs) != len(act_probs):
        raise ValueError("Incorrect dimensions: number of elements in act_probs and term_probs must match.")
    if target.shape != act_probs[0].shape:
        raise ValueError("Incorrect shape: target image and component images must have the same number of voxels.")

    # Convert inputs to 2-d format
    act_probs = list(map(lambda x: x[:, np.newaxis] if x.ndim == 1 else x, act_probs))
    act_probs = np.concatenate(act_probs, axis=1)
    term_probs = pd.DataFrame.from_dict(term_probs, dtype="float").T

    # Replace NaNs in act_probs, and remove any voxels missing in the target.
    # We might also want to track and return the number of valid voxels used.
    act_probs = np.nan_to_num(act_probs)
    nan_rows = np.isnan(target)
    if nan_rows.any():
        act_probs = act_probs[~nan_rows]
        target = target[~nan_rows]

    # Get the base topic weights--this is just the
    # input image multiplied by the P(A|T) images
    topic_weights = target.dot(act_probs)
    n_topics = act_probs.shape[1]
    
    # Apply uniform prior if none is passed
    if prior is None:
        prior = np.ones(n_topics) / n_topics
    topic_weights *= prior

    # Multiply topic weights by P(W|T) to get results, and return
    # as a pandas Series.
    print np.isnan(term_probs.T.values).any()
    print np.isnan(term_probs.T.values).sum()
    for i in range(12):
        print term_probs.T.values[i,:]
    results_dot = topic_weights.dot(term_probs.T.values)
    results_series = pd.Series(results_dot, index=term_probs.index)
    if limit is not None:
        results_series = results_series.sort_values(ascending=False)[:limit]
    return results_series
