/* The jQuery here above will load a jQuery popup */

// prepare overlays for normal (non-ajax) pages
jQuery(function($){

    // Add or edit advice popup
    $('a.link-overlay-pm').prepOverlay({
       subtype: 'ajax',
   });

});

// prepare overlays in ajax frames
// this method is made to initialize overlays in the ajax-frame
// because they are not correctly initialized at page load

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

function initializePMOverlaysOnMeeting(){

jQuery(function($) {
// Adapt the link that will show a popup for confirming a transition
// to pass iStartNumber and lStartNumber that are global JS variables defined on the meeting_view
$('a.link-overlay-pm.transition-overlay').each(function(){
    $(this).attr('href',$(this).attr('href') + '&iStartNumber=' + iStartNumber + '&lStartNumber=' + lStartNumber);
    })
})
initializePMOverlays()

}
