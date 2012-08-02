// Function for opening the popup window (HubSessions-improved)
function classifier_referencebrowser_openBrowser(path, fieldName, at_url, fieldRealName) {
  if (window.screen) {
    var w = window.screen.availWidth - 100;
    var h = window.screen.availHeight - 100;
    var left = parseInt((window.screen.availWidth/2) - (w/2));
    var top = parseInt((window.screen.availHeight/2) - (h/2));
  }
  else {
    var w = 700;
    var h = 550;
    var left = 50;
    var top = 50;
  }
  var windowAttrs = 'width=' + w + ',height=' + h + ',left=' +
    left + ',top=' + top + ',screenX=' + left + ',screenY=' + top +
    ',toolbar=no,menubar=no,scrollbars=yes,status=no,resizable=yes';
  // Popup will appear at the center of the screen
  atrefpopup = window.open(path + '/referencebrowser_popup?fieldName=' +
    fieldName + '&fieldRealName=' + fieldRealName +'&at_url=' + at_url,
    'referencebrowser_popup', windowAttrs);
}

// function to return a reference from the popup window back into the widget
function classifier_referencebrowser_setReference(widget_id, uid, label, multi)
{
    // differentiate between the single and mulitselect widget
    // since the single widget has an extra label field.
    if (multi==0) {
        element=document.getElementById(widget_id)
        label_element=document.getElementById(widget_id + '_label')
        element.value=uid
        label_element.value=label
     }  else {
         // check if the item isn't already in the list
         var current_values = cssQuery('#' + widget_id + ' input');
         for (var i=0; i < current_values.length; i++) {
            if (current_values[i].value == uid) {
              return false;
            }
          }         
          // now add the new item
          list=document.getElementById(widget_id);
          li = document.createElement('li');
          label_element = document.createElement('label');
          input = document.createElement('input');
          input.type = 'checkbox';
          input.value = uid;
          input.checked = true;
          input.name = widget_id + ':list';
          label_element.appendChild(input);
          label_element.appendChild(document.createTextNode(label));
          li.appendChild(label_element);
          list.appendChild(li);
          // fix on IE7 - check *after* adding to DOM
          input.checked = true;
     }
}

// function to clear the reference field or remove items
// from the multivalued reference list.
function classifier_referencebrowser_removeReference(widget_id, multi)
{
    if (multi) {
        list=document.getElementById(widget_id)
        for (var x=list.length-1; x >= 0; x--) {
          if (list[x].selected) {
            list[x]=null;
          }
        }
        for (var x=0; x < list.length; x++) {
            list[x].selected='selected';
          }        
    } else {
        element=document.getElementById(widget_id);
        label_element=document.getElementById(widget_id + '_label');
        label_element.value = "";
        element.value="";
    }
}


