/* The jQuery here above will load a jQuery popup */

// prepare overlays for normal (non-ajax) pages
// like meetingitem_view or overlays that you can raise from the portlet_plonemeeting
jQuery(document).ready(function($) {

jQuery(function($) {
  // Add or edit advice popup
  $('a.link-overlay-pm-advice').prepOverlay({
        subtype: 'ajax',
        closeselector: '[name="form.buttons.cancel"]',
        config: {
            onBeforeLoad : function (e) {
                // CKeditor instances need to be initialized
                launchCKInstances();
                return true;
            },
            onClose : function (e) {
                // make sure CKeditor instances are destroyed because
                // it can not be initialized twice
                CKEDITOR.instances['form.widgets.advice_comment'].destroy();
                return true;
            }
        }
  });
});

jQuery(function($){
    // Every common overelays, must stay at the bottom of every defined overlays!!!
    // Or it is taken before others because selector matches
    $('a.link-overlay-pm').prepOverlay({
        subtype: 'ajax',
        closeselector: '[name="form.buttons.cancel"]',
   });
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
  // Add or edit advice popup
  $('a.link-overlay-pm-advice').prepOverlay({
        subtype: 'ajax',
        closeselector: '[name="form.buttons.cancel"]',
        config: {
            onBeforeLoad : function (e) {
                // CKeditor instances need to be initialized
                launchCKInstances();
                return true;
            },
            onClose : function (e) {
                // make sure CKeditor instances are destroyed because
                // it can not be initialized twice
                CKEDITOR.instances['form.widgets.advice_comment'].destroy();
                return true;
            }
        }
  });
    // Content history popup
    $('a.overlay-history').prepOverlay({
       subtype: 'ajax',
       filter: 'h2, #content-history',
       urlmatch: '@@historyview',
       urlreplace: '@@contenthistorypopup'
    });
});

jQuery(function($) {
  // every common overelays
  $('a.link-overlay-pm').prepOverlay({
        subtype: 'ajax',
        closeselector: '[name="form.buttons.cancel"]',
  });
});

jQuery(function($) {
  // Add transition confirmation popup
  $('a.link-overlay-actionspanel.transition-overlay').prepOverlay({
        subtype: 'ajax',
        closeselector: '[name="form.buttons.cancel"]',
  });
});
// as this method is called on the onmousover event of the ajax-frame
// remove the event after first call to avoid it being called more than once
$('div.ajax-pm-frame').each(function(){
    $(this).removeAttr('onmouseover');
    })
}

// When on a meething view, we have to handle some more parameters to keep on wich page we are
// Adapt the link that will show a popup for confirming a transition
// to pass iStartNumber and lStartNumber that are global JS variables defined on the meeting_view
function initializePMOverlaysOnMeeting(){
jQuery(function($) {
$('a.link-overlay-actionspanel.transition-overlay').each(function(){
    $(this).attr('href',$(this).attr('href') + '&iStartNumber=' + iStartNumber + '&lStartNumber=' + lStartNumber);
    })
  })
  initializePMOverlays()
}

// Open every links having the classicpopup class in a... classic popup...
jQuery(document).ready(function($) {
    jQuery('a.classicpopup').live('click', function(){
        newwindow=window.open($(this).attr('href'),'','height=auto,width=auto');
        if (window.focus) {newwindow.focus()}
        return false;
    });
});
