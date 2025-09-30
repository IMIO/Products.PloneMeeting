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
            onBeforeClose : function (e) {
                // avoid closing overlay when click outside overlay
                // or when it is closed by WSC
                if (e.target.id == "exposeMask" ||
                    e.target.classList.contains("wsc-icon") ||
                    e.target.classList.contains("wsc-button")) {return false;}
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

// opening the encode votes form
function manageAttendees() {
    jQuery(function($){
        $('a.link-overlay-pm-manage-attendees').prepOverlay({
            api: true,
            subtype: 'ajax',
            noform: 'redirect',
            redirect: $.plonepopups.redirectbasehref,
            closeselector: '[name="form.buttons.cancel"]',
            config: {
                onBeforeLoad : function (e) {
                  // odd even for datagridfield
                  // need to add listing to table class
                  $('table.datagridwidget-table-view').addClass('listing');
                  $('table tbody').each(setoddeven);
                  submitFormHelper(this.form, onsuccess=onsuccessManageAttendees);
                  return true;
                },
                onBeforeClose : function (e) {
                    // avoid closing overlay when click outside overlay
                    if (e.target.id == "exposeMask") {return false;}
                },
                onClose : function (e) {
                    selector = '.attendee-value';
                    if (e.target.innerHTML.includes('item-encode-votes-form')) {
                      selector = '.vote-value';
                    }
                    else if (e.target.innerHTML.includes('_attendee_form')) {
                      selector = '.attendee-assembly';
                    }
                    else if (e.target.innerHTML.includes('_signatory_form')) {
                      selector = '.attendee-signatory';
                    }
                    else if (e.target.innerHTML.includes('_nonattendee_form')) {
                      selector = '.attendee-nonattendee';
                    }
                    highlight_attendees(selector);

                    // reload votesResult
                    if (e.target.innerHTML.includes('_votes_form')) {
                      reloadVotesResult();
                    }
              },
            }
       });
    });
}

function reloadVotesResult() {
    tags = $("div#marker-collapsible-field-votesResult");
    if (tags.length == 1) {
      loadContent(tags[0], load_view='@@display-collapsible-rich-field?field_name=votesResult');
    }
}

// refresh meeting attendees panel
function refresh_meeting_attendees() {
  tag = $("#collapsible-assembly-and-signatures div")[0];
  var timeStamp = new Date();
  result = loadContent(
    tag,
    load_view='@@load_meeting_assembly_and_signatures?cache_date=' + timeStamp,
    async=false,
    base_url=null,
    event_name="toggle_details_ajax_success");
  highlight_attendees();
}

// refresh item attendees panel
function refresh_attendees(highlight=null, click_cancel=false) {
  tag = $("#collapsible-assembly-and-signatures div")[0];
  var timeStamp = new Date();
  result = loadContent(
    tag,
    load_view='@@load_item_assembly_and_signatures?cache_date=' + timeStamp,
    async=false,
    base_url=null,
    event_name="toggle_details_ajax_success");
  if (click_cancel) {
    $('input#form-buttons-cancel').click();
  }
  if (highlight) {
    $.when(highlight_attendees(highlight));
  }
}
// highlight votes when it is refreshed
function highlight_attendees(highlight_selector='') {
  $.when($("#collapsible-assembly-and-signatures table tr td" + highlight_selector).effect(
    'highlight', {}, 2000));
  $.when($("#collapsible-assembly-and-signatures dl.portalMessage.warning").effect(
    'bounce', {}, 1000));
}

function onsuccessManageAttendees(data) {
  if (data.byteLength) {
    // data is an arraybuffer, convert it to str
    data_str = new TextDecoder().decode(data);
    $("div.pb-ajax div")[0].innerHTML = data_str;
  }
  else {
    refresh_attendees(highlight=null, click_cancel=true);
  }
}

// the content history popup
function contentHistory() {
    jQuery(function($) {
        // Content history popup
        $('.contentHistory a').prepOverlay({
           subtype: 'ajax',
           filter: 'h2, #content-history',
           urlmatch: '@@historyview',
           urlreplace: '@@contenthistorypopup'
        });
  });
}

// the duplicate item action
function duplicateItem() {
    jQuery(function($) {
        // Content history popup
        $('.apButtonAction_form_duplicate').prepOverlay({
           subtype: 'ajax',
           closeselector: '[name="form.buttons.cancel"]',
        });
  });
}

// the item export pdf action
function itemExportPDF() {
    // Content history popup
    $('.apButtonAction_form_export_pdf').prepOverlay({
       subtype: 'ajax',
       closeselector: '[name="form.buttons.cancel"]',
       config: {
            onBeforeLoad : function(e) {
                // close on Apply as we download a file
                var apply_button = $("input#form-buttons-apply_export_pdf");
                apply_button.click(function(e) {
                    $('input#form-buttons-cancel').click();
                });
                // open in new tab so user see that download is on the way
                var form = $("form#form");
                form.attr('target', 'blank');
                return true;
          },
        },
    });
}

// common overlays
// the content history popup
function pmCommonOverlays(selector_prefix='') {
    jQuery(function($){
        // Every common overelays, must stay at the bottom of every defined overlays!!!
        // Or it is taken before others because selector matches
        $(selector_prefix + 'a.link-overlay-pm').prepOverlay({
            subtype: 'ajax',
            closeselector: '[name="form.buttons.cancel"]',
            config: {
                onBeforeClose : function (e) {
                    // avoid closing overlay when click outside overlay
                    // or when it is closed by WSC
                    if (e.target.id == "exposeMask" ||
                        e.target.classList.contains("wsc-icon") ||
                        e.target.classList.contains("wsc-button")) {return false;}
                },
            },
        });
        // Info overlays that may be closed whenever clicking outside
        $(selector_prefix + 'a.link-overlay-pm-info').prepOverlay({
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
    adviceAddEdit();
    listTypeChange();
    pollTypeChange();
    emergencyChange();
    completenessChange();
    availableMailingLists();
    duplicateItem();
    itemExportPDF();

    // inserting methods infos on meeting_view
    tooltipster_helper(selector='.tooltipster-inserting-methods-helper-msg',
                       view_name='@@display-inserting-methods-helper-msg',
                       data_parameters=[],
                       options={position: 'bottom',
                                trigger: 'click'});
    pmCommonOverlays();
});

function attendeesInfos() {
    // item absents on item/meeting
    tooltipster_helper(selector='.tooltipster-meeting-item-not-present',
                       view_name='@@display-meeting-item-not-present',
                       data_parameters=['not_present_uid', 'not_present_type']);
    // item signatories on item/meeting
    tooltipster_helper(selector='.tooltipster-meeting-item-signatories',
                       view_name='@@display-meeting-item-signatories',
                       data_parameters=['signatory_uid']);
    // item redefined position on item/meeting
    tooltipster_helper(selector='.tooltipster-meeting-item-redefined-position',
                       view_name='@@display-meeting-item-redefined-position',
                       data_parameters=['attendee_uid']);
}

// prepare overlays and tooltipsters in dashboards
function initializeDashboard(){
    categorizedChildsInfos();
    advicesInfos();
    adviceAddEdit();
    contentHistory();
    duplicateItem();
    itemExportPDF();
    pmCommonOverlays();
    listTypeChange();
    actionsPanelTooltipster();
}

function initializeAdvicePopup(instance) {
    // configure the triggerClose options after popup has been opened
    // this avoid weird behavior where in this case, just quickly hovering
    // the tooltipster would open it
    instance.__options.triggerClose = {click: true, tap: true, };

    // when an advice popup tooltipster is opened, we need to init JS on it
    categorizedChildsInfos({selector: 'td.advice_annexes .tooltipster-childs-infos', });
    adviceAddEdit();
    advicePreview();
    inheritedItemInfos();
    usersGroupInfos();
    adviceChangeDelay();
    contentHistory();
    // overlay for remove inherited advice
    pmCommonOverlays(selector_prefix='div.advice_infos_tooltipster ');
    initReadmore();
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
                // avoid closing overlay when click outside overlay
                if (e.target.id == "exposeMask") {return false;}
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

function listTypeChange() {
    // listType change on meetingitem_view
    tooltipster_helper(selector='.tooltipster-item-listtype-change',
                       view_name='@@item-listtype',
                       data_parameters=[],
                       options={position: 'right'});
}

function pollTypeChange() {
    // pollType change on meetingitem_view
    tooltipster_helper(selector='.tooltipster-item-polltype-change',
                       view_name='@@item-polltype',
                       data_parameters=[],
                       options={});
}

function votePollTypeChange() {
    // vote pollType change on meetingitem_view
    tooltipster_helper(selector='.tooltipster-item-vote-polltype-change',
                       view_name='@@item-vote-polltype',
                       data_parameters=['vote_number:int'],
                       options={});
}

function emergencyChange() {
    // emergency change on meetingitem_view
    tooltipster_helper(selector='.tooltipster-item-emergency-change',
                       view_name='@@item-emergency',
                       data_parameters=[],
                       options={position: 'bottom',
                                functionReady_callback: pmCommonOverlays});
}

function completenessChange() {
    // emergency change on meetingitem_view
    tooltipster_helper(selector='.tooltipster-item-completeness-change',
                       view_name='@@item-completeness',
                       data_parameters=[],
                       options={position: 'bottom',
                                functionReady_callback: pmCommonOverlays});
}

function availableMailingLists() {
    // mailing lists displayed on a POD template in the generation links viewlet
    tooltipster_helper(selector='.tooltipster-available-mailing-lists',
                       view_name='@@available-mailing-lists',
                       data_parameters=['template_uid', 'output_format'],
                       options={trigger: 'click', position: 'bottom'});
}

function inheritedItemInfos() {
    tooltipster_helper(selector='.tooltipster-inherited-advice',
                       view_name='@@display-inherited-item-infos',
                       data_parameters=['advice_id'],
                       options={maxWidth: 750});
}

function usersGroupInfos() {
    tooltipster_helper(selector='.tooltipster-group-users',
                       view_name='@@display-group-users',
                       data_parameters=['group_ids:json'],
                       options={position: 'bottom'});
}

function adviceChangeDelay() {
    tooltipster_helper(selector='.tooltipster-advice-change-delay',
                       view_name='@@advice-available-delays',
                       data_parameters=['advice'],
                       options={functionReady_callback: pmCommonOverlays});
}

function positionAdvicePopup(instance, helper, position) {
    // position to 50px of the top
    if (position.coord.top < 0) {
        position.coord.top = 0;
    }
    return position;
}

function advicesInfos() {
    // values are adapted when used in a dashboard to avoid negative top position
    // may occur with the available items dashboard or when screen zoomed to much
    dashboard_position = 'left';
    position_callback = null;
    if ($('table#faceted_table').length) {
        dashboard_position = ['left'];
        position_callback = positionAdvicePopup;
    }
    // displayed in faceted dashboard
    tooltipster_helper(
      selector='div#faceted-form a.tooltipster-advices-infos',
      view_name='@@advices-icons-infos',
      data_parameters=['adviceType'],
      options={zIndex: 50,
               position: dashboard_position,
               functionReady_callback: initializeAdvicePopup,
               passInstanceToCallback: true,
               functionPosition_callback: position_callback,
               minWidth: 750,
               maxWidth: 750,
               close_other_tips: true});
    // displayed on item view, displayed bottom to deal with readmorable
    tooltipster_helper(
      selector='a.tooltipster-advices-infos',
      view_name='@@advices-icons-infos',
      data_parameters=['adviceType'],
      options={zIndex: 50,
               position: 'bottom',
               functionReady_callback: initializeAdvicePopup,
               passInstanceToCallback: true,
               minWidth: 750,
               maxWidth: 750,
               close_other_tips: true});
}

function groupedConfigs() {
    tooltipster_helper(selector='li[id*="portaltab-mc_config_group_"] a',
                       view_name='@@display-grouped-configs',
                       data_parameters=['config_group'],
                       options={
                        theme: 'tooltipster-light sub-portaltab',
                        arrow: false,
                        functionPosition_callback: function (instance, helper, position){
                            position.coord.top -= 6;return position;},
                        });
}

function initializeActionsPanelTooltipster_callback() {
    jQuery(function($) {
        initializeOverlays();
        preventDefaultClick();
        duplicateItem();
        itemExportPDF();
    });
}

function actionsPanelTooltipster() {
    tooltipster_helper(
        selector='.tooltipster-actions-panel',
        view_name='@@facade_actions_panel',
        data_parameters=['showHistory:boolean', 'showActions'],
        options={
         position: 'bottom',
         functionReady_callback: initializeActionsPanelTooltipster_callback,
         close_other_tips: true, });
}
