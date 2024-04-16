// Function that shows a popup that asks the user if he really wants to reinitialize advice delay
function confirmReinitializeDelay(base_url, advice, tag, msgName){
    if (!msgName) {
        msgName = 'reinit_delay_confirm_message';
    }
    var msg = window.eval(msgName);
    if (confirm(msg)) {
        callViewAndReload(base_url, view_name='@@advice-reinit-delay', params={'advice': advice});
    }
}

// Dropdown for selecting an annex type
var ploneMeetingSelectBoxes = new Object();

function createPloneMeetingSelectBox(name, imgSelectBox) {
  ploneMeetingSelectBoxes[name] = imgSelectBox;
}

function displayPloneMeetingSelectBox(selectName) {
  var box = document.getElementById(ploneMeetingSelectBoxes[selectName].box);
  var button = document.getElementById(ploneMeetingSelectBoxes[selectName].button);
  box_is_visible = $(box).is(':visible');
  $(box).fadeToggle('fast');
  if (!box_is_visible) {
    /* Button seems pressed */
    button.style.borderStyle = "inset";
  }
  else {
    button.style.borderStyle = "outset";
  }
}

function hidePloneMeetingSelectBox(selectName, idImage, inner_tag, value, predefined_title) {
  var newImage = document.getElementById(idImage);

  var btnImage = document.getElementById(ploneMeetingSelectBoxes[selectName].image);
  var btnText = document.getElementById(ploneMeetingSelectBoxes[selectName].buttonText);

  document.getElementById(ploneMeetingSelectBoxes[selectName].button).style.borderStyle = "outset";
  document.getElementById(ploneMeetingSelectBoxes[selectName].box).style.display="none";
  btnText.innerHTML = inner_tag.innerHTML;
}

/* The functions below are derived from Plone's dropdown.js for using a dropdown
   menu that is specific to the block of icons showing annexes. */
function findParent(node, className) {
    // Finds a parent having a class named p_className.
    var nextParent = node.parentNode;
    while (nextParent) {
        if (hasClassName(nextParent, className)) return nextParent;
        nextParent = nextParent.parentNode;
    }
    return null;
}

function toggleMenu(menuId){
  /* we may have '.' in the id and it fails while using directly $(selector)
   * because it thinks we are using a CSS class selector so use getElementById */
  menu = $(document.getElementById('pm_menu_' + menuId));
  menu.fadeToggle(100);
  return;
}

var wrongTextInput = '#ff934a none';
function gotoItem(tag, lastItemNumber) {
  tag = tag[0];
  itemNumber = tag.value;
  if((parseInt(itemNumber)>=1) && (parseInt(itemNumber)<=lastItemNumber))  {
      document.location.href = document.baseURI + '@@object_goto?itemNumber=' + itemNumber;
    }
  else tag.style.background = wrongTextInput;
}

function computeStartNumberFrom(itemNumber, totalNbOfItems, batchSize) {
  // Here, we compute the start number of the batch where to find the item
  // whose number is p_itemNumber.
  var startNumber = 1;
  var res = startNumber;
  while (startNumber <= totalNbOfItems) {
    if (itemNumber < startNumber + batchSize) {
      res = startNumber;
      break;
    }
    else startNumber += batchSize;
  }
  return res;
}

// Function that toggles the descriptions visibility
function toggleMeetingDescriptions() {
  if (readCookie('pmShowDescriptions')=='true') {
      setDescriptionsVisiblity(false);
  }
  else {
      setDescriptionsVisiblity(true);
  }
}

// Function that, depending on p_mustShow, shows or hides the descriptions.
function setDescriptionsVisiblity(mustShow) {

  // hide or show every pmMoreInfo element
  var $pmMoreInfos = $('.pmMoreInfo');

  if (!$pmMoreInfos.length) {
      // reload the faceted
      Faceted.URLHandler.hash_changed();
  }
  // show/hide the infos and update the cookie
  if (mustShow) {
    $pmMoreInfos.hide().fadeIn("fast");
    createCookie('pmShowDescriptions', 'true');
  }
  else {
    $pmMoreInfos.fadeOut("fast", function() {
           $(this).hide();
       });
    createCookie('pmShowDescriptions', 'false');
  }
}

// Function that initialize CSS classes on assembly_and_signatures
function initializePersonsCookie() {
  show = readCookie('showPersons');
  if (!show) show = 'false';
  label_tag = $('div#assembly-and-signatures')[0];
  tag = $('div#collapsible-assembly-and-signatures')[0];
  if (show == 'true') {
    label_tag.click();
    createCookie('showPersons', 'true');
    //label_tag.classList.add('active');
    //tag.style.display = 'block';
  }
}

