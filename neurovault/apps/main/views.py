from django.shortcuts import render
from ..statmaps.models import Image

def index_view(request):
    recent_images = Image.objects.all().order_by('-add_date')[:5]
    context = {'recent_images': recent_images}
    return render(request, 'index.html.haml', context)