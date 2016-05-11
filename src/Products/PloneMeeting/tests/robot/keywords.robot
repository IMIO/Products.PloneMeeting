*** Keywords ***

ConnectAs
    [Arguments]  ${login}  ${mdp}
    Go to  ${PLONE_URL}
    Log in  ${login}  ${mdp}
