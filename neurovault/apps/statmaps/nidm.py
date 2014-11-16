from models import Image, Collection
import django.db.models as models
import os
from django.core.files.base import ContentFile
from collections import OrderedDict

class CollectionPart(models.Model):
    collection = models.ForeignKey(Collection)
    
    class Meta:
        abstract = True

class Prov(models.Model):
    prov_type = models.CharField(max_length=200, null=True, blank=True)
    prov_label = models.CharField(max_length=200, null=True, blank=True)
    prov_URI = models.CharField(max_length=200, null=True, blank=True)
    
    _translations = {'http://www.w3.org/1999/02/22-rdf-syntax-ns#type': ('prov_type', str),
                     'http://www.w3.org/2000/01/rdf-schema#label': ("prov_label", str)}
    
    @classmethod
    def create_from_nidm(cls, uri, graph, nidm_file_handle, **kwargs):
        try:
            instance = cls.objects.get(prov_URI=uri, **kwargs)
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
                if key not in property_value:
                    property_value[key] = row["value"].decode()
                else:
                    if isinstance(property_value[key], list):
                        property_value[key].append(row["value"].decode())
                    else:
                        property_value[key] = [property_value[key], row["value"].decode()]
            instance = cls()
            for (key, value) in kwargs.items():
                setattr(instance, key, value)
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
                        if not isinstance(property_value[property_uri], list):
                            attr_instance = property_type.create_from_nidm(property_value[property_uri], graph, nidm_file_handle, **kwargs)
                            setattr(instance, property_name, attr_instance)#
                        else:
                            instance.save()
                            m2m = getattr(instance, property_name)
                            for val in property_value[property_uri]:
                                m2m.add(property_type.create_from_nidm(val, graph, nidm_file_handle, **kwargs))
                    else:
                        print "setting %s to %s"%(property_name, property_type(property_value[property_uri]))
                        setattr(instance, property_name, property_type(property_value[property_uri]))
            print "unused attributes for %s"%uri
            filtered = set()
            remains = set(property_value.keys()) - set(cls._translations.keys())
            for val in remains:
                if (isinstance(val, tuple) and val[1] in ('Entity', 
                                                          'Collection', 
                                                          'SoftwareAgent', 
                                                          'Agent', 
                                                          'ErrorModel', 
                                                          'SPM', 
                                                          'FSL',
                                                          'Activity',
                                                          'ClusterDefinitionCriteria',
                                                          'DisplayMaskMap',
                                                          'PeakDefinitionCriteria')) or val in ['http://www.incf.org/ns/nidash/nidm#filename', 
                                                                                  'http://purl.org/dc/terms/format']:
                    continue
                else:
                    filtered.add(val)
            if filtered:
                pass
                #raise Exception("Non empty set of remaining fields for %s: %s"%(cls.__name__, str(filtered)))
                    
            
            instance.save()
        
        return instance
        
    class Meta:
        abstract = True

 
class ProvEntity(Prov):
    class Meta:
        abstract = True


class ProvActivity(Prov):
    class Meta:
        abstract = True


class CoordinateSpace(ProvEntity, CollectionPart):
    _translations = dict(Prov._translations.items() + {'http://www.incf.org/ns/nidash/nidm#voxelUnits': ("voxelUnits", str), 
                                                       'http://www.incf.org/ns/nidash/nidm#dimensionsInVoxels': ("dimensionsInVoxels", str),
                                                       'http://www.incf.org/ns/nidash/nidm#inWorldCoordinateSystem': ("inWorldCoordinateSystem", str),
                                                       'http://www.incf.org/ns/nidash/nidm#voxelSize': ("voxelSize", str),
                                                       'http://www.incf.org/ns/nidash/nidm#voxelToWorldMapping': ("voxelToWorldMapping", str),
                                                       'http://www.incf.org/ns/nidash/nidm#numberOfDimensions': ("numberOfDimensions", int)}.items())
    voxelUnits = models.CharField(max_length=200, null=True, blank=True)
    dimensionsInVoxels = models.CharField(max_length=200, null=True, blank=True)
    inWorldCoordinateSystem = models.CharField(max_length=200, null=True, blank=True)
    voxelSize = models.CharField(max_length=200, null=True, blank=True)
    voxelToWorldMapping = models.CharField(max_length=200, null=True, blank=True)
    numberOfDimensions = models.IntegerField(null=True, blank=True)
    
    