// Function that toggles the persons visibility
function togglePersonsCookie() {
  show = readCookie('showPersons');
  if (!show) show = 'true';
  if (show == 'true') {
    createCookie('showPersons', 'false');
  }
  else {
    createCookie('showPersons', 'true');
  }
}

function toggleBooleanCookie(cookieId) {
  // What is the state of this boolean (expanded/collapsed) cookie?
  var state = readCookie(cookieId);
  if ((state != 'collapsed') && (state != 'expanded')) {
    // No cookie yet, create it.
    createCookie(cookieId, 'collapsed');
    state = 'collapsed';
  }
  var hook = document.getElementById(cookieId); // The hook is the part of
  // the HTML document that needs to be shown or hidden.
  var displayValue = 'none';
  var newState = 'collapsed';
  var imgSrc = 'treeCollapsed.gif';
  if (state == 'collapsed') {
    // Show the HTML zone
    displayValue = 'block';
    imgSrc = 'treeExpanded.gif';
    newState = 'expanded';
  }
  // Update the corresponding HTML element
  hook.style.display = displayValue;
  var img = document.getElementById(cookieId + '_img');
  img.src = imgSrc;
  // Inverse the cookie value
  createCookie(cookieId, newState);
}

var dialogData = null; // Used to store data while popup is shown.
// Functions for opening and closing a dialog window
function openDialog(dialogId) {
  // Open the dialog window
  var dialog = document.getElementById(dialogId);
  // Put them at the right place on the screen
  var scrollTop = window.pageYOffset || document.documentElement.scrollTop || 0;
  dialog.style.top = (scrollTop + 150) + 'px';
  dialog.style.display = "block";
  // Show the greyed zone
  var greyed = document.getElementById('hsGrey');
  greyed.style.top = scrollTop + 'px';
  greyed.style.display = "block";
}

// Function allowing to remove an event from an object's history
function deleteEvent(objectUid, eventTime) {
  var f = document.getElementById("deleteForm");
  // Store the object UID
  f.objectUid.value = objectUid;
  f.eventTime.value = eventTime;
  openDialog('deleteDialog');
}

// AJAX machinery
var xhrObjects = new Array(); // An array of XMLHttpRequest objects
function XhrObject() { // Wraps a XmlHttpRequest object
  this.freed = 1; // Is this xhr object already dealing with a request or not?
  this.xhr = false;
  if (window.XMLHttpRequest) this.xhr = new XMLHttpRequest();
  else this.xhr = new ActiveXObject("Microsoft.XMLHTTP");
  this.hook = '';  /* The ID of the HTML element in the page that will be
                      replaced by result of executing the Ajax request. */
  this.onGet = ''; /* The name of a Javascript function to call once we receive
                      the result. */
  this.info = {};  /* An associative array for putting anything else. */
}

function getAjaxChunk(pos) {
  // This function is the callback called by the AJAX machinery (see function
  // askAjaxChunk below) when an Ajax response is available.
  // First, find back the correct XMLHttpRequest object
  if ( (typeof(xhrObjects[pos]) != 'undefined') &&
       (xhrObjects[pos].freed === 0)) {
    var hook = xhrObjects[pos].hook;
    if (xhrObjects[pos].xhr.readyState == 1) {
      // The request has been initialized: display the waiting radar
      var hookElem = document.getElementById(hook);
      if (hookElem) hookElem.innerHTML = "<br><br><div align=\"center\"><img src=\"spinner.gif\"/><\/div>";
    }
    if (xhrObjects[pos].xhr.readyState == 4) {
      // We have received the HTML chunk
      var hookElem = document.getElementById(hook);
      if (hookElem && (xhrObjects[pos].xhr.status == 200)) {
        hookElem.innerHTML = xhrObjects[pos].xhr.responseText;
        // Call a custom Javascript function if required
        if (xhrObjects[pos].onGet) {
          xhrObjects[pos].onGet(xhrObjects[pos], hookElem);
        }
        // Scroll to it if required
        if (hook.substr(-1) == '_') hookElem.scrollIntoView();
      }
      xhrObjects[pos].freed = 1;
    }
  }
}

