*** Keywords ***

ConnectAs
    [Arguments]  ${login}  ${mdp}
    Go to  ${PLONE_URL}
    Log in  ${login}  ${mdp}

Select collection
    [Documentation]  Click element of the collection widget corresponding to given path
    [Arguments]  ${col_path}  ${results}=1  ${widget_name}=c1
    ${UID} =  Path to uid  /${PLONE_SITE_ID}/${col_path}
    Click element  ${widget_name}${UID}
    Run keyword if  '${results}'=='1'  Wait until element is visible  css=.faceted-table-results  10  ELSE  Wait until element is visible  css=.table_faceted_no_results  10
    Sleep  1

Click and Screenshot overlayForm
    [Arguments]  ${locator}  ${image_title}  ${screen_zone}
    Click element  ${locator}
    Sleep  1
    wait until element is visible  ${screen_zone}  2
    Sleep  1
    Capture and crop page screenshot  ${image_title}  ${screen_zone}

Scroll Page
    [Arguments]  ${x_location}  ${y_location}
    Execute JavaScript  window.scrollTo(${x_location},${y_location})

Wait Until Page Loaded And Element Enabled
    [Arguments]  ${locator}
    Wait Until Element Is Visible  ${locator}  10
    Wait Until Element Is Not Visible  css=.faceted-lock-overlay  10
    Wait Until Element Is Enabled  ${locator}  10