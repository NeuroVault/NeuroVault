import django.db.models as models
import os
from django.core.files.base import ContentFile

class Prov(models.Model):
    prov_type = models.CharField(max_length=200)
    prov_label = models.CharField(max_length=200)
    prov_URI = models.CharField(max_length=200, unique=True)
    
    _translations = {'http://www.w3.org/1999/02/22-rdf-syntax-ns#type': ('prov_type', str),
                     'http://www.w3.org/2000/01/rdf-schema#label': ("prov_label", str)}
    
    @classmethod
    def create(cls, uri, graph, nidm_file_handle):
        try:
            instance = cls.objects.get(prov_URI=uri)
        except cls.DoesNotExist:
            print "creating %s"%uri
            query = """
prefix prov: <http://www.w3.org/ns/prov#>
prefix nidm: <http://www.incf.org/ns/nidash/nidm#>
prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?property ?value ?value_class WHERE {
 <%s> ?property ?value .
 OPTIONAL {?value a ?value_class .}
}
"""%uri
            results = graph.query(query)
            if not results:
                raise Exception("URI %s not found in graph"%uri)
            property_value = {}
            for _, row in enumerate(results.bindings):
                if "value_class" in row:
                    key = (str(row["property"]), str(row["value_class"]).split("#")[-1])
                else:
                    key = str(row["property"])
                property_value[key] = row["value"].decode()
            
            instance = cls()
            instance.prov_URI = uri
            for property_uri, (property_name, property_type) in cls._translations.iteritems():
                if property_uri in property_value:
                    if property_uri is tuple:
                        property_uri = property_uri[0]
                    if property_type is file:
                        file_field = getattr(instance, property_name)
                        root = nidm_file_handle.infolist()[0].filename
                        _,  filename = os.path.split(property_value[property_uri])
                        file_path = os.path.join(root + filename)
                        file_handle = nidm_file_handle.open(file_path, "r")
                        file_field.save(filename, ContentFile(file_handle.read()))
                    elif issubclass(property_type, Prov):
                        instance = property_type.create(property_value[property_uri], graph, nidm_file_handle)
                        setattr(instance, property_name, instance)
                    else:
                        setattr(instance, property_name, property_type(property_value[property_uri]))
            print "unused attributes for %s"%uri
            print set(property_value.keys()) - set(cls._translations.keys())

        return instance
        
    class Meta:
        abstract = True

 
class ProvEntity(Prov):
    class Meta:
        abstract = True


class ProvActivity(Prov):
    class Meta:
        abstract = True


class CoordinateSpace(ProvEntity):
    _translations = dict(Prov._translations.items() + {'http://www.incf.org/ns/nidash/nidm#voxelUnits': ("voxelUnits", str), 
                                                       'http://www.incf.org/ns/nidash/nidm#dimensionsInVoxels': ("dimensionsInVoxels", str),
                                                       'http://www.incf.org/ns/nidash/nidm#inWorldCoordinateSystem': ("inWorldCoordinateSystem", str),
                                                       'http://www.incf.org/ns/nidash/nidm#voxelSize': ("voxelSize", str),
                                                       'http://www.incf.org/ns/nidash/nidm#voxelToWorldMapping': ("voxelToWorldMapping", str),
                                                       'http://www.incf.org/ns/nidash/nidm#numberOfDimensions': ("numberOfDimensions", int)}.items())
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
    
    _translations = dict(Prov._translations.items() + {'http://purl.org/dc/terms/format': ("format", str),
                                                      'http://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions#sha512': ("sha512", str),
                                                      'http://www.incf.org/ns/nidash/nidm#filename': ("filename", str)}.items())
            

class Image(ProvEntity):
    _translations = dict(Prov._translations.items() + {'http://www.w3.org/ns/prov#atLocation': ("file", str)}.items())
  
    file = models.FileField(upload_to='hash_filestore', null=True)


# ## Model Fitting
    
class ContrastWeights(ProvEntity):
    _translations = dict(Prov._translations.items() + {'http://www.incf.org/ns/nidash/nidm#statisticType': ("statisticType", str),
                                                       'http://www.incf.org/ns/nidash/nidm#contrastName': ("contrastName", str),
                                                       'http://www.w3.org/ns/prov#value': ("value", str)}.items())
    _statisticsType_choices = [("http://www.incf.org/ns/nidash/nidm#ZStatistic", "Z"),
                               ("http://www.incf.org/ns/nidash/nidm#Statistic", "Other"),
                               ("http://www.incf.org/ns/nidash/nidm#FStatistic", "F"),
                               ("http://www.incf.org/ns/nidash/nidm#TStatistic", "F")]
    statisticType = models.CharField(max_length=200, choices=_statisticsType_choices, null=True)
    contrastName = models.CharField(max_length=200, null=True)
    value = models.CharField(max_length=200, null=True)


