from django.core.management.base import BaseCommand, CommandError
from neurovault.apps.statmaps.tests.utils import clearDB
from neurovault.apps.statmaps.models import Comparison, Similarity, User, Collection, Image
from neurovault.apps.statmaps.utils import get_existing_comparisons
from neurovault.apps.statmaps.tests.utils import  save_statmap_form
from neurovault.apps.statmaps.tasks import save_resampled_transformation_single

import os
import gc
import timeit
import numpy as np

class Command(BaseCommand):
	args = '<times_to_run>'
	help = 'bench'
	clearDB()
	app_path = '/code/neurovault/apps/statmaps/tests'
	u1 = User.objects.create(username='neurovault3')
	i = 1
	subjects = 4
	X = np.empty([28549,subjects])

	for file in os.listdir(os.path.join(app_path, 'bench/unthres/')):
		randomCollection = Collection(name='random' + file, owner=u1, DOI='10.3389/fninf.2015.00008' + str(i))
		randomCollection.save()

		image = save_statmap_form(image_path=os.path.join(app_path, 'bench/unthres/',file),collection=randomCollection,image_name=file,ignore_file_warning=True)
		if not image.reduced_representation or not os.path.exists(image.reduced_representation.path):
			image = save_resampled_transformation_single(image.pk)
		
		X[:,i] = np.load(image.reduced_representation.file)
		i = i+1
		if i == subjects: break

	n_bits = 10
	hash_counts = 5
	metric = "euclidean" 
	name = 'NearPy(n_bits=%d, hash_counts=%d)' % (n_bits, hash_counts)
	#fit
	import nearpy, nearpy.hashes, nearpy.distances

	hashes = []

	# doesn't seem like the NearPy code is using the metric??
	for k in xrange(hash_counts):
		nearpy_rbp = nearpy.hashes.RandomBinaryProjections('rbp_%d' % k, n_bits)
		hashes.append(nearpy_rbp)

	nearpy_engine = nearpy.Engine(X.shape[1], lshashes=hashes)

	for i, x in enumerate(X):
		nearpy_engine.store_vector(x.tolist(), i)

	def query(self, v, n):
		return [y for x, y, z in self._nearpy_engine.neighbours(v)]