class Map(ProvEntity, CollectionPart):
    format = models.CharField(max_length=200, null=True, blank=True)
    sha512 = models.CharField(max_length=200, null=True, blank=True)
    filename = models.CharField(max_length=200, null=True, blank=True)
    
    _translations = dict(Prov._translations.items() + {'http://purl.org/dc/terms/format': ("format", str),
                                                      'http://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions#sha512': ("sha512", str),
                                                      'http://www.incf.org/ns/nidash/nidm#filename': ("filename", str)}.items())
            

class ProvImage(ProvEntity, CollectionPart):
    _translations = dict(Prov._translations.items() + {'http://www.w3.org/ns/prov#atLocation': ("file", str)}.items())
  
    file = models.FileField(upload_to='hash_filestore', null=True, blank=True)


# ## Model Fitting
    
class ContrastWeights(ProvEntity, CollectionPart):
    _translations = dict(Prov._translations.items() + {'http://www.incf.org/ns/nidash/nidm#statisticType': ("statisticType", str),
                                                       'http://www.incf.org/ns/nidash/nidm#contrastName': ("contrastName", str),
                                                       'http://www.w3.org/ns/prov#value': ("value", str)}.items())
    _statisticsType_choices = [("http://www.incf.org/ns/nidash/nidm#ZStatistic", "Z"),
                               ("http://www.incf.org/ns/nidash/nidm#Statistic", "Other"),
                               ("http://www.incf.org/ns/nidash/nidm#FStatistic", "F"),
                               ("http://www.incf.org/ns/nidash/nidm#TStatistic", "F")]
    statisticType = models.CharField(max_length=200, choices=_statisticsType_choices, null=True, blank=True)
    contrastName = models.CharField(max_length=200, null=True, blank=True)
    value = models.CharField(max_length=200, null=True, blank=True)


class Data(ProvEntity, CollectionPart):
    _translations = dict(Prov._translations.items() + {'http://www.incf.org/ns/nidash/nidm#grandMeanScaling': ('grandMeanScaling', bool),
                                                       'http://www.incf.org/ns/nidash/nidm#targetIntensity': ('targetIntensity', float)}.items())
    grandMeanScaling = models.NullBooleanField(default=None, null=True, blank=True)
    targetIntensity = models.FloatField(null=True, blank=True)
    

class DesignMatrix(ProvEntity, CollectionPart):
    _translations = dict(Prov._translations.items() + {'http://www.w3.org/ns/prov#atLocation': ("file", file),
                                                       ('http://www.incf.org/ns/nidash/nidm#visualisation', 'Image'): ("image", ProvImage)}.items())
    image = models.OneToOneField(ProvImage, null=True, blank=True)
    file = models.FileField(upload_to='hash_filestore', null=True, blank=True)
    
    
