from django.utils import timezone


class DjangoClock:
    def now(self):
        return timezone.now()
