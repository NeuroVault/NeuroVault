"""Use case: turn an uploaded file, archive or folder into images."""
from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch

from neurovault.core.domain import map_quality

from .bundles import NamedBytes
from .items import ImageFilesInput

ALLOWED_EXTENSIONS = [".nii", ".img", ".nii.gz"]


@dataclass
class IngestResult:
    item_ids: list = field(default_factory=list)
    bundle_id: int = None
    warnings: list = field(default_factory=list)


class UploadService:
    def __init__(self, item_service, bundle_service, workspace_factory):
        self.item_service = item_service
        self.bundle_service = bundle_service
        self.workspace_factory = workspace_factory

    def ingest(self, actor, collection_id, upload=None, folder_files=None, folder_paths=None):
        """Create one image per NIfTI volume in the upload.

        `upload` is a single file or an archive; `folder_files`/`folder_paths`
        recreate an uploaded directory. A `*.nidm.zip` becomes an NIDM bundle.
        Volumes that cannot be read are skipped with a warning; any other
        failure raises.
        """
        self.item_service.require_change(actor, collection_id)
        result = IngestResult()

        if upload is not None and fnmatch(upload.name, "*.nidm.zip"):
            prepared = self.bundle_service.prepare(collection_id, upload)
            result.bundle_id = self.bundle_service.ingest(
                actor, collection_id, prepared, description="NIDM Results", check_access=False
            )
            return result

        with self.workspace_factory() as ws:
            if upload is not None:
                if fnmatch(upload.name, "*.zip") or fnmatch(upload.name, "*.tar.gz"):
                    ws.extract(upload)
                else:
                    ws.write(upload)
            elif folder_files:
                ws.write_tree(folder_files, folder_paths)
            else:
                raise ValueError("No uploaded files found.")

            for label, path, atlas_xml in ws.collect(ALLOWED_EXTENSIONS):
                try:
                    result.item_ids.append(self._create(actor, collection_id, label, path, atlas_xml, ws))
                except Exception as e:
                    result.warnings.append(f"Skipping {label}: {str(e)}")
        return result

    def _create(self, actor, collection_id, label, path, atlas_xml, ws):
        try:
            base_name, volume = ws.squeezed_volume(path)
        except ValueError:
            raise ValueError(f"Skipping {label}: 4D file detected.")
        spaced_name = base_name.replace("_", " ").replace("-", " ")
        files = ImageFilesInput(file=NamedBytes(base_name + ".nii.gz", volume))
        if atlas_xml:
            with open(atlas_xml, "rb") as f:
                files.label_description_file = NamedBytes(base_name + ".xml", f.read())
            return self.item_service.add(
                actor, collection_id, "atlas", {"name": spaced_name}, files, check_access=False
            )
        return self.item_service.add(
            actor,
            collection_id,
            "statmap",
            {"name": spaced_name, "is_valid": False, "map_type": map_quality.map_type_from_filename(path)},
            files,
            check_access=False,
        )
