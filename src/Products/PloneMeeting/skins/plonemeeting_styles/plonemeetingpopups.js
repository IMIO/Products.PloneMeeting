/* The jQuery here above will load a jQuery popup */

// prepare overlays for normal (non-ajax) pages
// like meetingitem_view or overlays that you can raise from the portlet_plonemeeting
jQuery(function($){

    // Add or edit advice popup
    $('a.link-overlay-pm').prepOverlay({
       subtype: 'ajax',
   });

});

// prepare overlays in ajax frames
// this method is made to initialize overlays in the ajax-frame
// because they are not correctly initialized at page load
// How does it work?  We add a handler "onmouseover" the produced div
// containing the ajax-frame that only appear when the ajax-frame is loaded
// "onmouseover" we initialize the overlays than remove the "onmouseover" event
// so overlays are only initialized once...

function initializePMOverlays(){
jQuery(function($) {
  // Add advice popup
  $('a.link-overlay-pm.advice-overlay').prepOverlay({
     subtype: 'ajax',
  });
});
jQuery(function($) {
  // Add advice popup
  $('a.link-overlay-pm.transition-overlay').prepOverlay({
     subtype: 'ajax',
  });
});
// as this method is called on the onmousover event of the ajax-frame
// remove the event after first call to avoid it being called more than once
$('div.ajax-listitems-frame').each(function(){
    $(this).removeAttr('onmouseover');
    })
}

// When on a meething view, we have to handle some more parameters to keep on wich page we are
// Adapt the link that will show a popup for confirming a transition
// to pass iStartNumber and lStartNumber that are global JS variables defined on the meeting_view
function initializePMOverlaysOnMeeting(){
jQuery(function($) {
$('a.link-overlay-pm.transition-overlay').each(function(){
    $(this).attr('href',$(this).attr('href') + '&iStartNumber=' + iStartNumber + '&lStartNumber=' + lStartNumber);
    })
})
initializePMOverlays()
}
