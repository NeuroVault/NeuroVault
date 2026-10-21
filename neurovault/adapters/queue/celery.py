"""Background work through Celery."""


class CeleryTaskQueue:
    def process_item(self, item_id):
        from neurovault.adapters.tasks import process_map

        process_map.apply_async([item_id])