class Data(ProvEntity):
    _translations = dict(Prov._translations.items() + {'http://www.incf.org/ns/nidash/nidm#grandMeanScaling': ('grandMeanScaling', bool),
                                                       'http://www.incf.org/ns/nidash/nidm#targetIntensity': ('targetIntensity', float)}.items())
    grandMeanScaling = models.NullBooleanField(default=None, null=True)
    targetIntensity = models.FloatField(null=True)
    

class DesignMatrix(ProvEntity):
    _translations = dict(Prov._translations.items() + {'http://www.w3.org/ns/prov#atLocation': ("file", file),
                                                       ('http://www.incf.org/ns/nidash/nidm#visualisation', 'Image'): ("image", Image)}.items())
    image = models.OneToOneField(Image, null=True)
    file = models.FileField(upload_to='hash_filestore', null=True)
    
    
class NoiseModel(ProvEntity):
    _translations = dict(Prov._translations.items() + {'http://www.incf.org/ns/nidash/nidm#noiseVarianceHomogeneous': ('noiseVarianceHomogeneous', bool),
                                                       'http://www.incf.org/ns/nidash/nidm#varianceSpatialModel': ('varianceSpatialModel', str),
                                                       'http://www.incf.org/ns/nidash/nidm#dependenceSpatialModel': ('dependenceSpatialModel', str),
                                                       'http://www.incf.org/ns/nidash/nidm#hasNoiseDependence': ('hasNoiseDependence', str),
                                                       'http://www.incf.org/ns/nidash/nidm#hasNoiseDistribution': ('hasNoiseDistribution', str)}.items())
    
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
    noiseVarianceHomogeneous = models.NullBooleanField(default=None, null=True)
    _varianceSpatialModel_choices = [("http://www.incf.org/ns/nidash/nidm#SpatiallyLocalModel", "Spatially Local"),
                                     ("http://www.incf.org/ns/nidash/nidm#SpatialModel", "Spatial"),
                                     ("http://www.incf.org/ns/nidash/nidm#SpatiallyRegularizedModel", "Spatially Regularized"),
                                     ("http://www.incf.org/ns/nidash/nidm#SpatiallyGlobalModel", "Spatially Global")]
    varianceSpatialModel = models.CharField(max_length=200, choices=_varianceSpatialModel_choices, null=True)
    
    
