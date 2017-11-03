import os
import subprocess
import yaml

from test import Test, Status
from reporter import Dispatcher, Event

dispatcher = Dispatcher()

def readlist(dict, key):
    if not key in dict:
        return []
    ret = dict[key]
    if type(ret) != list:
        ret = [ret]
    return ret

class ExceptionInvalidTheoFile(Exception):
    pass

class Suite(object):
    '''A suite represents a set of tests.'''
    default_configuration = dict(
        valgrind = False,
        environment = [],
        volatile = [],
        setup = [],
    )
    def __init__(self, path, arguments):

        with open(path, 'r') as testfile:
            content = testfile.readlines()

        self.arguments = arguments
        self.configuration = Suite.default_configuration.copy()
        self.tests = list()
        self.path = path

        content = self.search_theo(content)

        self.fromYAML(content)

        self.statusSetup = Status.NOTRUN
        self.statusSetdown = Status.NOTRUN

    def fromYAML(self, content):
        try:
            suite = yaml.load(content)
        except:
            raise ExceptionInvalidTheoFile()
        if 'configuration' in suite:
            self.parseConfiguration(suite['configuration'])
        if 'tests' in suite:
            self.parseTests(suite['tests'])

    def search_theo(self, data):
        '''Try to find a !theo block. If not found, get all the file.'''
        start = None
        end = None

        for lineno, line in enumerate(data):
            if '!theo' in line:
                if start == None:
                    start = lineno
                else:
                    end = lineno

        if start != None and end != None:
            i = data[start].index('!theo')
            prev = data[start][0:i]
            prevlen = len(prev)
            prev = prev.rstrip()

            contents = ''

            for line in data[start+1:end]:
                if not line.startswith(prev):
                    return
                cropped = line[prevlen:] or '\n'
                contents += cropped

            return contents
        else:
            return ''.join(data)

    def parseConfiguration(self, config):
        config['environment'] = readlist(config, 'environment')
        config['volatile'] = readlist(config, 'volatile')
        self.configuration.update(config)

    def parseTests(self, configlist):
        for config in configlist:
            self.tests.append(Test(config, self))

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

