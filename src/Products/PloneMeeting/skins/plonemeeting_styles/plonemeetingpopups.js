/* The jQuery here above will load a jQuery popup */

// function that initialize advice add/edit advice popup
function adviceAddEdit() {
  $('a.link-overlay-pm-advice').prepOverlay({
        subtype: 'ajax',
        closeselector: '[name="form.buttons.cancel"]',
        config: {
            onBeforeLoad : function (e) {
                // CKeditor instances need to be initialized
                launchCKInstances();
                // add an event handler onclick on the save button
                saveAdvice();
                // save advice_url as it is no more reachable when closing the overlay with the cross
                var rel_num = this.getOverlay().attr('id');
                this.advice_url = $("[rel='#" + rel_num + "']").attr('href');
                return true;
            },
            onClose : function (e) {
                // make sure CKeditor instances are destroyed because
                // it can not be initialized twice
                $.each(CKEDITOR.tools.objectKeys(CKEDITOR.instances), function(k, v) {
                  CKEDITOR.instances[v].destroy();
                });
                // unlock current element
                // do not unlock if we were on the '++add++meetingadvice' form
                if (this.advice_url.indexOf('++add++meetingadvice') === -1) {
                    // remove '/edit'
                    advice_url = this.advice_url.slice(0, -5);
                    // now we have the edit link, take the href and remove the '/edit'
                    $.ajax({
                        url: advice_url + "/@@plone_lock_operations/safe_unlock", });
                }
                return true;
            }
        }
  });
}


// opening the advice preview from the advice tooltip
function advicePreview() {
    jQuery(function($){
        $('a.link-overlay-pm-preview-advice').prepOverlay({
            subtype: 'ajax',
            closeselector: '[name="form.buttons.cancel"]',
            config: {
                onBeforeLoad : function (e) {
                    // tooltipster for annexes
                    categorizedChildsInfos({selector: 'div.meeting-advice-view .tooltipster-childs-infos', });
                    return true;
                },
            }
       });
    });
}

// the content history popup
function contentHistory() {
    jQuery(function($) {
        // Content history popup
        $('a.overlay-history').prepOverlay({
           subtype: 'ajax',
           filter: 'h2, #content-history',
           urlmatch: '@@historyview',
           urlreplace: '@@contenthistorypopup'
        });
  });
}

// common overlays
// the content history popup
function pmCommonOverlays() {
    jQuery(function($){
        // Every common overelays, must stay at the bottom of every defined overlays!!!
        // Or it is taken before others because selector matches
        $('a.link-overlay-pm').prepOverlay({
            subtype: 'ajax',
            closeselector: '[name="form.buttons.cancel"]',
       });
    });
}


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
          data[this.name] = this.form.elements[this.name].value;
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

jQuery(document).ready(function($) {
    usersGroupInfos();
    groupedConfigs();
    advicesInfos();

    // inserting methods infos on meeting_view
    tooltipster_helper(selector='.tooltipster-inserting-methods-helper-msg',
                       view_name='@@display-inserting-methods-helper-msg',
                       data_parameters={});

    pmCommonOverlays();
});

// prepare overlays and tooltipsters in dashboards
function initializeDashboard(){
    usersGroupInfos();
    categorizedChildsInfos();
    advicesInfos();
    contentHistory();
    pmCommonOverlays();
}

function initializeAdvicePopup(){
    // when an advice popup tooltipster is opened, we need to init JS on it
    categorizedChildsInfos({selector: 'td.advice_annexes .tooltipster-childs-infos', });
    adviceAddEdit();
    advicePreview();
    inheritedItemInfos();
    usersGroupInfos();
    contentHistory();
}

function overOverlays(){
  // used by overlays displayed over another overlay
  $('a.link-overlay-pm-over').prepOverlay({
        subtype: 'ajax',
        closeselector: '[name="form.buttons.cancel"]',
        config: {
          top:'15%',
          left:'0',
          onBeforeLoad: function(e) {
            $(this.getOverlay()).css("z-index", "50000");
              return true;
              },
            },
    });
}

function editAnnex(){
  $('a.link-overlay-pm-annex').prepOverlay({
        subtype: 'ajax',
        closeselector: '[name="form.buttons.cancel"]',
        config: {
            onLoad : function (e) {
                // initialize select2 widget
                initializeSelect2Widgets(width='400px');
                initializeIconifiedCategoryWidget();
                return true;
            },
            onBeforeClose : function (e) {
                // close every opened select2 widgets
                $('.single-select2-widget').select2("close");
                $('.multi-select2-widget').select2("close");
            },
            onClose : function (e) {
                // unlock current element
                // compute url, find link to annex edit and remove trailing '/edit'
                var rel_num = this.getOverlay().attr('id');
                obj_url = $("[rel='#" + rel_num + "']").attr('href');
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
}

function inheritedItemInfos() {
    tooltipster_helper(selector='.tooltipster-inherited-advice',
                       view_name='@@display-inherited-item-infos',
                       data_parameters=['advice_id']);
}

function usersGroupInfos() {
    tooltipster_helper(selector='.tooltipster-group-users',
                       view_name='@@display-group-users',
                       data_parameters=['group_id']);
}

function advicesInfos() {
    tooltipster_helper(
      selector='.tooltipster-advices-infos',
      view_name='@@advices-icons-infos',
      data_parameters=['adviceType'],
      options={zIndex: 1,
               position: 'bottom',
               trigger: 'custom',
               triggerOpen: {
                  mouseenter: true,
                  },
               triggerClose: {
                  click: true,
                  },
               functionReady_callback: initializeAdvicePopup,
               close_other_tips: true});
    tooltipster_helper(
      selector='.tooltipster-dashboard-advices-infos',
      view_name='@@advices-icons-infos',
      data_parameters=['adviceType'],
      options={zIndex: 1,
               position: 'left',
               trigger: 'custom',
               triggerOpen: {
                  mouseenter: true,
                  },
               triggerClose: {
                  click: true,
                  },
               functionReady_callback: initializeAdvicePopup,
               close_other_tips: true});
}

function groupedConfigs() {
    tooltipster_helper(selector='li[id*="portaltab-mc_config_group_"] a',
                       view_name='@@display-grouped-configs',
                       data_parameters=['config_group']);
}