function askAjaxChunk(hook, mode, url, page, macro, params, beforeSend, onGet) {
  /* This function will ask to get a chunk of HTML on the server through a
     XMLHttpRequest. p_mode can be 'GET' or 'POST'. p_url is the URL of a given
     server object. On this URL we will call the page "ajax.pt" that will call
     a specific p_macro in a given p_page with some additional p_params (must be
     an associative array) if required.

     p_hook is the ID of the HTML element that will be filled with the HTML
     result from the server.

     p_beforeSend is a Javascript function to call before sending the request.
     This function will get 2 args: the XMLHttpRequest object and the p_params.
     This method can return, in a string, additional parameters to send, ie:
     "&param1=blabla&param2=blabla".

     p_onGet is a Javascript function to call when we will receive the answer.
     This function will get 2 args, too: the XMLHttpRequest object and the HTML
     node element into which the result has been inserted.
  */
  // First, get a non-busy XMLHttpRequest object.
  var pos = -1;
  for (var i=0; i < xhrObjects.length; i++) {
    if (xhrObjects[i].freed == 1) { pos = i; break; }
  }
  if (pos == -1) {
    pos = xhrObjects.length;
    xhrObjects[pos] = new XhrObject();
  }
  xhrObjects[pos].hook = hook;
  xhrObjects[pos].onGet = onGet;
  if (xhrObjects[pos].xhr) {
    var rq = xhrObjects[pos];
    rq.freed = 0;
    // Construct parameters
    var paramsFull = 'page=' + page + '&macro=' + macro;
    if (params) {
      for (var paramName in params)
        paramsFull = paramsFull + '&' + paramName + '=' + params[paramName];
    }
    // Call beforeSend if required
    if (beforeSend) {
       var res = beforeSend(rq, params);
       if (res) paramsFull = paramsFull + res;
    }
    // Construct the URL to call
    var urlFull = url + '/@@ajax';
    if (mode == 'GET') {
      urlFull = urlFull + '?' + paramsFull;
    }
    // Perform the asynchronous HTTP GET or POST
    rq.xhr.open(mode, urlFull, true);
    if (mode == 'POST') {
      // Set the correct HTTP headers
      rq.xhr.setRequestHeader(
        "Content-Type", "application/x-www-form-urlencoded");
      rq.xhr.onreadystatechange = function(){ getAjaxChunk(pos); };
      rq.xhr.send(paramsFull);
    }
    else if (mode == 'GET') {
      rq.xhr.onreadystatechange = function() { getAjaxChunk(pos); };
      if (window.XMLHttpRequest) { rq.xhr.send(null); }
      else if (window.ActiveXObject) { rq.xhr.send(); }
    }
  }
  // show actions_panel viewlet
  $("div#viewlet-below-content-body").show();
}

function askObjectHistory(hookId, objectUrl, maxPerPage, startNumber) {
  // Sends an Ajax request for getting the history of an object
  var params = {'maxPerPage': maxPerPage, 'startNumber': startNumber};
  askAjaxChunk(hookId, 'GET', objectUrl, '@@pm-macros', 'history', params);
}

// subfunction called by asyncToggleIcon
function toggleIcon(UID, img_tag, baseUrl, viewName, baseSelector) {
  var selector = baseSelector + UID;
  var $span = $(selector);
  if ($span.length == 1) {
    var $old = $('img', $span);
    $span.empty();
    var $img = $(img_tag).appendTo($span);
    // only redefine a onclick if not already defined in the HTML
    // this way, if a specific onclick is defined by the called view, we keep it
    if (!($img.attr('onclick'))) {
        $img.click(function() {
            asyncToggleIcon(UID, baseUrl, viewName, baseSelector);
        });
    }
    // special management for the toggle budgetRelated where we need to display
    // or hide the budgetInfos field.  If budgetRelated, we show it, either we hide it...
    $budgetInfos = $('div#hideBudgetInfosIfNotBudgetRelated');
    if (viewName == '@@toggle_budget_related') {
        if (img_tag.indexOf('nameBudgetRelatedNo') > 0) {
        $('#hideBudgetInfosIfNotBudgetRelated')[0].style.display = 'block';
        $budgetInfos.fadeIn("fast");
        $budgetInfos.show();
        }
        else {
            // find the 'hook_budgetInfos' and removes it
            $budgetInfos.fadeOut("fast", function() {
                   $(this).hide();
               });
        }
    }
  }
}

// function that toggle an icon by calling the p_viewName view
function asyncToggleIcon(UID, baseUrl, viewName, baseSelector) {
  $.ajax({
    url: baseUrl + "/" + viewName,
    dataType: 'html',
    data: {UID:UID},
    cache: false,
    success: function(data) {
        toggleIcon(UID, data, baseUrl, viewName, baseSelector);
      },
    error: function(jqXHR, textStatus, errorThrown) {
      /*console.log(textStatus);*/
      window.location.href = window.location.href;
      }
    });
}

function unselectCheckBoxes(names) {
    for (const name in names) {
    $('input[name="' + names[name] + '"]').each(function() {
        this.checked = false;
    });
    }
}

