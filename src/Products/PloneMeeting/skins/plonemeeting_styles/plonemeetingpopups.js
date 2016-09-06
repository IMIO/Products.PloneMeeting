/* The jQuery here above will load a jQuery popup */

// function that initialize advice add, edit or view advice popup
function advicePopup() {
  $('a.link-overlay-pm-advice').prepOverlay({
        subtype: 'ajax',
        closeselector: '[name="form.buttons.cancel"]',
        config: {
            onBeforeLoad : function (e) {
                // CKeditor instances need to be initialized
                launchCKInstances();
                saveAdvice();
                return true;
            },
            onClose : function (e) {
                // make sure CKeditor instances are destroyed because
                // it can not be initialized twice
                $.each(CKEDITOR.tools.objectKeys(CKEDITOR.instances), function(k, v) {
                  CKEDITOR.instances[v].destroy();
                })
                // unlock current element
                // compute url, find link to advice edit and remove trailing '/edit'
                var rel_num = this.getOverlay().attr('id');
                advice_url = $("[rel='#" + rel_num + "']").attr('href')
                // do not unlock if we were on the '++add++meetingadvice' form
                if (advice_url.indexOf('++add++meetingadvice') === -1) {
                    // remove '/edit'
                    advice_url = advice_url.slice(0, -5);
                    // now we have the edit link, take the href and remove the '/edit'
                    $.ajax({
                        url: advice_url + "/@@plone_lock_operations/safe_unlock", });
                }
                return true;
            }
        }
  });
};

// when opened in an overlay, save advice using an ajax call, this is done for faceted
function saveAdvice() {
  if ($('#faceted-form').length) {
    $('input#form-buttons-save').click(function(event) {
      event.preventDefault();
      var data = {};
      $(this.form.elements).each(function(){
        // special handling for CKeditor instances
        if (CKEDITOR.instances[this.name]) {
          data[this.name] = CKEDITOR.instances[this.name].getData();
        }
        else if (this.id.match("-0$") || this.id.match("-1$")) {
          // pass some elements, like radio button subelements
          data[this.name] = this.form.elements[this.name].value
        }
        else {
          data[this.name] = this.value;
        }
        });
      $.ajax({
          type: 'POST',
          url: this.form.action,
          data: data,
          cache: false,
          async: true,
          success: function(data) {
              $('input#form-buttons-cancel').click();
              Faceted.URLHandler.hash_changed();
          },
          error: function(jqXHR, textStatus, errorThrown) {
            /*console.log(textStatus);*/
            window.location.href = window.location.href;
            },
      });

    });
    }
}

// prepare overlays for normal (non-ajax) pages
// like meetingitem_view or overlays that you can raise from the portlet_plonemeeting
jQuery(document).ready(function($) {
    // advice popup
    advicePopup();

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
    // advice popup
    advicePopup();

    jQuery(function($) {
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
}

// Open every links having the classicpopup class in a... classic popup...
jQuery(document).ready(function($) {
    jQuery('a.classicpopup').live('click', function(){
        newwindow=window.open($(this).attr('href'),'','height=auto,width=auto');
        if (window.focus) {newwindow.focus()}
        return false;
    });
});


jQuery(function($) {
  $('a.link-overlay-pm-annex').prepOverlay({
        subtype: 'ajax',
        closeselector: '[name="form.buttons.cancel"]',
        config: {
            onLoad : function (e) {
                // initialize select2 widget
                initializeSelect2Widgets();
                initializeIconifiedCategoryWidget();
                return true;
            },
            onClose : function (e) {
                // unlock current element
                // compute url, find link to advice edit and remove trailing '/edit'
                var rel_num = this.getOverlay().attr('id');
                obj_url = $("[rel='#" + rel_num + "']").attr('href')
                // do not unlock if we were on the '++add++annex' form
                if (obj_url.indexOf('++add++annex') === -1) {
                    // remove '/edit'
                    obj_url = obj_url.slice(0, -5);
                    // now we have the right url, append the unlock view name
                    $.ajax({
                        url: obj_url + "/@@plone_lock_operations/safe_unlock", });
                }
                return true;
            }
        }
  });
});
