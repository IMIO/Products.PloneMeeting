/* In the documentby_line, remove the link to the creator... */
removeLinkOnByLine = function() {
    tagToHandle = $('#plone-document-byline a')[0];
    $(tagToHandle).replaceWith('<span>' + $(tagToHandle).html() + '</span>');
}

/* Disable some elements from the optionalAdvisers list box
   Actually we add 2 special values that are help messages related to delay-aware advisers,
   these shoul not be selectable. */
disableSomeOptionsFromOptionalAdvisers = function() {
    box = $('select#optionalAdvisers option');
    box.each(function() {
        var valuesToDisable = ['not_selectable_value_delay_aware_optional_advisers',
                               'not_selectable_value_non_delay_aware_optional_advisers'];

        if ($.inArray($(this).val(), valuesToDisable) >= 0) {
            $(this).attr("disabled", "disabled");
        }
    });
}

jQuery(document).ready(removeLinkOnByLine);
jQuery(document).ready(disableSomeOptionsFromOptionalAdvisers);