function reloadIfLocked() {
  /* Function that needs to be called when getting the edit view of a
     rich-text field through Ajax. */
  /* Check that we can actually edit the field, indeed the object
   * could have been locked in between (concurrent edit) */
  is_locked = $.ajax({
     async: false,
     type: 'GET',
     url: '@@plone_lock_info/is_locked_for_current_user',
     success: function(data) {
          //callback
     }
    });
  if (is_locked.responseText === "True") {
    /* remove # part in URL (meeting view is a faceted) */
    href = window.parent.location.href;
    window.parent.location.href = href.split('#')[0];
    return false;
  }
  return true;
}

/* functions used to manage quick edit functionnality */
function initRichTextField(rq, hook) {
  reloadIfLocked();
  // Javascripts inside this zone will not be executed. So find them
  // and trigger their execution here.
  var scripts = $('script', hook);
  var fieldName = hook.id.substring(5);
  for (var i=0; i<scripts.length; i++) {
    var scriptContent = scripts[i].innerHTML;
    if (scriptContent.search('addEventHandler') != -1) {
      // This is a kupu field that will register an event onLoad on
      // window but this event will never be triggered. So do it by
      // hand.
      currentFieldName = hook.id.substring(5);
    }
    else { eval(scriptContent); }
  }
  // Initialize CKeditor and set focus on it so wsc is started
  jQuery(launchCKInstances([fieldName,]));
  CKEDITOR.instances[fieldName].config.startupFocus = true;

  // Enable unload protection, avoid loosing unsaved changes if user click somewhere else
  var tool = window.onbeforeunload && window.onbeforeunload.tool;
  if (tool!==null) {
    tool.addForms.apply(tool, $('form.enableUnloadProtection').get());
    tool.submitting = false;
  }
  // enable UnlockHandler so element is correctly unlocked
  // if user choose to lost the changes in formUnload
  plone.UnlockHandler.init();
  // hide the actions_panel viewlet
  $("div#viewlet-below-content-body").hide();
}

function getRichTextContent(rq, params) {
  /* Gets the content of a rich text field before sending it through an Ajax
     request. */
  var fieldName = rq.hook.substring(5);
  var formId = 'ajax_edit_' + fieldName;
  var theForm = document.getElementById(formId);
  var theWidget = theForm[fieldName];
  /* with CKeditor the value is not stored in the widget so get the data from the real CKeditor instance */
  theWidget.value = CKEDITOR.instances[fieldName].getData();
  CKEDITOR.instances[fieldName].destroy();
  /* Disable the Plone automatic detection of changes to the form. Indeed,
     Plone is not aware that we have sent the form, so he will try to display
     a message, saying that changes will be lost because an unsubmitted form
     contains changed data. */
  window.onbeforeunload = null;
  // Construct parameters and return them.
  var params = "&fieldName=" + encodeURIComponent(fieldName) +
               '&fieldContent=' + encodeURIComponent(theWidget.value);
  return params;
}

// Function that allows to present several items in a meeting
function presentSelectedItems(baseUrl) {
    var uids = selectedCheckBoxes('select_item');
    if (!uids.length) {
      alert(no_selected_items);
    }
    else {
        // Ask confirmation
        var msg = window.eval('sure_to_present_selected_items');
        if (confirm(msg)) {
          // avoid Arrays to be passed as uids[]
          params = $.param({'uids:list': uids}, traditional=true);
          $.ajax({
            url: baseUrl + "/@@present-several-items",
            dataType: 'html',
            data: params,
            cache: false,
            async: true,
            success: function(data) {
                // update number of items
                updateNumberOfItems();
                // reload the faceted page
                Faceted.URLHandler.hash_changed();
                // and the presented items (parent)
                if (window != parent) {
                    parent.Faceted.URLHandler.hash_changed();
                }
            },
            error: function(jqXHR, textStatus, errorThrown) {
              /*console.log(textStatus);*/
              window.location.href = window.location.href;
              }
            });
        }
    }
}

// Function that allows to remove several items from a meeting
function removeSelectedItems(baseUrl) {
    var uids = selectedCheckBoxes('select_item');
    if (!uids.length) {
      alert(no_selected_items);
    }
    else {
        // Ask confirmation
        var msg = window.eval('sure_to_remove_selected_items');
        if (confirm(msg)) {
          // avoid Arrays to be passed as uids[]
          params = $.param({uids: uids}, traditional=true);
          $.ajax({
            url: baseUrl + "/@@remove-several-items",
            dataType: 'html',
            data: params,
            cache: false,
            async: true,
            success: function(data) {
                // update number of items
                updateNumberOfItems();
                // reload the faceted page
                Faceted.URLHandler.hash_changed();
                // and the available items iframe
                if ((window.frames[0]) && (window.frames[0] != window)) {
                    window.frames[0].Faceted.URLHandler.hash_changed();
                    }
                },
            error: function(jqXHR, textStatus, errorThrown) {
              /*console.log(textStatus);*/
              window.location.href = window.location.href;
              }
            });
        }
    }
}

