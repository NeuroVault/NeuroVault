from django.shortcuts import render
from ..statmaps.models import Collection
from django.db.models.aggregates import Count

def index_view(request):
    recent_collections = Collection.objects.exclude(DOI__isnull=True).exclude(private=True).order_by('-add_date')[:10]
    context = {'recent_collections': recent_collections}
    return render(request, 'index.html.haml', context)