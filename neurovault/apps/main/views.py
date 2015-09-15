from django.shortcuts import render
from ..statmaps.models import Collection
from django.db.models.aggregates import Count

def index_view(request):
    recent_collections = Collection.objects.exclude(DOI__isnull=True).exclude(private=True).order_by('-doi_add_date')
    #this is faster than using annotate and count!
    recent_collections = [col for col in recent_collections if col.image_set.count() > 0][:10]
    
    context = {'recent_collections': recent_collections}
    return render(request, 'index.html.haml', context)