// show/hide "move item to position" action icon button
function onChangeItemNumberFocus(itemNumber) {
  var imageButtons = document.getElementsByName('moveImageButton');
  for (var i=0; i<imageButtons.length; i++) {
      if (!['moveAction_' + itemNumber, 'moveAction_cancel_' + itemNumber].includes(
              imageButtons[i].id)) {
          imageButtons[i].style.visibility = 'hidden';
      }
      else {
          imageButtons[i].style.visibility = 'visible';
          imageButtons[i].style.cursor = 'pointer';
          document.getElementById('value_moveAction_' + itemNumber).select();
      }
  }
}

// hit on cancel button when changing item number
function onCancelChangeItemNumberClick(itemNumber) {
  // hide icons
  saveButton = document.getElementById('moveAction_' + itemNumber);
  saveButton.style.visibility = 'hidden';
  document.getElementById('moveAction_cancel_' + itemNumber).style.visibility = 'hidden';
  // set back original value in itemNumber input
  inputTag = saveButton.previousElementSibling;
  inputTag.value = inputTag.defaultValue;
}


// ajax call managing the @@change-item-order view
function moveItem(baseUrl, moveType, tag) {
  // if moveType is 'number', get the number from the input tag
  wishedNumber = '';
  if (moveType === 'number') {
    wishedNumber = tag.attr('value');
  }
  $.ajax({
    url: baseUrl + "/@@change-item-order",
    dataType: 'html',
    data: {'moveType': moveType,
           'wishedNumber': wishedNumber},
    cache: false,
    async: true,
    success: function(data) {
        // reload the faceted page
        Faceted.URLHandler.hash_changed();
        // set dashboardRowId if on meeting view
        // start_meeting_scroll_to_item_observer(tag);
    },
    error: function(jqXHR, textStatus, errorThrown) {
      /*console.log(textStatus);*/
      window.location.href = window.location.href;
      }
    });
}

function isMeeting() {
    if ($("body.template-meeting_view").length || $("body.template-meeting_available_items_view").length) {
        return true;
    }
    return false;
}

// event subscriber when a transition is triggered
$(document).on('ap_transition_triggered', synchronizeMeetingFaceteds);

// synchronize faceted displayed on the meeting_view, available items and presented items
function synchronizeMeetingFaceteds(infos) {

    if (isMeeting()) {

        // refresh iframe 'available items' while removing an item
        if ((infos.transition === 'backToValidated') &&
            ((window.frames[0]) && (window.frames[0] != window))) {
          /* if available collapsible closed, open it, this avoids problem
             with iframeresizer not correctly resized */
          if ($('h2.available-items.active').length == 0) {
            $('h2.available-items', parent.document).click();
          }
          window.frames[0].Faceted.URLHandler.hash_changed();
          updateNumberOfItems();
        } else if ((infos.transition === 'present') && (window != parent)) {
          // refresh main frame while presenting an item
          parent.Faceted.URLHandler.hash_changed();
          updateNumberOfItems();
        } else {
            // set dashboardRowId if on meeting view
            start_meeting_scroll_to_item_observer(infos.tag);
        }
    }
}

// event subscriber when a element is delete in a dashboard, refresh numberOfItems if we are on a meeting
$(document).on('ap_delete_givenuid', refreshAfterDelete);

function updateNumberOfItems() {
  // update the number of items displayed on the meeting_view when
  // items have been presented/removed of the meeting
  // get numberOfItems using an ajax call if on the meeting_view
  if (parent.$('.meeting_number_of_items').length) {
    response = $.ajax({
      url: document.baseURI + '/number_of_items?as_str:bool=1',
      dataType: 'html',
      cache: false,
      async: true,
      success: function(data) {
        parent.$('.meeting_number_of_items').each(function() {
          this.innerHTML = data;
        });
      },
    });
  }
}

function refreshAfterDelete(event) {
  // refresh number of items if relevant
  updateNumberOfItems();
  // refresh attendees if we removed a vote
  css_id = event.tag.id;
  if (css_id == 'delete-vote-action') {
    refresh_attendees(highlight='.vote-value');
  } else {
    if (css_id == 'reinit-attendees-order-action') {
      refresh_attendees(highlight='.td_cell_number-column');
    }
  }
}

function updateNumberOfAvailableItems() {
  // update the number of available items displayed on the meeting_view when
  // available items ajax query is successfull, we may get the search-results-number
  results = $('#search-results-number');
  if (results.length) {
    $('span.meeting_number_of_available_items', parent.document)[0].innerHTML = results.text();
  } else {
    $('span.meeting_number_of_available_items', parent.document)[0].innerHTML = "0";
    $('h2.available-items', parent.document).click();
  }
}

