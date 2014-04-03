from plone.testing import layered

import robotsuite

from Products.PloneMeeting.testing import PM_TESTING_ROBOT


def test_suite():
    return layered(robotsuite.RobotTestSuite('robot/views.robot'),
                   layer=PM_TESTING_ROBOT)