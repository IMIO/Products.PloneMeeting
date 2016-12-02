// Dropdown for selecting an annex type
var ploneMeetingSelectBoxes = new Object();
function displayPloneMeetingSelectBox(selectName) {
  var box = document.getElementById(ploneMeetingSelectBoxes[selectName]["box"]);
  var button = document.getElementById(ploneMeetingSelectBoxes[selectName]["button"]);
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

  var btnImage = document.getElementById(ploneMeetingSelectBoxes[selectName]["image"])
  var btnText = document.getElementById(ploneMeetingSelectBoxes[selectName]["buttonText"])

  document.getElementById(ploneMeetingSelectBoxes[selectName]["button"]).style.borderStyle = "outset";
  document.getElementById(ploneMeetingSelectBoxes[selectName]["box"]).style.display="none";
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
/* When several menubars are present on a page, when a menu is shown in a
   menubar, it may be displayed under another menu bar. This function solves
   this problem by assigning a special style "onTop" with a high z-style
   value to the menubar currently displayed.
*/
function bringForward(elem) {
    /* Put backward all annexes groups and popups (excepted the current one) */
    var annexGroups = $('table.contentActionsAX');
    var currentAnnexGroup = findParent(elem, "contentActionsAX");
    for (var i=0; i < annexGroups.length; i++) {
        if (annexGroups[i] == currentAnnexGroup){
            removeClassName(annexGroups[i], 'onBottom')
            addClassName(annexGroups[i], 'onTop')
        }
        else {
            removeClassName(annexGroups[i], 'onTop')
            addClassName(annexGroups[i], 'onBottom')
        }
    }
}
function hideAllMenusAX(node) {
    var menus = $('dl.actionMenuAX', node);
    for (var i=0; i < menus.length; i++) {
        replaceClassName(menus[i], 'activated', 'deactivated', true);
    }
}
function toggleMenuHandlerAX(event) {
    if (!event) var event = window.event; // IE compatibility

    // terminate if we hit a non-compliant DOM implementation
    // returning true, so the link is still followed
    if (!W3CDOM){return true;}
    var container = findParent(this, "actionMenuAX");
    if (!container) return true;
    // check if the menu is visible
    if (hasClassName(container, 'activated')) {
        // it's visible - hide it
        replaceClassName(container, 'activated', 'deactivated', true);
    } else {
        // it's invisible - make it visible (and hide all others except if a container)
        if (!findParent(container, "actionMenuAX")) {
            hideAllMenusAX()
        }
        else {
            hideAllMenusAX(findParent(container, "actionMenuAX"))
        }
        bringForward(this);
        replaceClassName(container, 'deactivated', 'activated', true);
    }
    return false;
}
function hideMenusHandlerAX(event) {
    if (!event) var event = window.event; // IE compatibility
    // hideAllMenusAX();
    return true;
}
function actionMenuDocumentMouseDownAX(event) {
    if (!event) var event = window.event; // IE compatibility
    if (event.target)
        targ = event.target;
    else if (event.srcElement)
        targ = event.srcElement;
    var container = findParent(targ, "actionMenuAX");
    if (container) {
        // targ is part of the menu, so just return and do the default
        return true;
    }
    hideAllMenusAX();
    return true;
}
function actionMenuMouseOverAX(event) {
    if (!event) var event = window.event; // IE compatibility

    if (!this.tagName && (this.tagName == 'A' || this.tagName == 'a')) {
        return true;
    }
    var container = findParent(this, "actionMenuAX");
    if (!container) {
        return true;
    }
    var menu_id = container.id;

    var switch_menu = false;
    // hide all menus
    var menus = $('dl.actionMenuAX');
    for (var i=0; i < menus.length; i++) {
        var menu = menus[i]
        // check if the menu is visible
        if (hasClassName(menu, 'activated')) {
            switch_menu = true;
        }
        // turn off menu when it's not the current one
        if (menu.id != menu_id) {
            replaceClassName(menu, 'activated', 'deactivated', true);
        }
    }
    if (switch_menu) {
        var menu = $('#'+menu_id)[0];
        if (menu) {
            bringForward(this);
            replaceClassName(menu, 'deactivated', 'activated', true);
        }
    }
    return true;
}

function initializeMenusAXStartingAt(node) {
  // Initializes menus starting at a given node in the page.
  // First, terminate if we hit a non-compliant DOM implementation
  if (!W3CDOM) {return false;}
  document.onmousedown = actionMenuDocumentMouseDownAX;
  hideAllMenusAX(node);

  // Add toggle function to header links
  var menu_headers = $('dl.actionMenuAX > dt.actionMenuHeaderAX > a', node);
  for (var i=0; i < menu_headers.length; i++) {
    var menu_header = menu_headers[i];
    menu_header.onclick = toggleMenuHandlerAX;
  }
  // Add hide function to all links in the dropdown, so the dropdown closes
  // when any link is clicked
  var menu_contents = $('dl.actionMenuAX > dd.actionMenuContentAX', node);
  for (var i=0; i < menu_contents.length; i++) {
        menu_contents[i].onclick = hideMenusHandlerAX;
  }
}

function initializeMenusAX() {
  initializeMenusAXStartingAt(document);
};

registerPloneFunction(initializeMenusAX);

/* used in configuration to show/hide documentation */
function toggleDoc(id) {
  elem = $('#' + id);
  elem.fadeToggle();
}

function toggleMenu(menuId){
  /* we may have '.' in the id and it fails while using directly $(selector)
   * because it thinks we are using a CSS class selector so use getElementById */
  menu = $(document.getElementById('pm_menu_' + menuId));
  menu.fadeToggle(100);
  return
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
};

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
};