$(document).on('toggle_details_ajax_success', init_tooltipsters);

function init_tooltipsters(event) {
    css_id = event.tag.parentElement.id;
    if (css_id == 'collapsible-assembly-and-signatures') {
      pmCommonOverlays(selector_prefix='table#meeting_users ');
      attendeesInfos();
      manageAttendees();
      initializeItemAttendeesDND();
      votePollTypeChange();
    }
    if (css_id.startsWith('collapsible-text-linkeditem-')) {
      categorizedChildsInfos({selector: 'div.item-linkeditems .tooltipster-childs-infos', });
      advicesInfos();
    }
}

$(document).on('ckeditor_prepare_ajax_success', init_ckeditor);

function init_ckeditor(event) {
  initRichTextField(rq=null, hook=event.tag);
}

function saveCKeditor(field_name, base_url, async=true) {
  ajaxsave = CKEDITOR.instances[field_name].getCommand('ajaxsave');
  ajaxsave.async = async;
  CKEDITOR.instances[field_name].execCommand('ajaxsave', 'saveCmd');
}

function saveAndExitCKeditor(field_name, base_url) {
  // make sure ajaxsave is not async so content is saved before being shown again
  saveCKeditor(field_name, base_url, async=false);
  exitCKeditor(field_name, base_url);
}

function exitCKeditor(field_name, base_url) {
  CKEDITOR.instances[field_name].destroy();
  tag=$('div#hook_' + field_name.replace('.', '\\.'))[0];
  loadContent(tag,
              load_view='@@render-single-widget?field_name=' + field_name,
              async=false,
              base_url=base_url,
              event_name=null);
  // unlock context
  plone.UnlockHandler.execute();
  // destroy Unload handler
  var tool = window.onbeforeunload && window.onbeforeunload.tool;
  if (tool!==null) {
    tool.removeForms.apply(tool, $(document).find('form').get());
    tool.submitting = true;
  }
  // show the actions_panel viewlet
  $("div#viewlet-below-content-body").show();
}

function cancelCKeditor(field_name, base_url) {
  if (confirm(sure_to_cancel_edit)) {
    exitCKeditor(field_name, base_url);
  }
}

// when clicking on the input#forceInsertNormal, update the 'pmForceInsertNormal' cookie
function changeForceInsertNormalCookie(input) {
  if (input.checked) {
  createCookie('pmForceInsertNormal', true);
  }
  else {
  createCookie('pmForceInsertNormal', false);
  }
}

// manage the item 'budgetRelated' and 'budgetInfos' fields hide/show
// functionnality when displayed on the meetingitem_edit form
$(document).ready(function () {

  budgetRelated = $('input#budgetRelated');
  if (budgetRelated.length) {
    budgetInfos = $('div#hideBudgetInfosIfNotBudgetRelated');
    if (!budgetRelated[0].checked) {
      budgetInfos.hide();
    }

    budgetRelated.on('click', function() {
      if (this.checked) {
        budgetInfos.hide().fadeIn("fast");
      }
      else {
        budgetInfos.fadeOut("fast", function() {
        $(this).hide();
      });
    }
    });
  }

});

function updatePortletTodo() {
  var url = $("link[rel='canonical']").attr('href') + '/@@portlet-todo-update';
  var tag = $('dl.portlet.portletTodo');
  if (tag.length) {
  $.ajax({
    url: url,
    cache: false,
    async: true,
    success: function(data) {
        tag[0].parentNode.innerHTML = data;
    },
    error: function(jqXHR, textStatus, errorThrown) {
      tag.innerHTML = "Error loading, error was : " + errorThrown;
      }
  });
}}

// called on each faceted table change to update the portlet_todo
$(document).ready(function () {
  if (!has_faceted()) {
    updatePortletTodo();
  }
  $(Faceted.Events).bind(Faceted.Events.AJAX_QUERY_SUCCESS, function() {
    updatePortletTodo();
  });
  $(Faceted.Events).bind(Faceted.Events.INITIALIZE, function() {
    let searchParams = new URLSearchParams(window.location.search);
    b_start = searchParams.get('custom_b_start');
    if (b_start) {
        Faceted.Query.b_start = parseInt(b_start);
    }
  });
});

/* Disable caching of AJAX responses when using IE,
   otherwise, the double ajax call on the meeting (available and presented items)
   will display the same result... */
if (/msie/.test(navigator.userAgent.toLowerCase())) {
  $.ajaxSetup ({
    cache: false });
}

/* make sure not_selectable inputs in MeetingItem.optionalAdvisers are not selectable ! */
$(document).ready(function () {
    $("input[value^='not_selectable_value_'").each(function() {
        this.disabled = true;
    });
});

