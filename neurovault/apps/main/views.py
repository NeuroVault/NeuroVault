from django.shortcuts import render
from ..statmaps.models import Collection

def index_view(request):
    recent_collections = Collection.objects.all().order_by('-add_date')[:5]
    context = {'recent_collections': recent_collections}
    return render(request, 'index.html.haml', context)