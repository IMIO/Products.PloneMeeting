*** Settings ***
Resource  plone/app/robotframework/keywords.robot
Resource  plone/app/robotframework/selenium.robot

Library  Remote  ${PLONE_URL}/RobotRemote
Library  plone.app.robotframework.keywords.Debugging

Suite Setup  Suite Setup
Suite Teardown  Close all browsers

*** Test cases ***

# Test that after login, a user is redirected to the defaut MeetingConfig home page
Test Moved to default MeetingConfig home page after connection
    Log in  pmManager  Meeting_12
    Wait until element is visible  css=.table_faceted_no_results

*** Keywords ***
Suite Setup
    Open test browser
