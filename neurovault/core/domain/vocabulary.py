"""Controlled vocabularies of the NeuroVault domain.

The persistence models and forms take their choices from here, so each
vocabulary has one definition.
"""

# Map types
T = "T"
Z = "Z"
F = "F"
X2 = "X2"
P = "P"
IP = "IP"
M = "M"
U = "U"
R = "R"
Pa = "Pa"
A = "A"
V = "V"
OTHER = "Other"

MAP_TYPE_CHOICES = (
    (T, "T map"),
    (Z, "Z map"),
    (F, "F map"),
    (X2, "Chi squared map"),
    (P, "P map (given null hypothesis)"),
    (IP, '1-P map ("inverted" probability)'),
    (M, "multivariate-beta map"),
    (U, "univariate-beta map"),
    (R, "ROI/mask"),
    (Pa, "parcellation"),
    (A, "anatomical"),
    (V, "variance"),
    (OTHER, "other"),
)

# Analysis levels
SINGLE_SUBJECT = "S"
GROUP = "G"
META_ANALYSIS = "M"

ANALYSIS_LEVEL_CHOICES = (
    (SINGLE_SUBJECT, "single-subject"),
    (GROUP, "group"),
    (META_ANALYSIS, "meta-analysis"),
    (OTHER, "other"),
)

# Acquisition modalities
fMRI_BOLD = "fMRI-BOLD"
MODALITY_CHOICES = (
    (fMRI_BOLD, "fMRI-BOLD"),
    ("fMRI-CBF", "fMRI-CBF"),
    ("fMRI-CBV", "fMRI-CBV"),
    ("Diffusion MRI", "Diffusion MRI"),
    ("Structural MRI", "Structural MRI"),
    ("PET FDG", "PET FDG"),
    ("PET [15O]-water", "PET [15O]-water"),
    ("PET other", "PET other"),
    ("MEG", "MEG"),
    ("EEG", "EEG"),
    ("Other", "Other"),
)

# Target template spaces
POSSIBLE_TEMPLATES = {
    "GenericMNI": {
        "name": "Human (Generic/Unknown MNI)",
        "species": "homo sapiens",
        "pycortex_enabled": True,
        "image_search_enabled": True,
        "mask": "MNI152_T1_2mm_brain_mask.nii.gz",
    },
    "Dorr2008": {
        "name": "Mouse (Dorr 2008 space)",
        "species": "mus musculus",
        "pycortex_enabled": False,
        "image_search_enabled": False,
        "mask": None,
    },
    "NMT": {
        "name": "Rhesus - macacca mulatta (NMT)",
        "species": "macaca mulatta",
        "pycortex_enabled": False,
        "image_search_enabled": False,
        "mask": None,
    },
    "MNI152NLin2009cAsym": {
        "name": "Human (MNI152 NLin 2009c Asym)",
        "species": "homo sapiens",
        "pycortex_enabled": True,
        "image_search_enabled": True,
        "mask": None,
    },
}
DEFAULT_TEMPLATE = "GenericMNI"
SURFACE_PROJECTION_TEMPLATES = ("GenericMNI", "MNI152NLin2009cAsym")


def target_template_choices():
    return [(key, value["name"]) for key, value in POSSIBLE_TEMPLATES.items()]


def species_for(template=DEFAULT_TEMPLATE):
    return POSSIBLE_TEMPLATES[template]["species"]


def pycortex_compatible(template=DEFAULT_TEMPLATE):
    return POSSIBLE_TEMPLATES[template]["pycortex_enabled"]


def search_compatible(template=DEFAULT_TEMPLATE):
    return POSSIBLE_TEMPLATES[template]["image_search_enabled"]


COMMUNITIES = {
    "developmental": {"short_desc": "Developmental Neuroscience"},
    "nutrition": {"short_desc": "Nutrition Neuroscience"},
}
