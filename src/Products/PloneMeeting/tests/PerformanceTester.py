# ------------------------------------------------------------------------------
# GNU General Public License (GPL)

# ------------------------------------------------------------------------------
import sys
import re
import urlparse
import os
import os.path
import random
import time
import socket
from appy.shared.dav import Resource
from appy.shared.utils import FolderDeleter


class PerformanceTester:
    '''This class allows to connect to a Zope/Plone PloneMeeting server in HTTP
       and send him HTTP requests for testing its response times.'''

    def __init__(self, url, login=None, password=None):
        self.server = Resource(url, measure=True)
        self.login = login
        self.password = password
        # We will store hereafter the last HTTP response retrieved from the
        # server.
        self.resp = None
        # How many times will we run the test scenario ?
        self.numberOfTests = 2
        # For every test run, how many meetings, items and annexes will we
        # visit/download ?
        self.meetingsPerTest = 2
        self.itemsPerMeeting = 2
        self.annexesPerItem = 1
        # If the boolean hereafter is True, downloaded annexes will be saved to
        # disk, in a subFolder named "download" in the current folder. Be
        # careful: if this folder already exists, it will be removed completely.
        self.saveAnnexes = False
        if self.saveAnnexes:
            if os.path.exists('download'):
                FolderDeleter.delete('download')
                print 'Existing "download" folder was removed.'
            os.mkdir('download')

    def authenticate(self):
        '''Logs into the server.'''
        # Get the home page (so we know if the site is alive)
        try:
            self.resp = self.server.get()
        except socket.error, se:
            print 'URL "%s" is unreachable (%s).' % (self.server.url, str(se))
            sys.exit(-1)
        if not self.resp.code == 200:
            print 'URL "%s" is wrong (returned error %d).' % (self.server.url,
                                                              self.resp.code)
            sys.exit(-1)
        print self.resp, 'Got the home page at', self.server.uri
        # Define the parameters for the login
        data = {'form.submitted':1, 'came_from': self.server.url,
                'js_enabled': 0, 'cookies_enabled': '', 'login_name':'',
                'pwd_empty':0, '__ac_name': self.login,
                '__ac_password': self.password, 'submit': 'Connect'}
        self.resp = self.server.post(data, uri='%s/login_form' %self.server.url)
        if not self.resp.code == 302:
            print 'Authentication failed'
            sys.exit(-1)
        print self.resp, 'Authenticated'
        self.server.headers['Cookie'] = self.resp.headers['set-cookie']
        self.server.headers['Referer'] = self.server.url
        return self.resp

    def gotoHomePage(self):
        '''We must redirect the user to its home page as member.'''
        msg = 'Redirected to %s' % self.resp.data
        self.resp = self.server.get(uri=self.resp.data)
        print self.resp, msg
        if self.resp.code == 302:
            msg = 'Redirected to %s' % self.resp.data
            self.resp = self.server.get(uri=self.resp.data)
            print self.resp, msg

    trRex = re.compile('<tr(.*?)</tr>', re.S)
    hrefRex = re.compile('href="(.*?)"')
    def extractMeetingUrls(self, meetings):
        '''p_meetings is a HTML table containing URLs to meetings. This method
           extracts meeting URLs from it.'''
        res = []
        for tr in self.trRex.findall(meetings):
            if tr.find('</th>') != -1: continue # This is the header row
            match = self.hrefRex.search(tr)
            res.append(urlparse.urlparse(match.group(1))[2])
        return res

    def listMeetings(self, decision=True):
        '''Sends the (normally called via Ajax) HTTP request for getting the
           list of available meetings. If p_decision is True, it returns the
           meetings for which decisions have already been published.'''
        self.resp = self.server.get(
            uri='/ArchiveEgcf/portal_plonemeeting/egcf/ajax?page=' \
                'plonemeeting_topic_result&macro=topicResult&topicId=' \
                'searchalldecisions&b_start=0&hookId=queryResult')
        print self.resp, 'Got list of meetings'
        return self.extractMeetingUrls(self.resp.body)

    def navigateInMeeting(self, meetingUri):
        '''Navigates in the meeting, and returns the list of items (having at
           least one annex) that appear on the first page.'''
        # We will store here one dict per item. In this dict, we will store the
        # item URI at key 'uri', and a list of annex URIs at key 'annexes'.
        items = []
        self.resp = self.server.get(uri=meetingUri)
        print self.resp, 'Got meeting page at', meetingUri
        # Navigate to some items in this meeting. Get the list of items by
        # calling the HTTP request normally Ajax-called.
        itemsListsUri = '%s/ajax?page=meetingitems_list&macro=items&' \
                        'whichItems=meetingItems&showColors=False&' \
                        'startNumber=1&showDescriptions=true' % meetingUri
        self.resp = self.server.get(uri=itemsListsUri)
        print self.resp, 'Got (normal) items list'
        for href in self.hrefRex.findall(self.resp.body):
            # Among all hrefs, there are:
            # (a) URLs for viewing items; (= a full URL)
            # (b) URLs for editing items; (= a full URL)
            # (c) URLs for downloading an annex linked to an item
            #     (= the URI part only)
            if href.endswith('/edit'): continue # We don't care about (b)
            # Determine if the href refers to an item or an annex and
            # standardize the way the URI must be expressed.
            isItem = True
            baseName = os.path.basename(href)
            if '.' in baseName: isItem = False
            if href.startswith('http'): href = urlparse.urlparse(href)[2]
            if isItem:
                items.append({'uri':href, 'annexes':[]})
            else:
                # Add the annex to the last item in self.items
                items[-1]['annexes'].append(href)
        # Keep only items that have at least one annex
        return [i for i in items if i['annexes']]

    def navigateInItem(self, itemUri):
        '''Navigates in an item.'''
        self.resp = self.server.get(uri=itemUri)
        print self.resp, 'Got item page at', itemUri

    def downloadAnnex(self, annexUri):
        '''Downloads an annex.'''
        self.resp = self.server.get(uri=annexUri)
        print self.resp, 'Downloaded annex at', annexUri
        if self.saveAnnexes:
            # Save downloaded annexes to the disk, in the current folder.
            annexName = os.path.basename(annexUri)
            f = file('download/%s' % annexName, 'wb')
            f.write(self.resp.body)
            f.close()

    def chooseElements(self, elems, count=2):
        '''This method chooses randomly, among p_elems, p_count elements and
           returns a tuple with those elements. If the number of elements in
           p_elems is less or equal to p_count, the returned value is equal
           to p_elems.'''
        if len(elems) > count:
            # Choose p_count elems randomly among all elems in p_elems.
            res = []
            indexes = [] # The already chosen indexes
            while len(res) < count:
                i = random.randint(0,len(elems)-1)
                if i not in indexes:
                    res.append(elems[i])
                    indexes.append(i)
        else:
            res = elems
        return res

    def runScenario(self):
        '''Executes our test scenario.'''
        # Choose a subset of meetings among all available meetings
        meetings = self.listMeetings()
        if len(meetings) > self.meetingsPerTest:
            meetings = self.chooseElements(meetings, count=self.meetingsPerTest)
        elif len(meetings) < self.meetingsPerTest:
            print 'Warning! Less than %d decided meetings are available...' % \
                  self.meetingsPerTest
        # Navigate among the chosen meetings
        for meetingUri in meetings:
            items = self.navigateInMeeting(meetingUri)
            # Choose a subset of items among all available items
            if len(items) > self.itemsPerMeeting:
                items = self.chooseElements(items, count=self.itemsPerMeeting)
            else:
                print 'Warning! Less than %d items with annexes are ' \
                      'available in this meeting...' % self.itemsPerMeeting
            for item in items:
                self.navigateInItem(item['uri'])
                # Download a subset of annexes per item
                annexes = self.chooseElements(item['annexes'],
                                              self.annexesPerItem)
                for annexUri in annexes:
                    self.downloadAnnex(annexUri)

    def run(self):
        startTime = time.time()
        self.authenticate()
        self.gotoHomePage()
        for i in range(self.numberOfTests):
            self.runScenario()
        # Print a report
        nbOfMeetings = self.numberOfTests * self.meetingsPerTest
        nbOfItems = self.itemsPerMeeting * nbOfMeetings
        nbOfAnnexes = nbOfItems * self.annexesPerItem
        endTime = time.time()
        print '----------------------------------------------------------------'
        print 'Test scenario executed %d times.' % self.numberOfTests
        print 'Total downloads: %d meeting(s), %s items and %s annexes' % \
              (nbOfMeetings, nbOfItems, nbOfAnnexes)
        print 'Total server time is %.4f seconds' % self.server.serverTime
        print 'Total script time (including server time) is %.4f seconds' % \
              (endTime - startTime)
        if self.saveAnnexes:
            print 'Annexes were saved to the "download" subfolder.'
        print '----------------------------------------------------------------'

# ------------------------------------------------------------------------------
if __name__ == '__main__':
    if len(sys.argv) != 4:
        print 'Please specify 3 args: (1) the URL of the Plone site to test '\
              'on your server, (2) the user name to use, (3) its password.'
        sys.exit(-1)
    PerformanceTester(sys.argv[1],login=sys.argv[2],password=sys.argv[3]).run()
# ------------------------------------------------------------------------------
