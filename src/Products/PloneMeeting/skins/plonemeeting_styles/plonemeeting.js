// Function that shows a popup that asks the user if he really wants to delete
function confirmReinitializeDelay(base_url, advice, tag, msgName){
    if (!msgName) {
        msgName = 'reinit_delay_confirm_message';
    }
    var msg = window.eval(msgName);
    if (confirm(msg)) {
        callViewAndReload(base_url, view_name='@@advice-reinit-delay', tag, params={'advice': advice});
    }
}

// function that show/hide icons to manage attendees (absents, signatories, ...)
function setHiddenButton(userId, visibility, prefix='byebye_') {
  var button = document.getElementById(prefix + userId);
  if (!button) return;
  button.style.visibility = visibility;
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

/* used in configuration to show/hide documentation */
function toggleDoc(id, toggle_parent_active=true, parent_elem=null, load_view=null) {
  elem = $('#' + id);
  elem.slideToggle(200);
  if (toggle_parent_active) {
    if (!parent_elem) {
      parent_elem = elem.prev()[0];
    }
    parent_elem.classList.toggle("active");
  }

  inner_content_tag = $('div.collapsible-inner-content', elem)[0];
  if (load_view && !inner_content_tag.dataset.loaded) {
    // load content in the collapsible-inner-content div
    var url = $("link[rel='canonical']").attr('href') + '/' + load_view;
    $.ajax({
      url: url,
      dataType: 'html',
      data: {},
      cache: false,
      async: true,
      success: function(data) {
        inner_content_tag.innerHTML = data;
        inner_content_tag.dataset.loaded = true;
      },
      error: function(jqXHR, textStatus, errorThrown) {
        /*console.log(textStatus);*/
        window.location.href = window.location.href;
        }
    });
  }
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
    label_tag.classList.add('active');
    tag.style.display = 'block';
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
}

// Triggers recording of item-people-related info like votes, questioners, answerers.
function saveItemPeopleInfos(itemUrl, allVotesYes) {
  // If "allVotesYes" is true, all vote values must be set to "yes".
  theForm = document.forms.itemPeopleForm;
  params = {'action': 'SaveItemPeopleInfos', 'allYes': allVotesYes};
  // Collect params to send via the AJAX request.
  for (var i=0; i<theForm.elements.length; i++) {
    widget = theForm.elements[i];
    if ((widget.type == "text") || widget.checked) {
      params[widget.name] = widget.value;
    }
  }
  askAjaxChunk('meeting_users_', 'POST', itemUrl, '@@pm-macros', 'itemPeople', params);
}

// Refresh the vote values
function refreshVotes(itemUrl) {
  askAjaxChunk('meeting_users_', 'POST', itemUrl, '@@pm-macros', 'itemPeople');
}
// Switch votes mode (secret / not secret)
function switchVotes(itemUrl, secret) {
  var params = {'action': 'SwitchVotes', 'secret': secret};
  askAjaxChunk('meeting_users_', 'POST', itemUrl, '@@pm-macros', 'itemPeople', params);
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

/* functions used to manage quick edit functionnality */
function initRichTextField(rq, hook) {
  /* Function that needs to be called when getting the edit view of a
     rich-text field through Ajax. */
  /* Check that we can actually edit the field, indeed the object
   * could have been locked in between (concurrent edit) */
  is_locked = $.ajax({
     async: true,
     type: 'GET',
     url: '@@plone_lock_info/is_locked_for_current_user',
     success: function(data) {
          //callback
     }
    });
  if (is_locked.responseText === "True") {
    window.location.href = window.location.href;
  }
  else {
    // Javascripts inside this zone will not be executed. So find them
    // and trigger their execution here.
    var scripts = $('script', hook);
    var fieldName = rq.hook.substring(5);
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
    // Initialize CKeditor if it is the used editor
    if (ploneEditor == 'CKeditor') { jQuery(launchCKInstances([fieldName,])); }
    // Enable unload protection, avoid loosing unsaved changes if user click somewhere else
    var tool = window.onbeforeunload && window.onbeforeunload.tool;
    if (tool!==null) {
      tool.addForms.apply(tool, $('form.enableUnloadProtection').get());
    }
    // enable UnlockHandler so element is correctly unlocked after edit
    plone.UnlockHandler.init();
  }
}
function getRichTextContent(rq, params) {
  /* Gets the content of a rich text field before sending it through an Ajax
     request. */
  var fieldName = rq.hook.substring(5);
  var formId = 'ajax_edit_' + fieldName;
  var theForm = document.getElementById(formId);
  var theWidget = theForm[fieldName];
  if (ploneEditor == 'CKeditor'){
     /* with CKeditor the value is not stored in the widget so get the data from the real CKeditor instance */
     theWidget.value = CKEDITOR.instances[fieldName].getData();
     CKEDITOR.instances[fieldName].destroy();
  }
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
function onImageButtonFocus(itemNumber) {
  var imageButtons = document.getElementsByName('moveImageButton');
  for (var i=0; i<imageButtons.length; i++) {
      if (imageButtons[i].id != 'moveAction_' + itemNumber) {
          imageButtons[i].style.visibility = 'hidden';
      }
      else {
          imageButtons[i].style.visibility = 'visible';
          imageButtons[i].style.cursor = 'pointer';
          document.getElementById('value_moveAction_' + itemNumber).select();
      }
  }
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
    },
    error: function(jqXHR, textStatus, errorThrown) {
      /*console.log(textStatus);*/
      window.location.href = window.location.href;
      }
    });
}