/* make sure first line of MeetingConfig.itemWFValidationLevels can not be edited */
$(document).ready(function () {
    $("input[id$='_itemWFValidationLevels_1'").each(function() {
        this.readOnly = true;
    });

});

function update_search_term(tag){
  var url = $("link[rel='canonical']").attr('href') + '/@@async_render_search_term';
  $.ajax({
    url: url,
    dataType: 'html',
    data: {collection_uid: tag.dataset.collection_uid},
    cache: false,
    // async: true provokes ConflictErrors when freezing a meeting???
    async: true,
    success: function(data) {
      $(tag).replaceWith(data);
      $(tag).find("script").each(function(i) {
        eval($(this).text());
      });
      createPloneMeetingSelectBox();
    },
    error: function(jqXHR, textStatus, errorThrown) {
      /*console.log(textStatus);*/
      tag.innerHTML = "Error loading, error was : " + errorThrown;
      }
  });
}

$(document).ready(function () {
  $('div[id^="async_search_term_"]').each(function() {
    update_search_term(this);
  });
});

function tableDNDComputeNewValue(table, row, data_name) {
    row_index = row.rowIndex;
    // data value will be something like 100 (item_number) or 2 (attendee position)
    row_number = parseInt(table.rows[row.rowIndex].cells[2].dataset[data_name]);
    // find if moving up or down
    move_type = 'up';
    if (table.tBodies[0].rows.length > row_index) {
         // we have a next row, compare with it
         next_row_number = parseInt(table.rows[row.rowIndex + 1].cells[2].dataset[data_name]);
         if (row_number < next_row_number) {
             move_type = 'down';
         }
    } else {move_type = 'down';}

    // now that we know the move, we can determinate number to use
    if (move_type == 'down') {
      new_value = parseInt(table.rows[row.rowIndex - 1].cells[2].dataset[data_name]);
    } else {
      new_value = parseInt(table.rows[row.rowIndex + 1].cells[2].dataset[data_name]);
    }
    return new_value;
}

/* dnd for items position on a meeting */
function initializeMeetingItemsDND(){
    let data_name = "item_number";
    let view_name = "@@change-item-order";
    $('table.faceted-table-results').tableDnD({
      onDrop: function(table, row) {
        row_id = row.id;
        new_value = tableDNDComputeNewValue(table, row, data_name);
        base_url = row.cells[3].children.item('a').href;
        $.ajax({
          url: base_url + "/" + view_name,
          dataType: 'html',
          data: {moveType:'number',
                 wishedNumber:parseFloat(new_value)/100},
          cache: false,
          success: function(data) {
            Faceted.URLHandler.hash_changed();
            start_meeting_scroll_to_item_observer(tag=null, row_id=row_id);
          },
          error: function(jqXHR, textStatus, errorThrown) {
            /*console.log(textStatus);*/
            window.location.href = window.location.href;
            }
          });
       },
       dragHandle: ".draggable",
       onDragClass: "dragindicator dragging",

    });
}

/* dnd for attendees on an item */
function initializeItemAttendeesDND() {
    let data_name = "attendee_number";
    let view_name = "@@item-change-attendee-order";
    $('table.faceted-table-results').tableDnD({
      onDrop: function(table, row) {
        row_id = row.id;
        new_value = tableDNDComputeNewValue(table, row, data_name);
        base_url = canonical_url();
        $.ajax({
          url: base_url + "/" + view_name,
          dataType: 'html',
          data: {attendee_uid: row.cells[2].dataset.attendee_uid,
                 'position:int': parseInt(new_value)},
          cache: false,
          success: function(data) {
            refresh_attendees(highlight=['.td_cell_number-column', '.th_header_number-column']);
          },
          error: function(jqXHR, textStatus, errorThrown) {
            /*console.log(textStatus);*/
            window.location.href = window.location.href;
            }
          });
      },
      dragHandle: ".draggable",
      onDragClass: "dragindicator dragging"
    });
}

// do not redefine window.onbeforeunload or it breaks form unload protection
$(document).ready(function () {
    localStorage.removeItem("toggleAllDetails");
});

function toggleAllDetails() {
  state = localStorage.getItem("toggleAllDetails");
  if (!state || state == "1") {
    localStorage.setItem("toggleAllDetails", "0");
    $('.collapsible.active:not(.not-auto-collapsible-deactivable)').each(function() {$(this).click();});
  } else {
    localStorage.setItem("toggleAllDetails", "1");
    $('.collapsible:not(.active):not(.not-auto-collapsible-activable)').each(function() {$(this).click();});
  }
}

