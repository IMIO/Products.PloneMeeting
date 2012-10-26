/* In the documentby_line, remove the link to the creator... */
removeLinkOnByLine = function() {
    tagToHandle = $('#plone-document-byline a')[0];
    $(tagToHandle).replaceWith('<span>' + $(tagToHandle).html() + '</span>');
}

jQuery(document).ready(removeLinkOnByLine)

