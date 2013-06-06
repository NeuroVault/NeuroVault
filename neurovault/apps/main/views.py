from django.shortcuts import render
from ..statmaps.models import Collection

def index_view(request):
    recent_studies = Collection.objects.all().order_by('-add_date')[:5]
    context = {'recent_studies': recent_studies}
    return render(request, 'index.html', context)