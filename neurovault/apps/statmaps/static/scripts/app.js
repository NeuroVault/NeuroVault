$(document).ready(function() {

	viewer = new Viewer('#layer-list', '.layer-settings', true, { panzoomEnabled: false} )
	viewer.addView('#view-axial', Viewer.AXIAL);
	viewer.addView('#view-coronal', Viewer.CORONAL);
	viewer.addView('#view-sagittal', Viewer.SAGITTAL);
	viewer.addSlider('opacity', '.slider#opacity', 'horizontal', 0, 1, 1, 0.05);
	viewer.addSlider('pos-threshold', '.slider#pos-threshold', 'horizontal', 0, 1, 0, 0.01);
	viewer.addSlider('neg-threshold', '.slider#neg-threshold', 'horizontal', 0, 1, 0, 0.01);
	viewer.addSlider("nav-xaxis", ".slider#nav-xaxis", "horizontal", 0, 1, 0.5, 0.01, Viewer.XAXIS);
	viewer.addSlider("nav-yaxis", ".slider#nav-yaxis", "vertical", 0, 1, 0.5, 0.01, Viewer.YAXIS);
	viewer.addSlider("nav-zaxis", ".slider#nav-zaxis", "vertical", 0, 1, 0.5, 0.01, Viewer.ZAXIS);

	viewer.addColorSelect('#select-color');
	viewer.addSignSelect('#select-sign')
	viewer.addDataField('voxelValue', '#data-current-value')
	viewer.addDataField('currentCoords', '#data-current-coords')
	viewer.addSettingsCheckboxes('#checkbox-list', 'standard')
	// We already have the functional overlay, so add the anatomical...
	images.unshift(
		{
			'url': '/static/anatomical/MNI152.nii.gz.json',
			'name': 'MNI152 2mm',
			'colorPalette': 'grayscale'
		}
	)
	viewer.loadImages(images)
	window.viewer = viewer
});