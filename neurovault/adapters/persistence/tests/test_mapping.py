"""The domain's field groups map every column of the persistence models, and
only those (columns the persistence layer owns are listed explicitly)."""
from django.test import SimpleTestCase

from neurovault.adapters.persistence import models as orm
from neurovault.core.domain import collection as dc
from neurovault.core.domain.items import _names, column_names

ITEM_OWNED = {"id", "kind", "source_bundle_id", "add_date", "modify_date"}
COLLECTION_OWNED = {"id", "owner_id", "add_date", "modify_date"}


def columns(model):
    return {f.attname for f in model._meta.concrete_fields}


class ColumnCoverage(SimpleTestCase):
    def test_item_columns(self):
        mapped = column_names("statmap") | column_names("atlas")
        self.assertEqual(columns(orm.Item) - ITEM_OWNED, mapped)

    def test_collection_columns(self):
        mapped = set(dc.SCALARS).union(*(_names(cls) for cls in dc.METADATA_GROUPS.values()))
        self.assertEqual(columns(orm.Collection) - COLLECTION_OWNED, mapped)
