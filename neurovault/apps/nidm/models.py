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
    voxelUnits = models.CharField(max_length=200, null=True)
    dimensionsInVoxels = models.CharField(max_length=200, null=True)
    inWorldCoordinateSystem = models.CharField(max_length=200, null=True)
    voxelSize = models.CharField(max_length=200, null=True)
    voxelToWorldMapping = models.CharField(max_length=200, null=True)
    numberOfDimensions = models.IntegerField(null=True)
    
    
class Map(ProvEntity):
    format = models.CharField(max_length=200, null=True)
    sha512 = models.CharField(max_length=200, null=True)
    filename = models.CharField(max_length=200, null=True)
    

class Image(ProvEntity):
    models.FileField(upload_to=upload_to, null=True)


# ## Model Fitting
    
class ContrastWeights(ProvEntity):
    _statisticsType_choices = [("http://www.incf.org/ns/nidash/nidm#ZStatistic", "Z"),
                               ("http://www.incf.org/ns/nidash/nidm#Statistic", "Other"),
                               ("http://www.incf.org/ns/nidash/nidm#FStatistic", "F"),
                               ("http://www.incf.org/ns/nidash/nidm#TStatistic", "F")]
    statisticType = models.CharField(max_length=200, choices=_statisticsType_choices, null=True)
    contrastName = models.CharField(max_length=200, null=True)
    value = models.CharField(max_length=200, null=True)


class Data(ProvEntity):
    grandMeanScaling = models.BooleanField(default=None, null=True)
    targetIntensity = models.FloatField(null=True)
    

class DesignMatrix(ProvEntity):
    image = models.OneToOneField(Image, null=True)
    file = models.FileField(upload_to=upload_to, null=True)
    
    
class NoiseModel(ProvEntity):
    _dependenceSpatialModel_choices = [("http://www.incf.org/ns/nidash/nidm#SpatiallyLocalModel", "Spatiakky Local"),
                                       ("http://www.incf.org/ns/nidash/nidm#SpatialModel", "Spatial"),
                                       ("http://www.incf.org/ns/nidash/nidm#SpatiallyRegularizedModel", "SpatiallyRegularized"),
                                       ("http://www.incf.org/ns/nidash/nidm#SpatiallyGlobalModel", "Spatially Global")]
    dependenceSpatialModel = models.CharField(max_length=200, choices=_dependenceSpatialModel_choices, null=True)
    _hasNoiseDistribution_choices = [("fsl:NonParametricSymmetricDistribution", "Non-Parametric Symmetric"),
                                     ("http://www.incf.org/ns/nidash/nidm#GaussianDistribution", "Gaussian"),
                                     ("http://www.incf.org/ns/nidash/nidm#NoiseDistribution", "Noise"),
                                     ("http://www.incf.org/ns/nidash/nidm#PoissonDistribution", "Poisson"),
                                     ("fsl:BinomialDistribution", "Binomial"),
                                     ("http://www.incf.org/ns/nidash/nidm#NonParametricDistribution", "Non-Parametric")]
    hasNoiseDistribution = models.CharField(max_length=200, choices=_hasNoiseDistribution_choices, null=True)
    _hasNoiseDependence_choices = [("http://www.incf.org/ns/nidash/nidm#ArbitrarilyCorrelatedNoise", "Arbitrarily Correlated"),
                                   ("http://www.incf.org/ns/nidash/nidm#ExchangeableNoise", "Exchangable"),
                                   ("http://www.incf.org/ns/nidash/nidm#SeriallyCorrelatedNoise", "Serially Correlated"),
                                   ("http://www.incf.org/ns/nidash/nidm#CompoundSymmetricNoise", "Compound Symmetric"),
                                   ("http://www.incf.org/ns/nidash/nidm#IndependentNoise", "Independent")]
    hasNoiseDependence = models.CharField(max_length=200, choices=_hasNoiseDependence_choices, null=True)
    noiseVarianceHomogeneous = models.BooleanField(default=None, null=True)
    _varianceSpatialModel_choices = [("http://www.incf.org/ns/nidash/nidm#SpatiallyLocalModel", "Spatially Local"),
                                     ("http://www.incf.org/ns/nidash/nidm#SpatialModel", "Spatial"),
                                     ("http://www.incf.org/ns/nidash/nidm#SpatiallyRegularizedModel", "Spatially Regularized"),
                                     ("http://www.incf.org/ns/nidash/nidm#SpatiallyGlobalModel", "Spatially Global")]
    varianceSpatialModel = models.CharField(max_length=200, choices=_varianceSpatialModel_choices, null=True)
    
    
