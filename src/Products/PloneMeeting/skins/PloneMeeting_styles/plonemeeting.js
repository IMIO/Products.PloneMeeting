// Function for triggering a workflow transition
function triggerTransition(objectUid, transition, confirm, comment,
                           iStartNumber, lStartNumber) {
  var theForm = document.forms["formTriggerTransition"];
  theForm.objectUid.value = objectUid;
  theForm.transition.value = transition;
  if (comment) theForm.comment.value = comment;
  if (iStartNumber) theForm.iStartNumber.value = iStartNumber;
  if (lStartNumber) theForm.lStartNumber.value = lStartNumber;
  // Either we send the form directly, or we show a confirmation popup
  if (!confirm) { theForm.submit(); }
  else { openDialog('confirmTransitionDialog') }
}

/* Dropdown for selecting an annex type */
var ploneMeetingSelectBoxes = new Object();

function displayPloneMeetingSelectBox(selectName) {
  var box = document.getElementById(ploneMeetingSelectBoxes[selectName]["box"]);
  var button = document.getElementById(ploneMeetingSelectBoxes[selectName]["button"]);
  if (box.style.display!="block") {
    /* Button seems pressed */
    button.style.borderStyle = "inset";
    box.style.display = "block";
  }
  else {
    button.style.borderStyle = "outset";
    box.style.display= "none";
  }
}

function hidePloneMeetingSelectBox(selectName, idImage, msg, value, predefined_title) {
  var newImage = document.getElementById(idImage);

  var btnImage = document.getElementById(ploneMeetingSelectBoxes[selectName]["image"])
  var btnText = document.getElementById(ploneMeetingSelectBoxes[selectName]["buttonText"])

  document.getElementById(ploneMeetingSelectBoxes[selectName]["button"]).style.borderStyle = "outset";
  document.getElementById(ploneMeetingSelectBoxes[selectName]["box"]).style.display="none";
  btnText.innerHTML = msg;

  // Display
  btnImage.src = newImage.src;
  document.getElementById(ploneMeetingSelectBoxes[selectName]["hidden"]).value = value;
  document.annexForm.annex_title.value = predefined_title
}

function ploneMeetingSelectOnMouseOverItem(obj) {
  // Set the "selected" style
  obj.className = "ploneMeetingSelectItem ploneMeetingSelectItemUnselected";
}

function ploneMeetingSelectOnMouseOutItem(obj) {
  // Set the default style (unselected)
  obj.className = "ploneMeetingSelectItem";
}

function getEnclosingForm(elem) {
  // Gets the form that surrounds the HTML p_elem.
  var node = elem.parentNode;
  while (node.nodeName != "FORM") { node = node.parentNode; }
  return node;
}
/* Function that shows a popup that asks the user if he really wants to delete
   some object. If confirmed, the form where p_theElement lies is posted. */
function confirmDeleteObject(theElement, objectType){
    var msg = window.plonemeeting_delete_confirm_message;
    if (objectType == 'wholeMeeting') {
      msg = window.plonemeeting_delete_meeting_confirm_message;
    }
    else if (objectType == 'archivedMeetings') {
      msg = window.confirm_delete_archived_meetings;
    }
    if (confirm(msg)) { getEnclosingForm(theElement).submit(); }
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
    var annexGroups = cssQuery('table.contentActionsAX');
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
    var menus = cssQuery('dl.actionMenuAX', node);
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
        // it's invisible - make it visible (and hide all others)
        hideAllMenusAX()
        bringForward(this);
        replaceClassName(container, 'deactivated', 'activated', true);
    }
    return false;
}
function hideMenusHandlerAX(event) {
    if (!event) var event = window.event; // IE compatibility
    hideAllMenusAX();
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
    var menus = cssQuery('dl.actionMenuAX');
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
        var menu = cssQuery('#'+menu_id)[0];
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
  var menu_headers = cssQuery('dl.actionMenuAX > dt.actionMenuHeaderAX > a', node);
  for (var i=0; i < menu_headers.length; i++) {
    var menu_header = menu_headers[i];
    menu_header.onclick = toggleMenuHandlerAX;
  }
  // Add hide function to all links in the dropdown, so the dropdown closes
  // when any link is clicked
  var menu_contents = cssQuery('dl.actionMenuAX > dd.actionMenuContentAX', node);
  for (var i=0; i < menu_contents.length; i++) {
    menu_contents[i].onclick = hideMenusHandlerAX;
  }
}

function initializeMenusAX() {
  initializeMenusAXStartingAt(document);
};

registerPloneFunction(initializeMenusAX);

