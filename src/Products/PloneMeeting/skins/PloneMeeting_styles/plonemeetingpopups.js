/* The jQuery here above will load a jQuery popup */

jQuery(function($){

    // Add or edit advice popup
    $('a.link-overlay').prepOverlay({
       subtype: 'ajax',
       urlmatch: '@@addeditadvice',
   });

});

// this method is made to initialize overlays in the ajax-frame
// because they are not correctly initialized at page load
function initializePMOverlays(){
jQuery(function($) {
  
  // Add advice popup
  $('a.link-overlay').prepOverlay({
     subtype: 'ajax',
     urlmatch: '@@addeditadvice',
  });
});
// as this method is called on the onmousover event of the ajax-frame
// remove the event after first call to avoid it being called more than once
tag = $('div#ajax-listitems-frame');
tag[0].onmouseover = '';
}