class ModelParametersEstimation(ProvActivity):
    _withEstimation_method_choices = [("http://www.incf.org/ns/nidash/nidm#WeightedLeastSquares", "WeightedLeastSquares"),
                                      ("http://www.incf.org/ns/nidash/nidm#OrdinaryLeastSquares", "OrdinaryLeastSquares"),
                                      ("http://www.incf.org/ns/nidash/nidm#GeneralizedLeastSquares", "GeneralizedLeastSquares"),
                                      ("http://www.incf.org/ns/nidash/nidm#EstimationMethod", "EstimatedMethod"),
                                      ("http://www.incf.org/ns/nidash/nidm#RobustIterativelyReweighedLeastSquares", "RobustIterativelyReweighedLeastSquares")]
    withEstimationMethod = models.CharField(max_length=200, choices=_withEstimation_method_choices, null=True)
    designMatrix = models.ForeignKey(DesignMatrix, null=True)
    data = models.ForeignKey(Data, null=True)
    noiseModel = models.ForeignKey(NoiseModel, null=True)
    
    
class MaskMap(ProvEntity):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage(), null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    hasMapHeader = models.CharField(max_length=200, null=True)
    modelParametersEstimation = models.OneToOneField(ModelParametersEstimation, null=True)
    map = models.OneToOneField(Map, null=True)
    
    
class ParameterEstimateMap(ProvEntity):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage(), null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    hasMapHeader = models.CharField(max_length=200, null=True)
    modelParameterEstimation = models.ForeignKey(ModelParametersEstimation, null=True)
    map = models.OneToOneField(Map, null=True)
    
    
class ResidualMeanSquaresMap(ProvEntity):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage(), null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    modelParametersEstimation = models.OneToOneField(ModelParametersEstimation, null=True)
    sha512 = models.CharField(max_length=200, null=True)
    map = models.OneToOneField(Map, null=True)
    

class ContrastEstimation(ProvActivity):
    parameterEstimationMap = models.ForeignKey(ParameterEstimateMap, null=True)
    residualMeanSquaresMap = models.ForeignKey(ResidualMeanSquaresMap, null=True)
    maskMap = models.ForeignKey(MaskMap, null=True)
    contrastWeights = models.ForeignKey(ContrastWeights, null=True)


