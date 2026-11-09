from django.apps import AppConfig


class PersistenceConfig(AppConfig):
    """ORM models and migrations. The label stays "statmaps" so table names,
    content types, permissions and the migration history are unchanged."""

    name = "neurovault.adapters.persistence"
    label = "statmaps"
    verbose_name = "NeuroVault data"
