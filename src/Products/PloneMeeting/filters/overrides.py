# -*- coding: utf-8 -*-

from plone.outputfilters.filters.resolveuid_and_caption import ResolveUIDAndCaptionFilter


class PMResolveUIDAndCaptionFilter(ResolveUIDAndCaptionFilter):
    """Complete the transform to enable lazy loading for images."""

    def unknown_starttag(self, tag, attrs):
        if tag == 'img':
            attrs.append(('loading', 'lazy'))
        ResolveUIDAndCaptionFilter.unknown_starttag(self, tag, attrs)