// Function that toggles the persons visibility
function togglePersons() {
  persons = document.getElementById('meeting_users_');
  if (!persons) persons = document.getElementById('meeting_users');
  if (!persons) return;
  show = readCookie('showPersons');
  if (!show) show = 'true';
  if (show == 'true') {
    createCookie('showPersons', 'false');
    persons.style.display = 'none';
  }
  else {
    createCookie('showPersons', 'true');
    persons.style.display = 'table';
  }
};

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
};

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

function closeDialog(dialogId) {
  // Close the dialog window
  var dialog = document.getElementById(dialogId);
  dialog.style.display = "none";
  // Hide the greyed zone
  var greyed = document.getElementById('hsGrey');
  greyed.style.display = "none";
  // Empty the global variable dialogData
  dialogData = null;
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
       (xhrObjects[pos].freed == 0)) {
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
      rq.xhr.setRequestHeader("Content-length", paramsFull.length);
      rq.xhr.setRequestHeader("Connection", "close");
      rq.xhr.onreadystatechange = function(){ getAjaxChunk(pos); }
      rq.xhr.send(paramsFull);
    }
    else if (mode == 'GET') {
      rq.xhr.onreadystatechange = function() { getAjaxChunk(pos); }
      if (window.XMLHttpRequest) { rq.xhr.send(null); }
      else if (window.ActiveXObject) { rq.xhr.send(); }
    }
  }
}

