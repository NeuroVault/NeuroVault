"""Rules for NIDM-Results bundles."""
import os
import re


def bundle_name(zip_filename, existing_count, replacing=False):
    """Name of a bundle uploaded as `zip_filename`.

    `existing_count` is how many bundles in the collection already start with
    the same base name; the bundle being replaced, if any, does not count.
    """
    base = os.path.split(zip_filename)[-1].replace(".nidm.zip", "")
    if replacing and existing_count != 0:
        existing_count -= 1
    if existing_count == 0:
        return base + ".nidm"
    return "{0}_{1}.nidm".format(base, existing_count)


def base_name(zip_filename):
    return os.path.split(zip_filename)[-1].replace(".nidm.zip", "")


def rewrite_ttl_locations(ttl_content, map_filename, public_prefix):
    """Point the TTL's prov:atLocation of `map_filename` at `public_prefix`."""
    ttl_regx = re.compile(
        r"(prov:atLocation\ \")(file:\/.*\/)?(" + map_filename + r')("\^\^xsd\:anyURI\ \;)'
    )
    hdr, urlprefix, _, _ = re.search(ttl_regx, ttl_content).groups()
    if not urlprefix:
        urlprefix = ""
    return ttl_content.replace(hdr + urlprefix, hdr + public_prefix)


def fix_spm12_ttl(ttl):
    """Earlier SPM12 exports wrote an invalid property name."""
    return ttl.replace("nidm_NoiseModel", "nidm:NoiseModel")
