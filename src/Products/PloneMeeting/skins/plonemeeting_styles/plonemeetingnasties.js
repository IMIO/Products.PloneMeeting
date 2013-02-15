/* In the documentby_line, remove the link to the creator... */
removeLinkOnByLine = function() {
    tagToHandle = $('#plone-document-byline a')[0];
    $(tagToHandle).replaceWith('<span>' + $(tagToHandle).html() + '</span>');
}

/* while using the default search @@search, remove the link to author */
function removeLinkOnByLineOnSearch(){
jQuery(function($) {
$('.documentAuthor a').each(function(){
    $(this).replaceWith('<span>' + $(this).html() + '</span>');
    })
})
}
removeLinkOnByLineOnSearch()
