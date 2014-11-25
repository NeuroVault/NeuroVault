
import nibabel
import xml.etree.ElementTree as ET
import numpy
import os.path
from __builtin__ import True
import urllib2
import networkx as nx
import cPickle as pickle





def getAtlasVoxels(region, atlas_file, atlas_dir):
	tree = ET.parse(os.path.join(atlas_dir, atlas_file))
	root = tree.getroot()
	summaryimagelist = []
	summaryimagefile = ''
	root_header = root.find('header')
	for images in root_header.findall('images'):
		if '2mm' in images.find('summaryimagefile').text:
			summaryimagefile = images.find('summaryimagefile').text
			
	atlas_name = os.path.basename(summaryimagefile) + '.nii.gz'
	atlas=nibabel.load(os.path.join(atlas_dir, atlas_name))
	atlas_data=atlas.get_data()
	name_value = 0
	data = root.find
	
	for i in range(len(root[1])):
		name = root[1][i].text.replace("'",'').rstrip(' ').lower()
		if name == region.lower():
			name_value = i+1
			voxels = numpy.where(atlas_data==name_value)
			return voxels
	raise ValueError('"{region}" not in "{atlas_file}"'.format(region=region, atlas_file=atlas_file))

def voxelToRegion(X,Y,Z,atlas_file, atlas_dir):
	tree = ET.parse(os.path.join(atlas_dir, atlas_file))
	root = tree.getroot()
	summaryimagelist = []
	summaryimagefile = ''
	root_header = root.find('header')
	for images in root_header.findall('images'):
		if '2mm' in images.find('summaryimagefile').text:
			summaryimagefile = images.find('summaryimagefile').text
			
	atlas_name = os.path.basename(summaryimagefile) + '.nii.gz'
	atlas=nibabel.load(os.path.join(atlas_dir, atlas_name))
	atlas_data=atlas.get_data()
	atlasRegions = [x.text.lower() for x in root[1]]
	index = atlas_data[X,Y,Z] - 1
	print index
	if index == -1:
		return 'none'
	else:
		return atlasRegions[index]
	
def getSynonyms(keyword):
	keywordQuery = keyword
	keywordQuery = keywordQuery.replace(' ', '%20')
	keywordQuery = keywordQuery.replace('/', '')
	keywordQuery = keywordQuery.replace('\\', '')
	hdr = {'Accept': 'ext/html,application/xhtml+xml,application/xml,*/*'}
	target_url = 'http://nif-services.neuinfo.org/servicesv1/v1/literature/search?q=' + keywordQuery
	request = urllib2.Request(target_url,headers=hdr)
	synFile = urllib2.urlopen(request)
	tree = ET.parse(synFile)
	root = tree.getroot()
	syn_list_loc = root.findall('query/clauses/clauses/expansion/expansion')
	syn_list = []
	for syn in syn_list_loc:
		syn_list.append(syn.text)
	syn_list.append(keyword)
	return syn_list

def findNodes(graph, startNode, atlasRegions, synonymsDict, direction = 'children'):
	matches = [key for key in synonymsDict.keys() if graph.node[startNode]['name'] in synonymsDict[key]]
	if matches != []:
		return matches
	else:
		matchingRelatives = []
		if direction == 'parents':
			for child in graph.predecessors_iter(startNode):
				matchingRelatives += findNodes(graph, child, atlasRegions, synonymsDict, direction)
		else:
			for child in graph.successors_iter(startNode):
				matchingRelatives += findNodes(graph, child, atlasRegions, synonymsDict, direction)
		return matchingRelatives


def toAtlas(region, graph, atlasRegions, synonymsDict):
	final_list = []
	# checking if region or synonyms exist in atlas. if so, simply return region
	for atlasRegion in atlasRegions:
		if region in synonymsDict[atlasRegion]:
			final_list.append(atlasRegion)
	if final_list != []: 
		return final_list

	# checking recursively for child matches. if it finds any, return them
	try:
		region_id = [n for n,d in graph.nodes_iter(data=True) if d['name'] == region][0]
	except IndexError:
		raise ValueError('"{region}" not in graph'.format(region=region))
	matchingChildren = findNodes(graph, region_id, atlasRegions, synonymsDict, 'children')
	if len(matchingChildren) > 0:
		return matchingChildren

	# checking recursively for parent matches. if it finds any, return them
	else:
		matchingParents = findNodes(graph, region_id, atlasRegions, synonymsDict, 'parents')
		if len(matchingParents) > 0:
			return matchingParents

	# otherwise, return 'none'
	return 'none'

