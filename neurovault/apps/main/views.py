from django.shortcuts import render
from ..statmaps.models import Collection
from django.db.models.aggregates import Count

def index_view(request):
    recent_collections = Collection.objects.annotate(num_submissions=Count('image')).filter(num_submissions__gt = 0).order_by('-add_date')[:5]
    context = {'recent_collections': recent_collections}
    return render(request, 'index.html.haml', context)