import django.db.models as models
from neurovault.apps.statmaps.models import upload_to
from neurovault.apps.statmaps.storage import NiftiGzStorage

class Prov(models.Model):
    prov_type = models.CharField(max_length=200)
    prov_label = models.CharField(max_length=200)
    prov_URI = models.CharField(max_length=200, primary_key=True)
    class Meta:
        abstract = True

 
class ProvEntity(Prov):
    class Meta:
        abstract = True


class ProvActivity(Prov):
    class Meta:
        abstract = True


class CoordinateSpace(ProvEntity):
    voxelUnits = models.CharField(max_length=200)
    dimensionsInVoxels = models.CharField(max_length=200)
    inWorldCoordinateSystem = models.CharField(max_length=200)
    voxelSize = models.CharField(max_length=200)
    voxelToWorldMapping = models.CharField(max_length=200)
    numberOfDimensions = models.IntegerField()
    
    
class Map(ProvEntity):
    format = models.CharField(max_length=200)
    sha512 = models.CharField(max_length=200)
    filename = models.CharField(max_length=200)
    

class Image(ProvEntity):
    models.FileField(upload_to=upload_to)


# ## Model Fitting
    
class ContrastWeights(ProvEntity):
    _statisticsType_choices = [("http://www.incf.org/ns/nidash/nidm#ZStatistic", "Z"),
                               ("http://www.incf.org/ns/nidash/nidm#Statistic", "Other"),
                               ("http://www.incf.org/ns/nidash/nidm#FStatistic", "F"),
                               ("http://www.incf.org/ns/nidash/nidm#TStatistic", "F")]
    statisticType = models.CharField(max_length=200, choices=_statisticsType_choices)
    contrastName = models.CharField(max_length=200)
    value = models.CharField(max_length=200)


class Data(ProvEntity):
    grandMeanScaling = models.BooleanField(default=None)
    targetIntensity = models.FloatField()
    

class DesignMatrix(ProvEntity):
    image = models.OneToOneField(Image)
    file = models.FileField(upload_to=upload_to)
    
    
class NoiseModel(ProvEntity):
    _dependenceSpatialModel_choices = [("http://www.incf.org/ns/nidash/nidm#SpatiallyLocalModel", "Spatiakky Local"),
                                       ("http://www.incf.org/ns/nidash/nidm#SpatialModel", "Spatial"),
                                       ("http://www.incf.org/ns/nidash/nidm#SpatiallyRegularizedModel", "SpatiallyRegularized"),
                                       ("http://www.incf.org/ns/nidash/nidm#SpatiallyGlobalModel", "Spatially Global")]
    dependenceSpatialModel = models.CharField(max_length=200, choices=_dependenceSpatialModel_choices)
    _hasNoiseDistribution_choices = [("fsl:NonParametricSymmetricDistribution", "Non-Parametric Symmetric"),
                                     ("http://www.incf.org/ns/nidash/nidm#GaussianDistribution", "Gaussian"),
                                     ("http://www.incf.org/ns/nidash/nidm#NoiseDistribution", "Noise"),
                                     ("http://www.incf.org/ns/nidash/nidm#PoissonDistribution", "Poisson"),
                                     ("fsl:BinomialDistribution", "Binomial"),
                                     ("http://www.incf.org/ns/nidash/nidm#NonParametricDistribution", "Non-Parametric")]
    hasNoiseDistribution = models.CharField(max_length=200, choices=_hasNoiseDistribution_choices)
    _hasNoiseDependence_choices = [("http://www.incf.org/ns/nidash/nidm#ArbitrarilyCorrelatedNoise", "Arbitrarily Correlated"),
                                   ("http://www.incf.org/ns/nidash/nidm#ExchangeableNoise", "Exchangable"),
                                   ("http://www.incf.org/ns/nidash/nidm#SeriallyCorrelatedNoise", "Serially Correlated"),
                                   ("http://www.incf.org/ns/nidash/nidm#CompoundSymmetricNoise", "Compound Symmetric"),
                                   ("http://www.incf.org/ns/nidash/nidm#IndependentNoise", "Independent")]
    hasNoiseDependence = models.CharField(max_length=200, choices=_hasNoiseDependence_choices)
    noiseVarianceHomogeneous = models.BooleanField(default=None)
    _varianceSpatialModel_choices = [("http://www.incf.org/ns/nidash/nidm#SpatiallyLocalModel", "Spatially Local"),
                                     ("http://www.incf.org/ns/nidash/nidm#SpatialModel", "Spatial"),
                                     ("http://www.incf.org/ns/nidash/nidm#SpatiallyRegularizedModel", "Spatially Regularized"),
                                     ("http://www.incf.org/ns/nidash/nidm#SpatiallyGlobalModel", "Spatially Global")]
    varianceSpatialModel = models.CharField(max_length=200, choices=_varianceSpatialModel_choices)
    
    
