from django.core.urlresolvers import reverse
from django.db.models.aggregates import Count
from django.shortcuts import render, get_object_or_404

from neurovault.apps.statmaps.models import Community
from ..statmaps.models import Collection


def index_view(request):
    recent_collections = Collection.objects.exclude(DOI__isnull=True).exclude(private=True).order_by('-doi_add_date')
    #this is faster than using annotate and count!
    recent_collections = [col for col in recent_collections if col.basecollectionitem_set.count() > 0][:10]
    
    context = {'recent_collections': recent_collections,
               'query_explanation': "Recently added collections of images from published papers",
               'tagline': "A public repository of unthresholded statistical maps, <br />"
                          "parcellations, and atlases of the brain",
               'what_is_it': "A place where researchers can publicly store and share unthresholded statistical maps, parcellations, and atlases produced by MRI and PET studies."}

    return render(request, 'index.html', context)


def community_view(request, community_label):
    community = get_object_or_404(Community, label=community_label)

    recent_collections = community.collections.exclude(DOI__isnull=True).exclude(
        private=True).order_by('-doi_add_date')
    # this is faster than using annotate and count!
    recent_collections = [col for col in recent_collections if col.basecollectionitem_set.count() > 0][:10]

    context = {'recent_collections': recent_collections,
               'query_explanation': "Recently added collections of images from the %s Community"%community.short_desc,
               'tagline': "A public repository of unthresholded statistical maps, <br />"
                          "parcellations, and atlases of the brain <br />"
                          "from the %s Community"%community.short_desc,
               'what_is_it': "A place where %s researchers can publicly store and share unthresholded statistical maps, parcellations, and atlases produced by MRI and PET studies."%community.short_desc,
               'name_subscript': community.label,
               'name_subscript_url': reverse('view_community', kwargs={'community_label': community_label})}
    return render(request, 'index.html', context)