class ModelParametersEstimation(ProvActivity):
    _translations = dict(Prov._translations.items() + {('http://www.w3.org/ns/prov#used', 'Data'): ("data", Data), 
                                                       'http://www.incf.org/ns/nidash/nidm#withEstimationMethod': ("withEstimationMethod", str),
                                                       ('http://www.w3.org/ns/prov#used', 'DesignMatrix'): ("designMatrix", DesignMatrix),
                                                       ('http://www.w3.org/ns/prov#used', 'NoiseModel'): ("noiseModel", NoiseModel)}.items())
    
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
    _translations = dict(Prov._translations.items() + {'http://www.w3.org/ns/prov#atLocation': ("file", file), 
                                                       ('http://www.incf.org/ns/nidash/nidm#atCoordinateSpace', 'CoordinateSpace'): ("atCoordinateSpace", CoordinateSpace),
                                                       ('http://www.w3.org/ns/prov#wasDerivedFrom', 'Map'): ("map", Map),
                                                       'http://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions#sha512': ("sha512", str),
                                                       ('http://www.w3.org/ns/prov#wasGeneratedBy', 'ModelParametersEstimation'): ("modelParametersEstimation", ModelParametersEstimation)}.items())
    file = models.FileField(upload_to='hash_filestore', null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    hasMapHeader = models.CharField(max_length=200, null=True)
    modelParametersEstimation = models.OneToOneField(ModelParametersEstimation, null=True)
    map = models.OneToOneField(Map, null=True)
    
    
class ParameterEstimateMap(ProvEntity):
    _translations = dict(Prov._translations.items() + {('http://www.incf.org/ns/nidash/nidm#atCoordinateSpace', 'CoordinateSpace'): ("atCoordinateSpace", CoordinateSpace),
                                                       ('http://www.w3.org/ns/prov#wasGeneratedBy', 'ModelParametersEstimation'): ("modelParametersEstimation", ModelParametersEstimation),
                                                       ('http://www.w3.org/ns/prov#wasDerivedFrom', 'Map'): ("map", Map)}.items())
    file = models.FileField(upload_to='hash_filestore', null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    hasMapHeader = models.CharField(max_length=200, null=True)
    modelParameterEstimation = models.ForeignKey(ModelParametersEstimation, null=True)
    map = models.OneToOneField(Map, null=True)
    
    
class ResidualMeanSquaresMap(ProvEntity):
    _translations = dict(Prov._translations.items() + {'http://www.w3.org/ns/prov#atLocation': ("file", file), 
                                                       ('http://www.incf.org/ns/nidash/nidm#atCoordinateSpace', 'CoordinateSpace'): ("atCoordinateSpace", CoordinateSpace),
                                                       ('http://www.w3.org/ns/prov#wasDerivedFrom', 'Map'): ("map", Map), 
                                                       'http://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions#sha512': ("sha512", str),
                                                       ('http://www.w3.org/ns/prov#wasGeneratedBy', 'ModelParametersEstimation'): ("modelParametersEstimation", ModelParametersEstimation)}.items())
    file = models.FileField(null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    modelParametersEstimation = models.OneToOneField(ModelParametersEstimation, null=True)
    sha512 = models.CharField(max_length=200, null=True)
    map = models.OneToOneField(Map, null=True)
    

class ContrastEstimation(ProvActivity):
    _translations = dict(Prov._translations.items() + {('http://www.w3.org/ns/prov#used', 'ParameterEstimateMap'): ("parameterEstimateMap", ParameterEstimateMap),
                                                       ('http://www.w3.org/ns/prov#used', 'ResidualMeanSquaresMap'): ("residualMeanSquaresMap", ResidualMeanSquaresMap),
                                                       ('http://www.w3.org/ns/prov#used', 'MaskMap'): ("maskMap", MaskMap),
                                                       ('http://www.w3.org/ns/prov#used', 'ContrastWeights'): ("contrastWeights", ContrastWeights)}.items())
    parameterEstimateMap = models.ForeignKey(ParameterEstimateMap, null=True)
    residualMeanSquaresMap = models.ForeignKey(ResidualMeanSquaresMap, null=True)
    maskMap = models.ForeignKey(MaskMap, null=True)
    contrastWeights = models.ForeignKey(ContrastWeights, null=True)


class ContrastMap(ProvEntity):
    file = models.FileField(upload_to='hash_filestore', null=True)
    contrastName = models.CharField(max_length=200, null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    contrastEstimation = models.ForeignKey(ContrastEstimation, null=True)
    sha512 = models.CharField(max_length=200, null=True)
    map = models.OneToOneField(Map, null=True)
    
    
class StatisticMap(ProvEntity):
    nidm_identifier = "nidm:StatisticMap"
    _translations = dict(Prov._translations.items() + {'http://www.incf.org/ns/nidash/nidm#errorDegreesOfFreedom': ("errorDegreesOfFreedomu", float),
                                                       'http://www.w3.org/ns/prov#atLocation': ("file", file),
                                                       'http://www.incf.org/ns/nidash/nidm#contrastName': ('contrastName', str),
                                                       ('http://www.incf.org/ns/nidash/nidm#atCoordinateSpace', 'CoordinateSpace'): ("atCoordinateSpace", CoordinateSpace),
                                                       ('http://www.w3.org/ns/prov#wasGeneratedBy', 'ContrastEstimation'): ("contrastEstimation", ContrastEstimation),
                                                       ('http://www.w3.org/ns/prov#wasDerivedFrom', 'Map'): ("map", Map),
                                                       'http://www.incf.org/ns/nidash/nidm#statisticType': ("statisticType", str),
                                                       'http://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions#sha512': ("sha512", str),
                                                       'http://www.incf.org/ns/nidash/nidm#effectDegreesOfFreedom': ("effectDegreesOfFreedom", float)}.items())
    file = models.FileField(null=True)
    contrastName = models.CharField(max_length=200, null=True)
    errorDegreesOfFreedom = models.FloatField(null=True)
    effectDegreesOfFreedom = models.FloatField(null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    modelParametersEstimation = models.ForeignKey(ModelParametersEstimation, null=True)
    statisticType = models.CharField(max_length=200, null=True)
    sha512 = models.CharField(max_length=200, null=True)
    map = models.OneToOneField(Map, null=True)
    

class ContrastStandardErrorMap(ProvEntity):
    file = models.FileField(upload_to='hash_filestore', null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    contrastEstimation = models.OneToOneField(ContrastEstimation, null=True)
    sha512 = models.CharField(max_length=200, null=True)
    map = models.OneToOneField(Map, null=True)
    
    
# ## Inference

class ReselsPerVoxelMap(ProvEntity):
    file = models.FileField(upload_to='hash_filestore', null=True)
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
    file = models.FileField(upload_to='hash_filestore', null=True)
    
    
class ExcursionSet(ProvEntity):
    file = models.FileField(upload_to='hash_filestore', null=True)
    maximumIntensityProjection = models.FileField(upload_to='hash_filestore', null=True)
    pValue = models.FloatField(null=True)
    numberOfClusters = models.IntegerField(null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    inference = models.ForeignKey(Inference, null=True)
    sha512 = models.CharField(max_length=200, null=True)
    clusterLabelMap = models.ForeignKey(ClusterLabelMap, null=True)
    image = models.OneToOneField(Image, null=True)
    underlayFile = models.FileField(upload_to='hash_filestore', null=True)
    
    
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
    file = models.FileField(upload_to='hash_filestore', null=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True)
    randomFieldStationarity = models.NullBooleanField(default=None, null=True)
    searchVolumeReselsGeometry = models.CharField(max_length=200, null=True)
    map = models.OneToOneField(Map, null=True)
    
