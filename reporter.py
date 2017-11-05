from threading import Thread
from Queue import Queue
import time

class RootDispatcher():
    def __init__(self):
        global enabled
        if enabled == False:
            self._queue = Queue()
            enabled = True
    def put(self, event):
        self._queue.put(event)

enabled = False
rootdispatcher = RootDispatcher()

def Dispatcher():
    return rootdispatcher

queues = dict(event=None)

def enum(**named_values):
    return type('Enum', (), named_values)

Event = enum(
        SuiteStart='SuiteStart',
        SuiteSetupFinished='SuiteSetupFinished',
        TestSetupStart='TestSetupStart',
        TestSetupEnd='TestSetupEnd',
        TestStart='TestStart',
        TestFinished='TestFinished',
        SuiteFinished='SuiteFinished',
        TestRunStart='TestRunStart',
        TestRunFinish='TestRunFinish',
        Exit='Exit'
)


class Reporter(Thread):
    def __init__(self):
        super(Reporter, self).__init__()

    def run(self):
        while True:
            event = rootdispatcher._queue.get()
            name, payload = event
            if name == Event.Exit:
                return
            self.process_event(name, payload)

    def process_event(self, name, payload):
        handler = None
        try:
            handler = self.__getattribute__('event_' + name)
        except:
            return
        handler(payload)

class EventsReporter(Reporter):
    def process_event(self, name, payload):
        print name, payload

class NiceReporter(Reporter):
    def event_SuiteStart(self, payload):
        print u'\u250C', 'Starting', payload.path,

    def event_SuiteSetupFinished(self, payload):
        from test import Status
        if payload.statusSetup == Status.ERROR:
            print "\033[31mFAIL\033[0m",
        print

    def event_TestFinished(self, test):
        from test import Status
        print u'\u251C\u2500\u2500','{0:30}'.format(test.config['name']),

        if test.statusTest == Status.PASS:
            print "\033[32mPASS\033[0m",
        elif test.statusTest == Status.ERROR:
            print "\033[31mFAIL\033[0m",
        elif test.statusTest == Status.NOTRUN:
            print "----",

        if test.statusValgrind == Status.PASS:
            print "\033[32mPASS\033[0m",
        elif test.statusValgrind == Status.ERROR:
            print "\033[31mFAIL\033[0m",
        elif test.statusValgrind == Status.NOTRUN:
            print "----",

        if test.hasFailed():
            print test.abortmsg,
        print

    def event_SuiteFinished(self, suite):
        from test import Status
        failed = [t for t in suite.tests if t.hasFailed()]

        print u'\u2514', 'Ending', suite.path,

        if suite.statusSetup == Status.ERROR:
            print
            print
            print 'The suite setup failed!'
            print
            return

        if suite.statusSetdown == Status.ERROR:
            print "\033[31mFAIL\033[0m",
        print

        if len(failed) == 0:
            msg = 'All clear!'
        else:
            msg = 'Failed {0} tests of {1}'.format(len(failed), len(suite.tests))
        print
        print msg
        print

        for test in failed:
            print "{0}.{1}: {2}".format(suite.path, test.config['name'], test.failureMessage())

