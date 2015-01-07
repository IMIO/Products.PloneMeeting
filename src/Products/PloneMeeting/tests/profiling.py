# -*- coding: utf-8 -*-
#
# Copyright (c) 2015 by Imio.be
#
# GNU General Public License (GPL)
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#
# ------------------------------------------------------------------------------

import time
import logging
logger = logging.getLogger('PloneMeeting')

# ------------------------------------------------------------------------------
class ProfilingError(Exception): pass
NO_LEAVE_TIME = 'I cannot compute duration of this call, the leaveTime is ' \
                'unknown.'
CALL_STACK_ERROR = "Problem with the method call stack: we did not enter any " \
                   "method, so we can't leave a method now."
# ------------------------------------------------------------------------------
class MethodCall:
    '''Stores information about a method call.'''
    def __init__(self, methodName, enterTime, method=None):
        self.methodName = methodName # The name of the called method
        self.method = method # The method
        self.enterTime = enterTime # Whe did we enter the method ?
        self.leaveTime = None # When did we leave the method ?

    def duration(self):
        '''How long did the call lasted (in seconds) ?'''
        if not self.leaveTime:
            raise ProfilingError(NO_LEAVE_TIME)
        return self.leaveTime - self.enterTime

class PloneMeetingProfiler:
    '''Allows to do simple profiling throughout PloneMeeting code.'''
    def __init__(self, mustLog=False, mustPrint=True):
        self.mustLog = mustLog # Must I log profiling results to Zope log ?
        self.mustPrint = mustPrint # Must I print profiling results to stdout?
        self.callStack = [] # Stack of profiled method calls
        self.durations = {} # ~{m_methodName: f_totalTimeInMethod}~

    def log(self, msg):
        # First, indent the message for readability
        blanks = ' ' * 2 * len(self.callStack)
        message = blanks + msg
        if self.mustLog:
            logger.log(message)
        if self.mustPrint:
            print message

    def enter(self, method):
        '''Is called when entering a given method.'''
        enterTime = time.time()
        if isinstance(method, basestring):
            methodName = method
            theMethod = None
        else:
            methodName = method.__name__
            theMethod = method
        if not self.callStack:
            self.log('Entering %s...' % methodName)
        self.callStack.append(MethodCall(methodName, enterTime, theMethod))
        if not self.durations.has_key(methodName):
            self.durations[methodName] = 0

    def leave(self):
        '''Is called when leaving a given method.'''
        if not self.callStack:
            raise ProfilingError(CALL_STACK_ERROR)
        methodCall = self.callStack.pop()
        methodCall.leaveTime = time.time()
        self.durations[methodCall.methodName] += methodCall.duration()
        if not self.callStack:
            self.log('Leaving %s.' % methodCall.methodName)
            self.log('Total durations in methods:')
            for methodName, duration in self.durations.iteritems():
                self.log('  %s: %f second(s)' % (methodName, duration))
            # Reinitialise profiler
            self.__init__(self.mustLog, self.mustPrint)

# ------------------------------------------------------------------------------
# Default available profiler
profiler = PloneMeetingProfiler()
# ------------------------------------------------------------------------------
