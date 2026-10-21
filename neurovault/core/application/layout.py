"""Where map files live in the store (unchanged from the original layout)."""
import os


def collection_dir(collection_id):
    return os.path.join("images", str(collection_id))


def bundle_dir(collection_id, zip_ref):
    """A bundle's files sit next to its zip: images/<collection>/<zip name>/."""
    return os.path.join(collection_dir(collection_id), os.path.split(zip_ref)[-1].replace(".zip", ""))