class NoiseModel(ProvEntity, CollectionPart):
    _translations = dict(Prov._translations.items() + {'http://www.incf.org/ns/nidash/nidm#noiseVarianceHomogeneous': ('noiseVarianceHomogeneous', bool),
                                                       'http://www.incf.org/ns/nidash/nidm#varianceSpatialModel': ('varianceSpatialModel', str),
                                                       'http://www.incf.org/ns/nidash/nidm#dependenceSpatialModel': ('dependenceSpatialModel', str),
                                                       'http://www.incf.org/ns/nidash/nidm#hasNoiseDependence': ('hasNoiseDependence', str),
                                                       'http://www.incf.org/ns/nidash/nidm#hasNoiseDistribution': ('hasNoiseDistribution', str)}.items())
    
    _dependenceSpatialModel_choices = [("http://www.incf.org/ns/nidash/nidm#SpatiallyLocalModel", "Spatiakky Local"),
                                       ("http://www.incf.org/ns/nidash/nidm#SpatialModel", "Spatial"),
                                       ("http://www.incf.org/ns/nidash/nidm#SpatiallyRegularizedModel", "SpatiallyRegularized"),
                                       ("http://www.incf.org/ns/nidash/nidm#SpatiallyGlobalModel", "Spatially Global")]
    dependenceSpatialModel = models.CharField(max_length=200, choices=_dependenceSpatialModel_choices, null=True, blank=True)
    _hasNoiseDistribution_choices = [("fsl:NonParametricSymmetricDistribution", "Non-Parametric Symmetric"),
                                     ("http://www.incf.org/ns/nidash/nidm#GaussianDistribution", "Gaussian"),
                                     ("http://www.incf.org/ns/nidash/nidm#NoiseDistribution", "Noise"),
                                     ("http://www.incf.org/ns/nidash/nidm#PoissonDistribution", "Poisson"),
                                     ("fsl:BinomialDistribution", "Binomial"),
                                     ("http://www.incf.org/ns/nidash/nidm#NonParametricDistribution", "Non-Parametric")]
    hasNoiseDistribution = models.CharField(max_length=200, choices=_hasNoiseDistribution_choices, null=True, blank=True)
    _hasNoiseDependence_choices = [("http://www.incf.org/ns/nidash/nidm#ArbitrarilyCorrelatedNoise", "Arbitrarily Correlated"),
                                   ("http://www.incf.org/ns/nidash/nidm#ExchangeableNoise", "Exchangable"),
                                   ("http://www.incf.org/ns/nidash/nidm#SeriallyCorrelatedNoise", "Serially Correlated"),
                                   ("http://www.incf.org/ns/nidash/nidm#CompoundSymmetricNoise", "Compound Symmetric"),
                                   ("http://www.incf.org/ns/nidash/nidm#IndependentNoise", "Independent")]
    hasNoiseDependence = models.CharField(max_length=200, choices=_hasNoiseDependence_choices, null=True, blank=True)
    noiseVarianceHomogeneous = models.NullBooleanField(default=None, null=True, blank=True)
    _varianceSpatialModel_choices = [("http://www.incf.org/ns/nidash/nidm#SpatiallyLocalModel", "Spatially Local"),
                                     ("http://www.incf.org/ns/nidash/nidm#SpatialModel", "Spatial"),
                                     ("http://www.incf.org/ns/nidash/nidm#SpatiallyRegularizedModel", "Spatially Regularized"),
                                     ("http://www.incf.org/ns/nidash/nidm#SpatiallyGlobalModel", "Spatially Global")]
    varianceSpatialModel = models.CharField(max_length=200, choices=_varianceSpatialModel_choices, null=True, blank=True)
    
    
class ModelParametersEstimation(ProvActivity, CollectionPart):
    _translations = dict(Prov._translations.items() + {('http://www.w3.org/ns/prov#used', 'Data'): ("data", Data), 
                                                       'http://www.incf.org/ns/nidash/nidm#withEstimationMethod': ("withEstimationMethod", str),
                                                       ('http://www.w3.org/ns/prov#used', 'DesignMatrix'): ("designMatrix", DesignMatrix),
                                                       ('http://www.w3.org/ns/prov#used', 'NoiseModel'): ("noiseModel", NoiseModel)}.items())
    
    _withEstimation_method_choices = [("http://www.incf.org/ns/nidash/nidm#WeightedLeastSquares", "WeightedLeastSquares"),
                                      ("http://www.incf.org/ns/nidash/nidm#OrdinaryLeastSquares", "OrdinaryLeastSquares"),
                                      ("http://www.incf.org/ns/nidash/nidm#GeneralizedLeastSquares", "GeneralizedLeastSquares"),
                                      ("http://www.incf.org/ns/nidash/nidm#EstimationMethod", "EstimatedMethod"),
                                      ("http://www.incf.org/ns/nidash/nidm#RobustIterativelyReweighedLeastSquares", "RobustIterativelyReweighedLeastSquares")]
    withEstimationMethod = models.CharField(max_length=200, choices=_withEstimation_method_choices, null=True, blank=True)
    designMatrix = models.ForeignKey(DesignMatrix, null=True, blank=True)
    data = models.ForeignKey(Data, null=True, blank=True)
    noiseModel = models.ForeignKey(NoiseModel, null=True, blank=True)
    
    
