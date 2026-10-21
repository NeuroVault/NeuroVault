"""Use cases for image-based meta-analyses."""
from __future__ import annotations

import os
import shutil
import tempfile

from neurovault.domain import metaanalysis as dm
from neurovault.domain.errors import PermissionDenied

from ..ports import MetaAnalysisInput
from .bundles import NamedBytes
from .items import ImageFilesInput


class MetaanalysisService:
    def __init__(self, metaanalyses, items, collection_service, item_service, store, engine, uow):
        self.metaanalyses = metaanalyses
        self.items = items
        self.collection_service = collection_service
        self.item_service = item_service
        self.store = store
        self.engine = engine
        self.uow = uow

    def get(self, metaanalysis_id):
        return self.metaanalyses.get(metaanalysis_id)

    def save(self, actor, metaanalysis_id, name, description):
        """Create (id None) or rename a meta-analysis; a new one becomes active."""
        if metaanalysis_id is None:
            m = dm.Metaanalysis(id=None, owner_id=actor.user_id, name=name, description=description)
        else:
            m = self.metaanalyses.get(metaanalysis_id)
            if m.owner_id != actor.user_id:
                raise PermissionDenied("not your meta-analysis")
            m.name, m.description = name, description
        return self._save(m)

    def _save(self, m):
        """Saving an active meta-analysis deactivates the owner's others."""
        with self.uow.atomic():
            if m.status == dm.ACTIVE:
                for other in self.metaanalyses.active_for(m.owner_id):
                    if other.id != m.id:
                        other.status = dm.INACTIVE
                        self.metaanalyses.save(other)
            if m.id is None:
                return self.metaanalyses.add(m)
            self.metaanalyses.save(m)
            return m.id

    def activate(self, actor, metaanalysis_id):
        m = self.metaanalyses.get(metaanalysis_id)
        if m.owner_id != actor.user_id or m.is_completed:
            raise PermissionDenied("cannot activate")
        m.status = dm.ACTIVE
        self._save(m)

    def active_for(self, user_id):
        active = self.metaanalyses.active_for(user_id)
        return active[0] if active else None

    def toggle_map(self, actor, item_id):
        """Add the map to the actor's active meta-analysis, or remove it; returns 'in'/'out'."""
        m = self.metaanalyses.active_for(actor.user_id)[0]
        if item_id in m.map_ids:
            m.map_ids = m.map_ids - {item_id}
            status = "out"
        else:
            m.map_ids = m.map_ids | {item_id}
            status = "in"
        self.metaanalyses.save(m)
        return status

    def finalize(self, actor, metaanalysis_id, absolute_url):
        """Run the meta-analysis into a new collection; returns its id."""
        m = self.metaanalyses.get(metaanalysis_id)
        if m.owner_id != actor.user_id or m.is_completed:
            raise PermissionDenied("cannot finalize")

        collection_id = self.collection_service.save(
            actor,
            None,
            {"name": f"Metaanalysis {m.id}: {m.name}", "full_dataset_url": absolute_url},
            owner_id=m.owner_id,
        )
        inputs = []
        for item_id in sorted(m.map_ids):
            item = self.items.get(item_id)
            with self.store.local_path(item.files.file) as path:
                inputs.append(MetaAnalysisInput(path, item.stats.map_type, item.stats.number_of_subjects))
        result = self.engine.run(inputs)
        self.collection_service.save(
            actor, collection_id, {"description": dm.description_for(result.n_maps, result.weighted)}
        )

        outputs = [
            ("FWE corrected Z map", "z", "z_fwe_corr.nii.gz", "Z", None),
            ("FWE corrected P map", "p", "p_fwe_corr.nii.gz", "P", -1),
        ]
        if result.weighted:
            outputs.append(("FFX map", "ffx_stat", "ffx_stat.nii.gz", "Other", None))
        tmp_dir = tempfile.mkdtemp()
        try:
            for name, key, filename, map_type, n_subjects in outputs:
                path = os.path.join(tmp_dir, filename)
                result.images[key].to_filename(path)
                with open(path, "rb") as f:
                    upload = NamedBytes(filename, f.read())
                changes = {
                    "name": name, "description": "", "modality": "Other", "map_type": map_type,
                    "analysis_level": "M", "target_template_image": "GenericMNI",
                }
                if n_subjects is not None:
                    changes["number_of_subjects"] = n_subjects
                self.item_service.add(actor, collection_id, "statmap", changes,
                                      ImageFilesInput(file=upload), check_access=False)
        finally:
            shutil.rmtree(tmp_dir)

        m.output_collection_id = collection_id
        m.status = dm.COMPLETED
        self._save(m)
        return collection_id