function selectAllVoteValues(tag, group_id, vote_value) {
  if (group_id == 'all') {
    $('table#form-widgets-votes input[value='+vote_value+']').each(function() {
      this.checked = true;
      }
    );
  } else {
        $('tr.'+group_id+' input[value='+vote_value+']').each(function() {
      this.checked = true;
      }
    );}
}

/* while scrolling on meeting manage available items sticky table header */
function onScrollMeetingView() {
  var iframe = $("iframe");
  if (iframe.length) {
    iframe_top = $("iframe")[0].getBoundingClientRect().top;
    if ((iframe_top ) < 0) {
      table = $("iframe").contents().find('table#faceted_table');
      header = $("iframe").contents().find('table thead');
      if (table.length && header.length) {
        table_top = table.offset().top;
        portal_header_height = $("#portal-header").height();
        $("th", header).css("top",
                            (table_top - iframe_top - (table_top - portal_header_height)).toString() + "px");
      }
    } else {
        /* reset the th top when outside iframe so header
           does not end lost in the middle of the table */
        th = $("iframe").contents().find('table thead th');
        if (th.length) {
            $(th).css("top", "0px");
        }
    }
  }
}


function initReadmore() {

var $el, $up;

/* first check if need to use readmorable or not, only if content > set CSS max-height + 100px */
$("div.readmorable").each(function() {
  $el = $(this);
  /* get max-height defined in CSS for div.readmorable {} */
  cssMaxHeight = parseInt(getComputedStyle(this).maxHeight);
  this.style = "max-height: none";
  if (this.offsetHeight > cssMaxHeight + 100) {
    $el.addClass("enabled");
  }
  else {
    $el.addClass("disabled");
  }
  this.style = "";
});

$("div.readmorable p.readmore").click(function() {

  event.preventDefault();

  $el = $(this);
  $up  = $el.parent();
  $up[0].classList.toggle("opened");
  $el.hide();
  $("p.readless", $up).show();

  return false;
});

$("div.readmorable p.readless").click(function() {

  event.preventDefault();
  $el = $(this);
  $up = $el.parent();
  $up[0].classList.toggle("opened");
  $el.hide();
  $("p.readmore", $up).show();

  return false;
});
}

// utility method that will scroll to a position with an offset
function _scrollTo(el, yOffset = 0){
  const y = el.getBoundingClientRect().top + window.pageYOffset + yOffset;
  window.scrollTo({top: y, behavior: 'smooth'});
}

// function that scroll to a row in a dashboard
function scrollToRow(row) {
    // goto row
    header_height = $("#portal-header").height();
    _scrollTo(row, - 200 -header_height);
    // highlight row
    tds = $('td', row);
    tds.each(function(){
        $(this).effect('highlight', {}, 5000);
        }
    );
}

// mutation observer necessary to scroll to a position in a dashboard
// because when document is loaded, the faceted results are loaded by an ajax query
// and scrollToRow need the element to be visible
const observer = new MutationObserver((mutations, obs) => {
  var row_id = null;
  if (localStorage.getItem("dashboardRowId", null)) {
    row_id = localStorage.getItem("dashboardRowId", null);
  }
  if (row_id) {
    row_id_tag = document.getElementById(row_id);
    if (row_id_tag) {
      scrollToRow(row_id_tag);
      obs.disconnect();
      localStorage.removeItem("dashboardRowId");
      return;
    }
  }
  else {
      obs.disconnect();
      return;
  }

});

// start meeting observer when on meeting view
// it is used when needed to scroll to an item position when faceted is refreshed
function start_meeting_scroll_to_item_observer(tag=null, row_id=null) {
    if (isMeeting()) {
        if (tag) {
            row_id = null;
            /* tag comes from actions_panel, may be in tooltipster or not,
               this does not work when using actions_panel in tooltipster
               and adding a comment when a transition is triggered */
            if ($(tag).parents("table[id^='actions-panel-identifier-']").length) {
                actions_panel_table = $(tag).parents("table[id^='actions-panel-identifier-']")[0];
                row_id = "row_" + actions_panel_table.id.split("-")[3];
            }
            if ($(tag).parents("tr[id^='row_']").length) {
                row_id = $(tag).parents("tr[id^='row_']")[0].id;
            }
            localStorage.setItem("dashboardRowId", row_id);
        } else if (row_id) {
            localStorage.setItem("dashboardRowId", row_id);
        }
        observer.observe(document, {
          childList: true,
          subtree: true
        });
    }
}

$(document).ready(function () {
    start_meeting_scroll_to_item_observer();
});

$(document).ready(function () {

    $("body.portaltype-meetingconfig input.context[type='submit']").click(function() {
      $("div.ArchetypesInAndOutWidget").each(
        function() {inout_selectAllWords(this.dataset.fieldname);});
    });
});