class ModelParametersEstimation(ProvActivity):
    _withEstimation_method_choices = [("http://www.incf.org/ns/nidash/nidm#WeightedLeastSquares", "WeightedLeastSquares"),
                                      ("http://www.incf.org/ns/nidash/nidm#OrdinaryLeastSquares", "OrdinaryLeastSquares"),
                                      ("http://www.incf.org/ns/nidash/nidm#GeneralizedLeastSquares", "GeneralizedLeastSquares"),
                                      ("http://www.incf.org/ns/nidash/nidm#EstimationMethod", "EstimatedMethod"),
                                      ("http://www.incf.org/ns/nidash/nidm#RobustIterativelyReweighedLeastSquares", "RobustIterativelyReweighedLeastSquares")]
    withEstimationMethod = models.CharField(max_length=200, choices=_withEstimation_method_choices)
    designMatrix = models.ForeignKey(DesignMatrix)
    data = models.ForeignKey(Data)
    noiseModel = models.ForeignKey(NoiseModel)
    
    
class MaskMap(ProvEntity):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+')
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+')
    hasMapHeader = models.CharField(max_length=200)
    modelParametersEstimation = models.OneToOneField(ModelParametersEstimation)
    map = models.OneToOneField(Map)
    
    
class ParameterEstimateMap(ProvEntity):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+')
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+')
    hasMapHeader = models.CharField(max_length=200)
    modelParameterEstimation = models.ForeignKey(ModelParametersEstimation)
    map = models.OneToOneField(Map)
    
    
class ResidualMeanSquaresMap(ProvEntity):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+')
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+')
    modelParametersEstimation = models.OneToOneField(ModelParametersEstimation)
    sha512 = models.CharField(max_length=200)
    map = models.OneToOneField(Map)
    

class ContrastEstimation(ProvActivity):
    parameterEstimationMap = models.ForeignKey(ParameterEstimateMap)
    residualMeanSquaresMap = models.ForeignKey(ResidualMeanSquaresMap)
    maskMap = models.ForeignKey(MaskMap)
    contrastWeights = models.ForeignKey(ContrastWeights)


class ContrastMap(ProvEntity):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    contrastName = models.CharField(max_length=200)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+')
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+')
    contrastEstimation = models.ForeignKey(ContrastEstimation)
    sha512 = models.CharField(max_length=200)
    map = models.OneToOneField(Map)
    
    
