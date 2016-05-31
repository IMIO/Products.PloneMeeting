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