class ContrastMap(ProvEntity):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage(), null=True)
    contrastName = models.CharField(max_length=200, null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    contrastEstimation = models.ForeignKey(ContrastEstimation, null=True)
    sha512 = models.CharField(max_length=200, null=True)
    map = models.OneToOneField(Map, null=True)
    
    
class StatisticMap(ProvEntity):
    file = models.FileField(storage=NiftiGzStorage(), null=True)
    contrastName = models.CharField(max_length=200, null=True, null=True)
    errorDegreesOfFreedom = models.FloatField(null=True, null=True)
    effectDegreesOfFreedom = models.FloatField(null=True, null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, null=True)
    modelParametersEstimation = models.ForeignKey(ModelParametersEstimation, null=True, null=True)
    statisticType = models.CharField(max_length=200, null=True, null=True)
    sha512 = models.CharField(max_length=200, null=True, null=True)
    map = models.OneToOneField(Map, null=True, null=True)
    

class ContrastStandardErrorMap(ProvEntity):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage(), null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    contrastEstimation = models.OneToOneField(ContrastEstimation, null=True)
    sha512 = models.CharField(max_length=200, null=True)
    map = models.OneToOneField(Map, null=True)
    
    
# ## Inference

class ReselsPerVoxelMap(ProvEntity):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage(), null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    modelParametersEstimation = models.OneToOneField(ModelParametersEstimation, null=True)
    sha512 = models.CharField(max_length=200, null=True)
    map = models.OneToOneField(Map, null=True)

class Inference(ProvActivity):
    alternativeHypothesis = models.CharField(max_length=200, null=True)
    _hasAlternativeHypothesis_choices = [("http://www.incf.org/ns/nidash/nidm#TwoTailedTest", "Two Tailed"),
                                         ("http://www.incf.org/ns/nidash/nidm#OneTailedTest", "One Tailed")]
    hasAlternativeHypothesis = models.CharField(max_length=200, choices=_hasAlternativeHypothesis_choices, null=True)
    contrastMap = models.ForeignKey(ContrastMap, null=True)
    statisticMap = models.ForeignKey(StatisticMap, null=True)
    reselsPerVoxelMap = models.ForeignKey(ReselsPerVoxelMap, null=True)

    
class Coordinate(ProvEntity):
    coordinate3 = models.FloatField(null=True)
    coordinate2 = models.FloatField(null=True)
    coordinate1 = models.FloatField(null=True)
    
    
class ClusterLabelMap(ProvEntity):
    map = models.OneToOneField(Map, null=True)
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage(), null=True)
    
    
class ExcursionSet(ProvEntity):
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage(), null=True)
    maximumIntensityProjection = models.FileField(upload_to=upload_to, null=True)
    pValue = models.FloatField(null=True)
    numberOfClusters = models.IntegerField(null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    inference = models.ForeignKey(Inference, null=True)
    sha512 = models.CharField(max_length=200, null=True)
    clusterLabelMap = models.ForeignKey(ClusterLabelMap, null=True)
    image = models.OneToOneField(Image, null=True)
    underlayFile = models.FileField(upload_to=upload_to, storage=NiftiGzStorage(), null=True)
    
    
class Cluster(ProvEntity):
    qValueFDR = models.FloatField(null=True)
    clusterLabelId = models.IntegerField(null=True)
    pValueUncorrected = models.FloatField(null=True)
    pValueFWER = models.FloatField(null=True)
    excursionSet = models.ForeignKey(ExcursionSet, null=True)
    clusterSizeInVoxels = models.IntegerField(null=True)
    clusterSizeInResels = models.FloatField(null=True)
    
    
class ExtentThreshold(ProvEntity):
    userSpecifiedThresholdType = models.CharField(max_length=200, null=True)
    pValueUncorrected = models.FloatField(null=True)
    pValueFWER = models.FloatField(null=True)
    qValueFDR = models.FloatField(null=True)
    clusterSizeInVoxels = models.IntegerField(null=True)
    clusterSizeInResels = models.FloatField(null=True)
    

class HeightThreshold(ProvEntity):
    value = models.FloatField(null=True)
    userSpecifiedThresholdType = models.CharField(max_length=200, null=True)
    pValueUncorrected = models.FloatField(null=True)
    qValueFDR = models.FloatField(null=True)
    pValueFWER = models.FloatField(null=True)
    

class Peak(ProvEntity):
    coordinate = models.OneToOneField(Coordinate)
    equivalentZStatistic = models.FloatField(null=True)
    value = models.FloatField(null=True)
    qValueFDR = models.FloatField(null=True)
    pValueUncorrected = models.FloatField(null=True)
    pValueFWER = models.FloatField(null=True)
    cluster = models.ForeignKey(Cluster, null=True)
    
    
class SearchSpaceMap(ProvEntity):
    expectedNumberOfClusters = models.FloatField(null=True)
    expectedNumberOfVoxelsPerCluster = models.FloatField(null=True)
    reselSize = models.FloatField(null=True)
    inference = models.ForeignKey(Inference, null=True)
    smallestSignifClusterSizeInVoxelsFDR05 = models.IntegerField(null=True)
    smallestSignifClusterSizeInVoxelsFWE05 = models.IntegerField(null=True)
    heightCriticalThresholdFDR05 = models.FloatField(null=True)
    heightCriticalThresholdFWE05 = models.FloatField(null=True)
    searchVolumeInVoxels = models.IntegerField(null=True)
    searchVolumeInUnits = models.FloatField(null=True)
    noiseFWHMInVoxels = models.CharField(max_length=200, null=True)
    noiseFWHMInUnits = models.CharField(max_length=200, null=True)
    sha512 = models.CharField(max_length=200, null=True)
    searchVolumeInResels = models.FloatField(null=True)
    file = models.FileField(upload_to=upload_to, storage=NiftiGzStorage(), null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    randomFieldStationarity = models.BooleanField(default=None, null=True)
    searchVolumeReselsGeometry = models.CharField(max_length=200, null=True)
    map = models.OneToOneField(Map, null=True)
    