class StatisticMap(ProvEntity):
    file = models.FileField(storage=NiftiGzStorage())
    contrastName = models.CharField(max_length=200, null=True)
    errorDegreesOfFreedom = models.FloatField(null=True)
    effectDegreesOfFreedom = models.FloatField(null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    modelParametersEstimation = models.ForeignKey(ModelParametersEstimation, null=True)
    statisticType = models.CharField(max_length=200, null=True)
    sha512 = models.CharField(max_length=200, null=True)
    map = models.OneToOneField(Map, null=True)
    

class ContrastStandardErrorMap(ProvEntity):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+')
    contrastEstimation = models.OneToOneField(ContrastEstimation)
    sha512 = models.CharField(max_length=200)
    map = models.OneToOneField(Map)
    
    
# ## Inference

class ReselsPerVoxelMap(ProvEntity):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+')
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+')
    modelParametersEstimation = models.OneToOneField(ModelParametersEstimation)
    sha512 = models.CharField(max_length=200)
    map = models.OneToOneField(Map)

class Inference(ProvActivity):
    alternativeHypothesis = models.CharField(max_length=200)
    _hasAlternativeHypothesis_choices = [("http://www.incf.org/ns/nidash/nidm#TwoTailedTest", "Two Tailed"),
                                         ("http://www.incf.org/ns/nidash/nidm#OneTailedTest", "One Tailed")]
    hasAlternativeHypothesis = models.CharField(max_length=200, choices=_hasAlternativeHypothesis_choices)
    contrastMap = models.ForeignKey(ContrastMap)
    statisticMap = models.ForeignKey(StatisticMap)
    reselsPerVoxelMap = models.ForeignKey(ReselsPerVoxelMap)

    
class Coordinate(ProvEntity):
    coordinate3 = models.FloatField()
    coordinate2 = models.FloatField()
    coordinate1 = models.FloatField()
    
    
class ClusterLabelMap(ProvEntity):
    map = models.OneToOneField(Map)
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    
    
class ExcursionSet(ProvEntity):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    maximumIntensityProjection = models.FileField(upload_to=upload_to)
    pValue = models.FloatField()
    numberOfClusters = models.IntegerField()
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+')
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+')
    inference = models.ForeignKey(Inference)
    sha512 = models.CharField(max_length=200)
    clusterLabelMap = models.ForeignKey(ClusterLabelMap)
    image = models.OneToOneField(Image)
    underlayFile = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    
    
class Cluster(ProvEntity):
    qValueFDR = models.FloatField()
    clusterLabelId = models.IntegerField()
    pValueUncorrected = models.FloatField()
    pValueFWER = models.FloatField()
    excursionSet = models.ForeignKey(ExcursionSet)
    clusterSizeInVoxels = models.IntegerField()
    clusterSizeInResels = models.FloatField()
    
    
class ExtentThreshold(ProvEntity):
    userSpecifiedThresholdType = models.CharField(max_length=200)
    pValueUncorrected = models.FloatField()
    pValueFWER = models.FloatField()
    qValueFDR = models.FloatField()
    clusterSizeInVoxels = models.IntegerField()
    clusterSizeInResels = models.FloatField()
    

class HeightThreshold(ProvEntity):
    value = models.FloatField()
    userSpecifiedThresholdType = models.CharField(max_length=200)
    pValueUncorrected = models.FloatField()
    qValueFDR = models.FloatField()
    pValueFWER = models.FloatField()
    

class Peak(ProvEntity):
    coordinate = models.OneToOneField(Coordinate)
    equivalentZStatistic = models.FloatField()
    value = models.FloatField()
    qValueFDR = models.FloatField()
    pValueUncorrected = models.FloatField()
    pValueFWER = models.FloatField()
    cluster = models.ForeignKey(Cluster)
    
    
class SearchSpaceMap(ProvEntity):
    expectedNumberOfClusters = models.FloatField()
    expectedNumberOfVoxelsPerCluster = models.FloatField()
    reselSize = models.FloatField()
    inference = models.ForeignKey(Inference)
    smallestSignifClusterSizeInVoxelsFDR05 = models.IntegerField()
    smallestSignifClusterSizeInVoxelsFWE05 = models.IntegerField()
    heightCriticalThresholdFDR05 = models.FloatField()
    heightCriticalThresholdFWE05 = models.FloatField()
    searchVolumeInVoxels = models.IntegerField()
    searchVolumeInUnits = models.FloatField()
    noiseFWHMInVoxels = models.CharField(max_length=200)
    noiseFWHMInUnits = models.CharField(max_length=200)
    sha512 = models.CharField(max_length=200)
    searchVolumeInResels = models.FloatField()
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage())
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+')
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+')
    randomFieldStationarity = models.BooleanField(default=None)
    searchVolumeReselsGeometry = models.CharField(max_length=200)
    map = models.OneToOneField(Map)
    