var wrongTextInput = '#ff934a none';
function gotoItem(inputWidget, totalNbOfItems, meetingUid) {
  // Go to meetingitem_view for the item whose number is in p_inputWidget
  try {
    var itemNumber = parseInt(inputWidget.value);
    if (!isNaN(itemNumber)) {
      if ((itemNumber>=1) && (itemNumber<=totalNbOfItems)) {
        var theForm = document.forms["formGotoItem"];
        theForm.objectId.value = itemNumber;
        theForm.meetingUid.value = meetingUid;
        theForm.submit();
      }
      else inputWidget.style.background = wrongTextInput;
    }
    else inputWidget.style.background = wrongTextInput;
  }
  catch (err) { inputWidget.style.background = wrongTextInput; }
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

// Function that, depending on p_mustShow, shows or hides the descriptions.
function setDescriptionsVisiblity(mustShow) {
  // First, update every description of every item
  var pmDescriptions = document.getElementsByName('pmDescription');
  for (var i=0; i<pmDescriptions.length; i++) {
    var elem = pmDescriptions[i];
    if (mustShow) { // Show the descriptions
      addClassName(elem, 'pmExpanded');
      elem.style.display = 'inline';
    }
    else { // Hide the descriptions
      removeClassName(elem, 'pmExpanded');
      elem.style.display = 'none';
    }
  }
  // Then, change the action icon/text and update the cookie
  var toggleElement = document.getElementById('document-action-toggledescriptions');
  if (mustShow) {
    if (toggleElement.tagName == 'IMG') {
      toggleElement.src = toggleElement.src.replace('/expandDescrs.gif',
                                                    '/collapseDescrs.gif');
    }
    createCookie('pmShowDescriptions', 'true');
  }
  else {
    if (toggleElement.tagName == 'IMG') {
      toggleElement.src = 'expandDescrs.gif';
      toggleElement.src = toggleElement.src.replace('/collapseDescrs.gif',
                                                    '/expandDescrs.gif');
    }
    createCookie('pmShowDescriptions', 'false');
  }
};

// Function that toggles the descriptions visibility
function toggleMeetingDescriptions() {
  if (readCookie('pmShowDescriptions')=='true') setDescriptionsVisiblity(false);
  else setDescriptionsVisiblity(true);
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

// Function that shows the form for adding or updating an advice
function editAdvice(itemUid, meetingGroupsIds, adviceType, comment) {
  var f = document.getElementById("editAdviceForm");
  // Remember the object UID
  f.itemUid.value = itemUid;
  // Populate the widget allowing to select the adviser group
  var sg = document.getElementById("editAdviceGroupSelect");
  for (var i=sg.options.length-1 ; i>=0 ; i--) sg.remove(i);
  var groupIds = meetingGroupsIds.split('??');
  for (var i=0; i < groupIds.length; i++) {
    var opt = document.createElement("OPTION");
    var groupInfo = groupIds[i].split('**');
    opt.value = groupInfo[0];
    opt.text = groupInfo[1].replace(/&nbsp;/g, ' ');
    sg.options.add(opt);
  }
  if (adviceType) {
    // Override the default advice type. Loop among radio buttons
    for (var i=0; i < f.adviceType.length; i++) {
      if (f.adviceType[i].value == adviceType) { f.adviceType[i].checked=true; }
      else { f.adviceType[i].checked = false; }
    }
  }
  // Populate the comment
  f.comment.value = comment.replace(/<br\/>/g, '\n');
  openDialog('editAdviceDialog');
}

// Function allowing to remove an event from an object's history
function deleteEvent(objectUid, eventTime) {
  var f = document.getElementById("deleteForm");
  // Store the object UID
  f.objectUid.value = objectUid;
  f.eventTime.value = eventTime;
  openDialog('deleteDialog');
}

var isIe = (navigator.appName == "Microsoft Internet Explorer");
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
      if (hookElem) hookElem.innerHTML = "<div align=\"center\"><img src=\"waiting.gif\"/><\/div>";
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
    var urlFull = url + '/ajax';
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
  askAjaxChunk('meeting_users_', 'POST', itemUrl, 'hs_macros', 'itemPeople', params);
}

// Refresh the vote values
function refreshVotes(itemUrl) {
  askAjaxChunk('meeting_users_', 'POST', itemUrl, 'hs_macros', 'itemPeople');
}
// Switch votes mode (secret / not secret)
function switchVotes(itemUrl, secret) {
  var params = {'action': 'SwitchVotes', 'secret': secret};
  askAjaxChunk('meeting_users_', 'POST', itemUrl, 'hs_macros', 'itemPeople', params);
}

// Welcome a user in a meeting at some point.
function welcomeUser(itemUrl, userId, action){
  if (confirm(are_you_sure)) {
    var params = {'action': 'WelcomePerson', 'userId': userId, 'actionType': action};
    askAjaxChunk('meeting_users_', 'POST', itemUrl, 'hs_macros', 'itemPeople', params);
  }
}

function confirmByebyeUser(itemUrl, userId, actionType, byeType){
  dialogData = {'action': 'ByebyePerson', 'itemUrl': itemUrl,
                'userId': userId, 'actionType': actionType, 'byeType':byeType};
  if (actionType == "delete") {
    if (confirm(are_you_sure)) {
      delete dialogData['itemUrl'];
      askAjaxChunk('meeting_users_', 'POST', itemUrl, 'hs_macros', 'itemPeople', dialogData);
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
  askAjaxChunk('meeting_users_', 'POST', itemUrl, 'hs_macros', 'itemPeople', dialogData);
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
  askAjaxChunk(hookId, 'GET', objectUrl, 'hs_macros', 'history', params);
}

//Function to toggle MeetingItem.itemIsSigned
function toggleItemIsSigned(UID, img_tag, baseUrl) {
  var selector = "#marker_toggle_itemissigned_" + UID;
  var $span = jq(selector);
  if ($span.length == 1) {
    var $old = jq('img', $span);
    $span.empty();
    var $img = jq(img_tag).appendTo($span);
    //Does not seem to work with IE?
    //$img.click(function() {
    //asyncItemIsSigned(UID, baseUrl);
    //});
  };
}

function asyncItemIsSigned(UID, baseUrl) {
  jq.ajax({
    url: baseUrl + "/signItem",
    dataType: 'html',
    data: {UID:UID},
    success: function(data) {
        toggleItemIsSigned(UID, data, baseUrl);
      },
    error: function(jqXHR, textStatus, errorThrown) {
      /*console.log(textStatus);*/
      }
    });
 }