// ajax call managing a call to a given p_view_name and reload taking faceted into account
function callViewAndReload(baseUrl, view_name, tag, params, force_faceted=false) {
  redirect = '0';
  if (!force_faceted && !has_faceted()) {
    redirect = '1';
  }
  $.ajax({
    url: baseUrl + "/" + view_name,
    data: params,
    dataType: 'html',
    cache: false,
    async: true,
    success: function(data) {
        // reload the faceted page if we are on it, refresh current if not
        if ((redirect === '0') && !(data)) {
            Faceted.URLHandler.hash_changed();
        }
        else {
            window.location.href = data;
        }
    },
    error: function(jqXHR, textStatus, errorThrown) {
      /*console.log(textStatus);*/
      window.location.href = window.location.href;
      }
    });
}

// event subscriber when a transition is triggered
$(document).on('ap_transition_triggered', synchronizeMeetingFaceteds);
// synchronize faceted displayed on the meeting_view, available items and presented items
function synchronizeMeetingFaceteds(infos) {
    // refresh iframe 'available items' while removing an item
    if ((infos.transition === 'backToValidated') && ((window.frames[0]) && (window.frames[0] != window))) {
      window.frames[0].Faceted.URLHandler.hash_changed();
      updateNumberOfItems();
    }
    // refresh main frame while presenting an item
    if ((infos.transition === 'present') && (window != parent)) {
      parent.Faceted.URLHandler.hash_changed();
      updateNumberOfItems();
    }
}

// event subscriber when a element is delete in a dashboard, refresh numberOfItems if we are on a meeting
$(document).on('ap_delete_givenuid', updateNumberOfItems);

// update the number of items displayed on the meeting_view when items have been presented/removed of the meeting
function updateNumberOfItems() {
  // get numberOfItems using an ajax call
  response = $.ajax({
    url: document.baseURI + '/numberOfItems',
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
    async: false,
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


function update_search_term(tag){
  var url = $("link[rel='canonical']").attr('href') + '/@@async_render_search_term';
  $.ajax({
    url: url,
    dataType: 'html',
    data: {collection_uid: tag.dataset.collection_uid},
    cache: false,
    // async: true provokes ConflictErrors when freezing a meeting
    async: false,
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

function initializeItemsDND(){
$('table.faceted-table-results').tableDnD({
  onDrop: function(table, row) {
    row_index = row.rowIndex;
    // id is like row_200
    row_item_number = parseInt(table.rows[row.rowIndex].cells[2].dataset.item_number);
    // find if moving up or down
    move_type = 'up';
    if (table.tBodies[0].rows.length > row_index) {
         // we have a next row, compare with it
         next_row_item_number = parseInt(table.rows[row.rowIndex + 1].cells[2].dataset.item_number);
         if (row_item_number < next_row_item_number) {
             move_type = 'down';
         }
    } else {move_type = 'down';}
    
    // now that we know the move, we can determinate number to use
    if (move_type == 'down') {
      new_value = parseInt(table.rows[row.rowIndex - 1].cells[2].dataset.item_number);
    } else {
      new_value = parseInt(table.rows[row.rowIndex + 1].cells[2].dataset.item_number);
    }
    base_url = row.cells[3].children.item('a').href;
    $.ajax({
      url: base_url + "/@@change-item-order",
      dataType: 'html',
      data: {moveType:'number',
             wishedNumber:parseFloat(new_value)/100},
      cache: false,
      success: function(data) {
        Faceted.URLHandler.hash_changed();
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
