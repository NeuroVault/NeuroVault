import django.db.models as models


class ContrastMap(models.Model):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    contrastName = models.CharField(max_length=200)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace)
    wasGeneratedBy = models.ForeignKey(ContrastEstimation)
    sha512 = models.CharField(max_length=200)
    label = models.CharField(max_length=200)


class Data(models.Model):
    label = models.CharField(max_length=200)
    grandMeanScaling = models.BooleanField()
    targetIntensity = models.FloatField()


class Cluster(models.Model):
    qValueFDR = models.FloatField()
    clusterLabelId = models.IntField()
    pValueUncorrected = models.FloatField()
    pValueFWER = models.FloatField()
    wasDerivedFrom = models.ForeignKey(ExcursionSet)
    clusterSizeInVoxels = models.IntField()
    label = models.CharField(max_length=200)
    clusterSizeInResels = models.FloatField()


class DesignMatrix(models.Model):
    visualisation = models.FileField(upload_to=upload_to)
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    label = models.CharField(max_length=200)


class Peak(models.Model):
    atLocation = models.ForeignKey(Coordinate)
    equivalentZStatistic = models.FloatField()
    value = models.FloatField()
    qValueFDR = models.FloatField()
    pValueUncorrected = models.FloatField()
    pValueFWER = models.FloatField()
    wasDerivedFrom = models.ForeignKey(Cluster)
    label = models.CharField(max_length=200)


class HeightThreshold(models.Model):
    value = models.FloatField()
    userSpecifiedThresholdType = models.CharField(max_length=200)
    pValueUncorrected = models.FloatField()
    pValueFWER = models.FloatField()
    label = models.CharField(max_length=200)


class ParameterEstimateMap(models.Model):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    label = models.CharField(max_length=200)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace)
    wasGeneratedBy = models.ForeignKey(ModelParameterEstimation)


class SearchSpaceMap(models.Model):
    expectedNumberOfClusters = models.FloatField()
    expectedNumberOfVoxelsPerCluster = models.FloatField()
    reselSize = models.FloatField()
    wasGeneratedBy = models.ForeignKey(Inference)
    smallestSignifClusterSizeInVoxelsFDR05 = models.IntField()
    smallestSignifClusterSizeInVoxelsFWE05 = models.IntField()
    heightCriticalThresholdFDR05 = models.FloatField()
    searchVolumeInVoxels = models.IntField()
    noiseFWHMInVoxels = models.CharField(max_length=200)
    sha512 = models.CharField(max_length=200)
    searchVolumeInResels = models.FloatField()
    atLocation = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    filename = models.CharField(max_length=200)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace)
    label = models.CharField(max_length=200)
    searchVolumeInUnits = models.FloatField()
    randomFieldStationarity = models.BooleanField()
    noiseFWHMInUnits = models.CharField(max_length=200)
    heightCriticalThresholdFWE05 = models.FloatField()
    searchVolumeReselsGeometry = models.CharField(max_length=200)


class Coordinate(models.Model):
    coordinate3 = models.FloatField()
    coordinate2 = models.FloatField()
    coordinate1 = models.FloatField()
    label = models.CharField(max_length=200)


class ExtentThreshold(models.Model):
    pValueUncorrected = models.FloatField()
    pValueFWER = models.FloatField()
    clusterSizeInVoxels = models.IntField()
    label = models.CharField(max_length=200)
    clusterSizeInResels = models.FloatField()


class ResidualMeanSquaresMap(models.Model):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    atCoordinateSpace = models.ForeignKey(CoordinateSpace)
    wasGeneratedBy = models.ForeignKey(ModelParametersEstimation)
    sha512 = models.CharField(max_length=200)
    label = models.CharField(max_length=200)


class StatisticMap(models.Model):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    filename = models.CharField(max_length=200)
    contrastName = models.CharField(max_length=200)
    errorDegreesOfFreedom = models.FloatField()
    atCoordinateSpace = models.ForeignKey(CoordinateSpace)
    wasGeneratedBy = models.ForeignKey(ModelParametersEstimation)
    statisticType = models.CharField(max_length=200)
    sha512 = models.CharField(max_length=200)
    label = models.CharField(max_length=200)
    effectDegreesOfFreedom = models.FloatField()


class MaskMap(models.Model):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    filename = models.CharField(max_length=200)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace)
    wasGeneratedBy = models.ForeignKey(ModelParametersEstimation)
    sha512 = models.CharField(max_length=200)
    label = models.CharField(max_length=200)


class ExcursionSet(models.Model):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    maximumIntensityProjection = models.FileField(upload_to=upload_to)
    filename = models.CharField(max_length=200)
    pValue = models.FloatField()
    numberOfClusters = models.IntField()
    atCoordinateSpace = models.ForeignKey(CoordinateSpace)
    wasGeneratedBy = models.ForeignKey(Inference)
    sha512 = models.CharField(max_length=200)
    label = models.CharField(max_length=200)
    clusterLabelsMap = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())


class ReselsPerVoxelMap(models.Model):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    atCoordinateSpace = models.ForeignKey(CoordinateSpace)
    wasGeneratedBy = models.ForeignKey(ModelParametersEstimation)
    sha512 = models.CharField(max_length=200)
    label = models.CharField(max_length=200)


class CoordinateSpace(models.Model):
    voxelUnits = models.CharField(max_length=200)
    dimensionsInVoxels = models.CharField(max_length=200)
    inWorldCoordinateSystem = models.CharField(max_length=200)
    voxelSize = models.CharField(max_length=200)
    voxelToWorldMapping = models.CharField(max_length=200)
    numberOfDimensions = models.IntField()
    label = models.CharField(max_length=200)


class ContrastStandardErrorMap(models.Model):
    atLocation = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    filename = models.CharField(max_length=200)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace)
    wasGeneratedBy = models.ForeignKey(ContrastEstimation)
    sha512 = models.CharField(max_length=200)
    label = models.CharField(max_length=200)


class ContrastWeights(models.Model):
    statisticType = models.CharField(max_length=200)
    label = models.CharField(max_length=200)
    contrastName = models.CharField(max_length=200)
    value = models.CharField(max_length=200)
    

class ModelParametersEstimation(models.Model):
    withEstimationMethod = models.CharField(max_length=200)
    label = models.CharField(max_length=200)
    wasAssociatedWith = models.CharField(max_length=200)
    used = models.ForeignKey(DesignMatrix)


class Inference(models.Model):
    hasAlternativeHypothesis = models.CharField(max_length=200)
    label = models.CharField(max_length=200)
    wasAssociatedWith = models.CharField(max_length=200)
    used = models.ForeignKey(ReselsPerVoxelMap)


class ContrastEstimation(models.Model):
    wasAssociatedWith = models.CharField(max_length=200)
    label = models.CharField(max_length=200)
    used = models.ForeignKey(MaskMap)

