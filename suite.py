import os
import subprocess

from test import Test, Status
from reporter import Dispatcher, Event
from parser import ParserYaml

dispatcher = Dispatcher()

def readlist(dict, key):
    if not key in dict:
        return []
    ret = dict[key]
    if type(ret) != list:
        ret = [ret]
    return ret

class Suite(object):
    '''A suite represents a set of tests.'''

    default_configuration = dict(
        valgrind = False,
        environment = [],
        volatile = [],
        setup = [],
    )

    def __init__(self, path):
        self.path = path

        parser = ParserYaml(path)
        dictionary = parser.process()

        self.configuration = Suite.default_configuration.copy()
        self.configuration.update( dictionary['configuration'] )

        self.tests = []
        for test in dictionary['tests']:
            self.tests.append(Test(test, self))

        self.statusSetup = Status.NOTRUN
        self.statusSetdown = Status.NOTRUN

    def runTests(self):
        '''This method runs the tests in the suite.'''

        self.setup_suite()

        if self.statusSetup != Status.ERROR:
            for test in self.tests:
                self.setup()
                err = test.run()
                self.setdown()

        dispatcher.put((Event.SuiteFinished, self))

    def setup(self):
        '''Prepare the nevironment to a given test.'''
        self.savedEnvironment = dict()
        for pair in self.configuration['environment']:
            key,_,value = pair.partition('=')
            if key in os.environ:
                self.savedEnvironment[key] = os.environ[key]
            os.environ[key] = value

        for path in self.configuration['volatile']:
            try:
                os.remove(path)
            except:
                pass

    def setup_suite(self):
        '''Run the setup commands from the suite.'''
        dispatcher.put((Event.SuiteStart, self))
        if self.configuration['setup']:
            self.statusSetup = Status.RUNNING
            for command in readlist(self.configuration, 'setup'):
                if subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                    self.statusSetup = Status.ERROR
                    dispatcher.put((Event.SuiteSetupFinished, self))
                    return
            self.statusSetup = Status.PASS
        dispatcher.put((Event.SuiteSetupFinished, self))

    def setdown(self):
        '''Clean the environment from a given test.'''
        for pair in self.configuration['environment']:
            key,_,value = pair.partition('=')
            if key in self.savedEnvironment:
                os.environ[key] = self.savedEnvironment[key]
            else:
                del os.environ[key]

        for path in self.configuration['volatile']:
            try:
                os.remove(path)
            except:
                pass