class MaskMap(Image, ProvEntity):
    _translations = dict(Prov._translations.items() + {'http://www.w3.org/2000/01/rdf-schema#label': ('name', str),
                                                       'http://www.w3.org/ns/prov#atLocation': ("file", file), 
                                                       ('http://www.incf.org/ns/nidash/nidm#atCoordinateSpace', 'CoordinateSpace'): ("atCoordinateSpace", CoordinateSpace),
                                                       ('http://www.incf.org/ns/nidash/nidm#inCoordinateSpace', 'CoordinateSpace'): ("inCoordinateSpace", CoordinateSpace),
                                                       ('http://www.w3.org/ns/prov#wasDerivedFrom', 'Map'): ("map", Map),
                                                       'http://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions#sha512': ("sha512", str),
                                                       ('http://www.w3.org/ns/prov#wasGeneratedBy', 'ModelParametersEstimation'): ("modelParametersEstimation", ModelParametersEstimation)}.items())
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    hasMapHeader = models.CharField(max_length=200, null=True, blank=True)
    modelParametersEstimation = models.OneToOneField(ModelParametersEstimation, null=True, blank=True)
    map = models.OneToOneField(Map, null=True, blank=True)
    
    
class ParameterEstimateMap(Image, ProvEntity):
    _translations = dict(Prov._translations.items() + {'http://www.w3.org/2000/01/rdf-schema#label': ('name', str),
                                                       'http://www.w3.org/ns/prov#atLocation': ("file", file), 
                                                       ('http://www.incf.org/ns/nidash/nidm#atCoordinateSpace', 'CoordinateSpace'): ("atCoordinateSpace", CoordinateSpace),
                                                       ('http://www.w3.org/ns/prov#wasGeneratedBy', 'ModelParametersEstimation'): ("modelParametersEstimation", ModelParametersEstimation),
                                                       ('http://www.w3.org/ns/prov#wasDerivedFrom', 'Map'): ("map", Map)}.items())
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    hasMapHeader = models.CharField(max_length=200, null=True, blank=True)
    modelParametersEstimation = models.ForeignKey(ModelParametersEstimation, null=True, blank=True)
    map = models.OneToOneField(Map, null=True, blank=True)
    
    
class ResidualMeanSquaresMap(Image, ProvEntity):
    _translations = dict(Prov._translations.items() + {'http://www.w3.org/2000/01/rdf-schema#label': ('name', str),
                                                       'http://www.w3.org/ns/prov#atLocation': ("file", file), 
                                                       ('http://www.incf.org/ns/nidash/nidm#atCoordinateSpace', 'CoordinateSpace'): ("atCoordinateSpace", CoordinateSpace),
                                                       ('http://www.incf.org/ns/nidash/nidm#inCoordinateSpace', 'CoordinateSpace'): ("inCoordinateSpace", CoordinateSpace),
                                                       ('http://www.w3.org/ns/prov#wasDerivedFrom', 'Map'): ("map", Map), 
                                                       'http://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions#sha512': ("sha512", str),
                                                       ('http://www.w3.org/ns/prov#wasGeneratedBy', 'ModelParametersEstimation'): ("modelParametersEstimation", ModelParametersEstimation),
                                                       ('http://www.w3.org/ns/prov#used', 'DesignMatrix'): ('designMatrix', DesignMatrix)}.items())
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    modelParametersEstimation = models.OneToOneField(ModelParametersEstimation, null=True, blank=True)
    designMatrix = models.ForeignKey(DesignMatrix, null=True, blank=True)
    sha512 = models.CharField(max_length=200, null=True, blank=True)
    map = models.OneToOneField(Map, null=True, blank=True)
    