// Triggers recording of item-people-related info like votes, questioners, answerers.
function saveItemPeopleInfos(itemUrl, allVotesYes) {
  // If "allVotesYes" is true, all vote values must be set to "yes".
  theForm = document.forms["itemPeopleForm"];
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

// Welcome a user in a meeting at some point.
function welcomeUser(itemUrl, userId, action){
  if (confirm(are_you_sure)) {
    var params = {'action': 'WelcomePerson', 'userId': userId, 'actionType': action};
    askAjaxChunk('meeting_users_', 'POST', itemUrl, '@@pm-macros', 'itemPeople', params);
  }
}

function confirmByebyeUser(itemUrl, userId, actionType, byeType){
  dialogData = {'action': 'ByebyePerson', 'itemUrl': itemUrl,
                'userId': userId, 'actionType': actionType, 'byeType':byeType};
  if (actionType == "delete") {
    if (confirm(are_you_sure)) {
      delete dialogData['itemUrl'];
      askAjaxChunk('meeting_users_', 'POST', itemUrl, '@@pm-macros', 'itemPeople', dialogData);
    }
  }
  else openDialog('confirmByebyeUser');
}

// Note that a user lefts a meeting after some point.
function byebyeUser(widget) {
  itemUrl = dialogData['itemUrl'];
  delete dialogData['itemUrl'];
  // Does the user leave after this item, or does he leave only while this item is discussed?
  leavesAfter = document.getElementById('leaves_after');
  if (leavesAfter.checked) byeType = 'leaves_after';
  else byeType = 'leaves_now';
  dialogData['byeType'] = byeType
  askAjaxChunk('meeting_users_', 'POST', itemUrl, '@@pm-macros', 'itemPeople', dialogData);
  closeDialog('confirmByebyeUser');
}

function setByeByeButton(userId, visibility) {
  var button = document.getElementById('byebye_' + userId);
  if (!button) return;
  button.style.visibility = visibility;
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
    if ($img.attr('onclick') == null) {
        $img.click(function() {
            asyncToggleIcon(UID, baseUrl, viewName, baseSelector);
        });
    };
    // special management for the toggle budgetRelated where we need to display
    // or hide the budgetInfos field.  If budgetRelated, we show it, either we hide it...
    $hook_budgetInfos = $('#hook_budgetInfos');
    if (viewName == '@@toggle_budget_related') {
        if (img_tag.indexOf('nameBudgetRelatedNo') > 0) {
        $('#hideBudgetInfosIfNotBudgetRelated')[0].style.display = 'block';
        $hook_budgetInfos.fadeIn("fast");
        $hook_budgetInfos.show();
        }
        else {
            // find the 'hook_budgetInfos' and removes it
            $hook_budgetInfos.fadeOut("fast", function() {
                   $(this).hide();
               });
        };
    };
  };
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
    tool.addForms.apply(tool, $('form.enableUnloadProtection').get());
    // enable UnlockHandler so element is correctly unlocked after edit
    plone.UnlockHandler.init()
    
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
  return params
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
          params = $.param({'uids:list': uids}, traditional=true)
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
          params = $.param({uids: uids}, traditional=true)
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

// Function that allows to decide several items at once in a meeting
function decideSelectedItems(baseUrl,tag){
    var uids = selectedCheckBoxes('select_item');
    if (!uids.length) {
      alert(no_selected_items);
    }
    else {
          // avoid Arrays to be passed as uids[]
          params = $.param({uids: uids, transition: tag.name}, traditional=true)
          $.ajax({
            url: baseUrl + "/@@decide-several-items",
            dataType: 'html',
            data: params,
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
function callViewAndReload(baseUrl, view_name, tag, params) {
  redirect = '0';
  if (!$('#faceted-form').has(tag).length) {
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

// update the number of items displayed on the meeting_view when items have been presented/removed of the meeting
function updateNumberOfItems(infos) {
  // get numberOfItems using an ajax call
  response = $.ajax({
    url: document.baseURI + '/numberOfItems',
    dataType: 'html',
    cache: false,
    async: false});
  parent.$('.meeting_number_of_items').each(function() {
      this.innerHTML = response.responseText;
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

budgetRelated = $('input#budgetRelated')
if (budgetRelated.length) {
  budgetInfos = $('#archetypes-fieldname-budgetInfos');
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
  };
  });

}

});


// called on each faceted table change to update the portlet_todo
$(document).ready(function () {
  var url = $('base').attr('href') + '/@@portlet-todo-update';
  $(Faceted.Events).bind(Faceted.Events.AJAX_QUERY_SUCCESS, function() {
      $.get(url, function (data) {
          tag = $('dl.portlet.portletTodo');
          if (tag.length) {
            tag[0].parentNode.innerHTML = data;
          }
          
      })
  });
});

/* Disable caching of AJAX responses when using IE,
   otherwise, the double ajax call on the meeting (available and presented items)
   will display the same result... */
if (/msie/.test(navigator.userAgent.toLowerCase())) {
  $.ajaxSetup ({ 
    cache: false }); 
}

// tool tip, gently borrowed from
// https://github.com/collective/collective.contact.widget/blob/master/src/collective/contact/widget/js/widget.js.pt
$(document).ready(function() {

  var pendingCall = {timeStamp: null, procID: null};
  $(document).on('mouseleave', '.link-tooltip', function() {
    if (pendingCall.procID) {
      clearTimeout(pendingCall.procID);
      pendingCall.procID = null;
    }
    // if computed tooltip is still the wait_msg, destroy it
    trigger = $(this);
    tooltip = trigger.next('div.tooltip');
    if (tooltip && tooltip.html() === wait_msg) {
      tooltip.remove();
      trigger.removeData('tooltip');
    }
  });
  $(document).on('mouseenter', '.link-tooltip', function() {
    var trigger = $(this);
    // don't open tooltip in tooltip
    if (trigger.closest('.tooltip').length) {
        return;
    }
    if (!trigger.data('tooltip')) {
      if (pendingCall.procID) {
        clearTimeout(pendingCall.procID);
      }
      var timeStamp = new Date();
      var tip = $('<div class="tooltip pb-ajax" style="display:none">' + wait_msg + '</div>')
            .insertAfter(trigger);
      trigger.tooltip({relative: true, position: "center right"});
      var tooltip = trigger.tooltip();
      tooltip.show();
      var url = trigger.attr('href');
      var tooltipCall = function() {
          $.get(url, {ajax_load: new Date().getTime()}, function(data) {
            tooltip.hide();
            tooltip.getTip().html($('<div />').append(
                    data.replace(/<script(.|\s)*?\/script>/gi, ""))
                .find(common_content_filter));
            if (pendingCall.timeStamp == timeStamp) {
                tooltip.show();
            }
            pendingCall.procID = null;
          });
      }
      pendingCall = {timeStamp: timeStamp,
                     procID: setTimeout(tooltipCall, 0)};
    }
  });
});