class ContrastEstimation(ProvActivity, CollectionPart):
    _translations = dict(Prov._translations.items() + {('http://www.w3.org/ns/prov#used', 'ParameterEstimateMap'): ("parameterEstimateMap", ParameterEstimateMap),
                                                       ('http://www.w3.org/ns/prov#used', 'ResidualMeanSquaresMap'): ("residualMeanSquaresMap", ResidualMeanSquaresMap),
                                                       ('http://www.w3.org/ns/prov#used', 'MaskMap'): ("maskMap", MaskMap),
                                                       ('http://www.w3.org/ns/prov#used', 'ContrastWeights'): ("contrastWeights", ContrastWeights),
                                                       ('http://www.w3.org/ns/prov#used', 'DesignMatrix'): ('designMatrix', DesignMatrix)}.items())
    parameterEstimateMap = models.ManyToManyField(ParameterEstimateMap, null=True, blank=True)
    residualMeanSquaresMap = models.ForeignKey(ResidualMeanSquaresMap, null=True, blank=True)
    maskMap = models.ForeignKey(MaskMap, null=True, blank=True)
    contrastWeights = models.ForeignKey(ContrastWeights, null=True, blank=True)
    designMatrix = models.ForeignKey(DesignMatrix, null=True, blank=True)


class ContrastMap(Image, ProvEntity):
    contrastName = models.CharField(max_length=200, null=True, blank=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    contrastEstimation = models.ForeignKey(ContrastEstimation, null=True, blank=True)
    sha512 = models.CharField(max_length=200, null=True, blank=True)
    map = models.OneToOneField(Map, null=True, blank=True)
    
class StatisticMap(Image, ProvEntity):
    nidm_identifier = "nidm:StatisticMap"
    _translations = OrderedDict(Prov._translations.items() + {'http://www.w3.org/2000/01/rdf-schema#label': ('name', str),
                                                              'http://www.incf.org/ns/nidash/nidm#contrastName': ('contrastName', str),
                                                              'http://www.incf.org/ns/nidash/nidm#errorDegreesOfFreedom': ("errorDegreesOfFreedom", float),
                                                       'http://www.w3.org/ns/prov#atLocation': ("file", file),
                                                        ('http://www.incf.org/ns/nidash/nidm#atCoordinateSpace', 'CoordinateSpace'): ("atCoordinateSpace", CoordinateSpace),
                                                        ('http://www.incf.org/ns/nidash/nidm#inCoordinateSpace', 'CoordinateSpace'): ("inCoordinateSpace", CoordinateSpace),
                                                        ('http://www.w3.org/ns/prov#wasGeneratedBy', 'ContrastEstimation'): ("contrastEstimation", ContrastEstimation),
                                                        ('http://www.w3.org/ns/prov#wasDerivedFrom', 'Map'): ("map", Map),
                                                       'http://www.incf.org/ns/nidash/nidm#statisticType': ("statisticType", str),
                                                       'http://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions#sha512': ("sha512", str),
                                                       'http://www.incf.org/ns/nidash/nidm#effectDegreesOfFreedom': ("effectDegreesOfFreedom", float)}.items())
    errorDegreesOfFreedom = models.FloatField(null=True, blank=True)
    effectDegreesOfFreedom = models.FloatField(null=True, blank=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    contrastEstimation = models.ForeignKey(ContrastEstimation, null=True, blank=True)
    sha512 = models.CharField(max_length=200, null=True, blank=True)
    contrastName = models.CharField(max_length=200, null=True, blank=True)
    map = models.OneToOneField(Map, null=True, blank=True)
    
    Z = 'Z'
    T = 'T'
    F = 'F'
    X2 = 'X2'
    P = 'P'
    OTHER = 'Other'
    MAP_TYPE_CHOICES = (
        (T, 'T map'),
        (Z, 'Z map'),
        (F, 'F map'),
        (X2, 'Chi squared map'),
        (P, 'P map (given null hypothesis)'),
        (OTHER, 'Other'),
    )
    statisticType = models.CharField(help_text=("Type of statistic that is the basis of the inference"), verbose_name="Map type",
                                                       max_length=200, null=False, blank=False, choices=MAP_TYPE_CHOICES)
    statistic_parameters = models.FloatField(help_text="Parameters of the null distribution of the test statisic, typically degrees of freedom (should be clear from the test statistic what these are).", null=True, verbose_name="Statistic parameters", blank=True)
    smoothness_fwhm = models.FloatField(help_text="Noise smoothness for statistical inference; this is the estimated smoothness used with Random Field Theory or a simulation-based inference method.", verbose_name="Smoothness FWHM", null=True, blank=True)
    contrast_definition = models.CharField(help_text="Exactly what terms are subtracted from what? Define these in terms of task or stimulus conditions (e.g., 'one-back task with objects versus zero-back task with objects') instead of underlying psychological concepts (e.g., 'working memory').", verbose_name="Contrast definition", max_length=200, null=True, blank=True)
    contrast_definition_cogatlas = models.CharField(help_text="Link to <a href='http://www.cognitiveatlas.org/'>Cognitive Atlas</a> definition of this contrast", verbose_name="Cognitive Atlas definition", max_length=200, null=True, blank=True)
    
    def get_estimation_method(self):
        estimation_method = self.contrastEstimation.residualMeanSquaresMap.modelParametersEstimation.withEstimationMethod.split("#")[-1]
        return estimation_method

class ContrastStandardErrorMap(Image, ProvEntity):
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    contrastEstimation = models.OneToOneField(ContrastEstimation, null=True, blank=True)
    sha512 = models.CharField(max_length=200, null=True, blank=True)
    map = models.OneToOneField(Map, null=True, blank=True)
    
    
# ## Inference

class ReselsPerVoxelMap(Image, ProvEntity):
    _translations = OrderedDict(Prov._translations.items() + {('http://www.w3.org/ns/prov#wasDerivedFrom', 'Map'): ('map', Map), 
                                                              ('http://www.incf.org/ns/nidash/nidm#atCoordinateSpace', 'CoordinateSpace'): ('atCoordinateSpace', CoordinateSpace),
                                                              'http://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions#sha512': ('sha512', str), 
                                                              'http://www.w3.org/ns/prov#atLocation': ('file', file), 
                                                              ('http://www.w3.org/ns/prov#wasGeneratedBy', 'ModelParametersEstimation'): ('modelParametersEstimation', ModelParametersEstimation)}.items())
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    modelParametersEstimation = models.OneToOneField(ModelParametersEstimation, null=True, blank=True)
    sha512 = models.CharField(max_length=200, null=True, blank=True)
    map = models.OneToOneField(Map, null=True, blank=True)

class ExtentThreshold(ProvEntity, CollectionPart):
    userSpecifiedThresholdType = models.CharField(max_length=200, null=True, blank=True)
    pValueUncorrected = models.FloatField(null=True, blank=True)
    pValueFWER = models.FloatField(null=True, blank=True)
    qValueFDR = models.FloatField(null=True, blank=True)
    clusterSizeInVoxels = models.IntegerField(null=True, blank=True)
    clusterSizeInResels = models.FloatField(null=True, blank=True)
    

class HeightThreshold(ProvEntity, CollectionPart):
    value = models.FloatField(null=True, blank=True)
    userSpecifiedThresholdType = models.CharField(max_length=200, null=True, blank=True)
    pValueUncorrected = models.FloatField(null=True, blank=True)
    qValueFDR = models.FloatField(null=True, blank=True)
    pValueFWER = models.FloatField(null=True, blank=True)

class Inference(ProvActivity, CollectionPart):
    _translations = OrderedDict(Prov._translations.items() + {'http://www.incf.org/ns/nidash/nidm#hasAlternativeHypothesis': ('hasAlternativeHypothesis', str), 
                                                              ('http://www.w3.org/ns/prov#used', 'ExtentThreshold'): ('extentThreshold', ExtentThreshold), 
                                                              ('http://www.w3.org/ns/prov#used', 'StatisticMap'): ('statisticMap', StatisticMap), 
                                                              ('http://www.w3.org/ns/prov#used', 'HeightThreshold'): ('heightThreshold', HeightThreshold), 
                                                              ('http://www.w3.org/ns/prov#used', 'MaskMap'): ('maskMap', MaskMap), 
                                                              ('http://www.w3.org/ns/prov#used', 'ReselsPerVoxelMap'): ('reselsPerVoxelMap', ReselsPerVoxelMap)}.items())
    alternativeHypothesis = models.CharField(max_length=200, null=True, blank=True)
    _hasAlternativeHypothesis_choices = [("http://www.incf.org/ns/nidash/nidm#TwoTailedTest", "Two Tailed"),
                                         ("http://www.incf.org/ns/nidash/nidm#OneTailedTest", "One Tailed")]
    hasAlternativeHypothesis = models.CharField(max_length=200, choices=_hasAlternativeHypothesis_choices, null=True, blank=True)
    contrastMap = models.ForeignKey(ContrastMap, null=True, blank=True)
    statisticMap = models.ForeignKey(StatisticMap, null=True, blank=True)
    heightThreshold = models.ForeignKey(HeightThreshold, null=True, blank=True)
    extentThreshold = models.ForeignKey(ExtentThreshold, null=True, blank=True)
    reselsPerVoxelMap = models.ForeignKey(ReselsPerVoxelMap, null=True, blank=True)
    maskMap = models.ForeignKey(MaskMap, null=True, blank=True)

    
class Coordinate(ProvEntity, CollectionPart):
    _translations = OrderedDict(Prov._translations.items() + {'http://www.incf.org/ns/nidash/nidm#coordinate3': ('coordinate3', float), 
                                                              'http://www.incf.org/ns/nidash/nidm#coordinate2': ('coordinate2', float), 
                                                              'http://www.incf.org/ns/nidash/nidm#coordinate1': ('coordinate1', float)}.items())
    coordinate3 = models.FloatField(null=True, blank=True)
    coordinate2 = models.FloatField(null=True, blank=True)
    coordinate1 = models.FloatField(null=True, blank=True)
    
    
class ClusterLabelMap(Image, ProvEntity):
    _translations = dict(Prov._translations.items() + {'http://www.w3.org/2000/01/rdf-schema#label': ('name', str),
                                                       'http://www.w3.org/ns/prov#atLocation': ("file", file),
                                                       ('http://www.w3.org/ns/prov#wasDerivedFrom', 'Map'): ("map", Map)}.items())
    map = models.OneToOneField(Map, null=True, blank=True)
    
    
class ExcursionSet(ProvEntity, CollectionPart):
    _translations = OrderedDict(Prov._translations.items() + {('http://www.w3.org/ns/prov#wasGeneratedBy', 'Inference'): ('inference', Inference), 
                                                              'http://www.incf.org/ns/nidash/nidm#pValue': ('pValue', float), 
                                                              ('http://www.incf.org/ns/nidash/nidm#inCoordinateSpace', 'CoordinateSpace'): ('inCoordinateSpace', CoordinateSpace), 
                                                              ('http://www.incf.org/ns/nidash/nidm#atCoordinateSpace', 'CoordinateSpace'): ('atCoordinateSpace', CoordinateSpace), 
                                                              'http://www.incf.org/ns/nidash/nidm#numberOfClusters': ('numberOfClusters', int),
                                                              ('http://www.incf.org/ns/nidash/nidm#visualisation', 'Image'): ('image', ProvImage),
                                                              ('http://www.incf.org/ns/nidash/nidm#hasClusterLabelsMap', 'ClusterLabelsMap'): ('hasClusterLabelsMap', ClusterLabelMap), 
                                                              'http://id.loc.gov/vocabulary/preservation/cryptographicHashFunctions#sha512': ('sha512', str), 
                                                              ('http://www.incf.org/ns/nidash/spm#hasMaximumIntensityProjection', 'Image'): ('hasMaximumIntensityProjection', Image)}.items())
    maximumIntensityProjection = models.FileField(upload_to='hash_filestore', null=True, blank=True)
    pValue = models.FloatField(null=True, blank=True)
    numberOfClusters = models.IntegerField(null=True, blank=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    inference = models.ForeignKey(Inference, null=True, blank=True)
    sha512 = models.CharField(max_length=200, null=True, blank=True)
    clusterLabelMap = models.ForeignKey(ClusterLabelMap, null=True, blank=True)
    image = models.OneToOneField(ProvImage, null=True, blank=True)
    underlayFile = models.FileField(upload_to='hash_filestore', null=True, blank=True)
    
    
class Cluster(ProvEntity, CollectionPart):
    _translations = OrderedDict(Prov._translations.items() + {'http://www.incf.org/ns/nidash/nidm#clusterLabelId': ('clusterLabelId',float), 
                                                              'http://www.incf.org/ns/nidash/nidm#qValueFDR': ('qValueFDR', float), 
                                                              'http://www.incf.org/ns/nidash/nidm#pValueUncorrected': ('pValueUncorrected', float),
                                                              'http://www.incf.org/ns/nidash/nidm#pValueFWER': ('pValueFWER', float), 
                                                              'http://www.incf.org/ns/nidash/spm#clusterSizeInResels': ('clusterSizeInResels', float), 
                                                              ('http://www.w3.org/ns/prov#wasDerivedFrom', 'ExcursionSet'): ('excursionSet', ExcursionSet), 
                                                              'http://www.incf.org/ns/nidash/nidm#clusterSizeInVoxels': ('clusterSizeInVoxels', int)}.items())
    qValueFDR = models.FloatField(null=True, blank=True)
    clusterLabelId = models.IntegerField(null=True, blank=True)
    pValueUncorrected = models.FloatField(null=True, blank=True)
    pValueFWER = models.FloatField(null=True, blank=True)
    excursionSet = models.ForeignKey(ExcursionSet, null=True, blank=True)
    clusterSizeInVoxels = models.IntegerField(null=True, blank=True)
    clusterSizeInResels = models.FloatField(null=True, blank=True)
    

class Peak(ProvEntity, CollectionPart):
    nidm_identifier = "nidm:Peak"
    _translations = OrderedDict(Prov._translations.items() + {'http://www.incf.org/ns/nidash/nidm#equivalentZStatistic': ('equivalentZStatistic', float),
                                                              'http://www.w3.org/ns/prov#value': ('value', float),
                                                              ('http://www.w3.org/ns/prov#wasDerivedFrom', 'Cluster'): ('cluster', Cluster),
                                                              'http://www.incf.org/ns/nidash/nidm#pValueFWER': ('pValueFWER', float), 
                                                              'http://www.incf.org/ns/nidash/nidm#qValueFDR': ('qValueFDR', float), 
                                                              'http://www.incf.org/ns/nidash/nidm#pValueUncorrected': ('pValueUncorrected', float), 
                                                              ('http://www.w3.org/ns/prov#atLocation', 'Coordinate'): ('coordinate', Coordinate)}.items())

    coordinate = models.OneToOneField(Coordinate)
    equivalentZStatistic = models.FloatField(null=True, blank=True)
    value = models.FloatField(null=True, blank=True)
    qValueFDR = models.FloatField(null=True, blank=True)
    pValueUncorrected = models.FloatField(null=True, blank=True)
    pValueFWER = models.FloatField(null=True, blank=True)
    cluster = models.ForeignKey(Cluster, null=True, blank=True)
    
    
class SearchSpaceMap(Image, ProvEntity):
    expectedNumberOfClusters = models.FloatField(null=True, blank=True)
    expectedNumberOfVoxelsPerCluster = models.FloatField(null=True, blank=True)
    reselSize = models.FloatField(null=True, blank=True)
    inference = models.ForeignKey(Inference, null=True, blank=True)
    smallestSignifClusterSizeInVoxelsFDR05 = models.IntegerField(null=True, blank=True)
    smallestSignifClusterSizeInVoxelsFWE05 = models.IntegerField(null=True, blank=True)
    heightCriticalThresholdFDR05 = models.FloatField(null=True, blank=True)
    heightCriticalThresholdFWE05 = models.FloatField(null=True, blank=True)
    searchVolumeInVoxels = models.IntegerField(null=True, blank=True)
    searchVolumeInUnits = models.FloatField(null=True, blank=True)
    noiseFWHMInVoxels = models.CharField(max_length=200, null=True, blank=True)
    noiseFWHMInUnits = models.CharField(max_length=200, null=True, blank=True)
    sha512 = models.CharField(max_length=200, null=True, blank=True)
    searchVolumeInResels = models.FloatField(null=True, blank=True)
    atCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    inCoordinateSpace = models.ForeignKey(CoordinateSpace, related_name='+', null=True, blank=True)
    randomFieldStationarity = models.NullBooleanField(default=None, null=True, blank=True)
    searchVolumeReselsGeometry = models.CharField(max_length=200, null=True, blank=True)
    map = models.OneToOneField(Map, null=True, blank=True)
    
