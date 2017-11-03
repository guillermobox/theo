#!/usr/bin/python2
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import yaml

arguments = None

def readlist(dict, key):
    if not key in dict:
        return []
    ret = dict[key]
    if type(ret) != list:
        ret = [ret]
    return ret

class Status:
    NOTRUN = 0
    RUNNING = 1
    PASS = 2
    ERROR = 3

class FailureReason:
    NONE = 0
    SETUP = 1
    TIME  = 2
    OUTPUT = 3
    RETURN = 4

class Suite(object):
    default_configuration = dict(
        valgrind = False,
        environment = [],
        volatile = [],
        setup = [],
    )
    '''A suite represents a set of tests.'''
    def __init__(self, path):

        with open(path, 'r') as testfile:
            content = testfile.readlines()

        self.configuration = Suite.default_configuration.copy()
        self.tests = list()
        self.path = path

        try:
            self.fromYAML(content)
        except:
            try:
                content = self.search_theo(content)
                self.fromYAML(content)
            except Exception as e:
                raise e
                raise Exception('This is not a theo file, or does not contain theo data')

        self.statusSetup = Status.NOTRUN
        self.statusSetdown = Status.NOTRUN

    def fromYAML(self, content):
        try:
            suite = yaml.load(''.join(content))
        except yaml.scanner.ScannerError as e:
            raise Exception("Input file is not YAML, error at line %d"%(e.problem_mark.line,))
        if 'configuration' in suite:
            self.parseConfiguration(suite['configuration'])
        if 'tests' in suite:
            self.parseTests(suite['tests'])

    def search_theo(self, data):

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
                    print 'Error!'
                    return
                cropped = line[prevlen:] or '\n'
                contents += cropped

            return contents

        raise Exception('Theo not found in this file')

    def parseConfiguration(self, config):
        config['environment'] = readlist(config, 'environment')
        config['volatile'] = readlist(config, 'volatile')
        self.configuration.update(config)

    def parseTests(self, configlist):
        for config in configlist:
            self.tests.append(Test(config, self))

    def printHeader(self):
        if arguments.output == 'nice':
            print u'\u250C', 'Starting', self.path,

    def printAfterHeader(self):
        if arguments.output == 'nice':
            if self.statusSetup == Status.ERROR:
                print "\033[31mFAIL\033[0m",
            else:
                print "\033[32mPASS\033[0m",
            print

    def printTest(self, test):
        if arguments.output == 'nice':
            print u'\u251C\u2500\u2500','{0:39}'.format(test.config['name']),

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

    def printFooter(self):
        if arguments.output == 'nice':
            failed = [t for t in self.tests if t.hasFailed()]

            print u'\u2514', 'Ending', self.path,

            if self.statusSetup == Status.ERROR:
                print
                print
                print 'The suite setup failed!'
                print
                return

            if self.statusSetdown == Status.ERROR:
                print "\033[31mFAIL\033[0m",
            else:
                print "\033[32mPASS\033[0m",
            print

            if len(failed) == 0:
                msg = 'All clear!'
            else:
                msg = 'Failed {0} tests of {1}'.format(len(failed), len(self.tests))
            print
            print msg
            print

            for test in failed:
                print "{0}.{1}: {2}".format(self.path, test.config['name'], test.failureMessage())

    def runTests(self):
        '''This method runs the tests in the suite.'''
        self.printHeader()
        self.setup_suite()
        self.printAfterHeader()

        if self.statusSetup != Status.ERROR:
            for test in self.tests:
                self.setup()
                err = test.run()
                self.setdown()
                self.printTest(test)

        self.printFooter()

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
        if self.configuration['setup']:
            self.statusSetup = Status.RUNNING
            for command in readlist(self.configuration, 'setup'):
                if subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                    self.statusSetup = Status.ERROR
                    return
            self.statusSetup = Status.PASS


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

class Test(object):
    '''A test represents any command that the user wants to run and check its
    output. It could have a setup command. Valgrind can be executed and the
    result is checked.'''

    default_configuration = dict(
        input= None,
        output= None,
        timeout= 600,
        exit = None,
        valgrind = False
    )

    def __init__(self, config, suite):
        '''Initialize the test. Nothing is run here.'''
        self.config = Test.default_configuration.copy()
        self.config.update(config)

        self.suite = suite
        self.statusSetup = Status.NOTRUN
        self.statusTest = Status.NOTRUN
        self.statusValgrind = Status.NOTRUN

        self.abortmsg = None
        self.reason = None

    def hasFailed(self):
        '''Return true if the Test has failed.'''
        return self.abortmsg != None

    def abort(self, msg, reason):
        '''Abort the test with a message and reason.'''
        self.abortmsg = msg
        self.reason = reason
        return msg

    def setup(self):
        '''Run the setup of the test.'''
        self.statusSetup = Status.RUNNING
        for command in readlist(self.config, 'setup'):
            if subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                self.statusSetup = Status.ERROR
                return self.abort("Setup failed", FailureReason.SETUP)
        self.statusSetup = Status.PASS

    def run(self):
        '''Run the full test procedure, includes setup and test.'''
        if self.setup():
            return FailureReason.SETUP

        self.statusTest = Status.RUNNING
        self.process = subprocess.Popen("exec " + self.config['run'],
                shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=subprocess.PIPE)

        def target():
            (stdout, stderr) = self.process.communicate(self.config['input'])
            self.runResults = (stdout, stderr)

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(self.config['timeout'])
        if thread.is_alive():
            process.kill()
            thread.join()
            self.statusTest = Status.ERROR
            return self.abort("Timeout of %d seconds"%(self.config['timeout'],), FailureReason.TIME)

        if self.config['output'] != None and str(self.config['output']).strip() != self.runResults[0].strip():
            self.statusTest = Status.ERROR
            return self.abort("Wrong output", FailureReason.OUTPUT)

        if self.config['exit'] != None and self.config['exit'] != self.process.returncode:
            self.statusTest = Status.ERROR
            return self.abort("Wrong return value", FailureReason.RETURN)

        self.statusTest = Status.PASS

        if self.suite.configuration['valgrind'] != True:
            return None

        self.setup()

        xmlfile = tempfile.NamedTemporaryFile()

        self.statusValgrind = Status.RUNNING
        valgrindstr="valgrind --error-exitcode=127 --xml-file="+xmlfile.name+" --xml=yes --leak-check=full";
        self.process = subprocess.Popen("exec " + valgrindstr + " " + self.config['run'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

        def target():
            (stdout, stderr) = self.process.communicate(self.config['input'])
            self.runResults = (stdout, stderr)

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(self.config['timeout'])
        if thread.is_alive():
            process.kill()
            thread.join()
            self.statusValgrind = Status.ERROR
            return self.abort("Timeout of %d seconds"%(self.config['timeout'],), FailureReason.TIME)

        from lxml import etree
        tree = etree.parse(xmlfile)
        errors = tree.xpath('/valgrindoutput/error')
        if errors:
            self.statusValgrind = Status.ERROR
            self.valgrind = len(errors)
            shutil.copyfile(xmlfile.name, self.config['name'] + '.valgrind')
        else:
            self.statusValgrind = Status.PASS
        xmlfile.close()

    def failureMessage(self):
        '''This is the short failure message for the user.'''
        if self.reason == FailureReason.OUTPUT:
            return "Expected output '{0}' but found '{1}'".format(str(self.config['output']).strip(), self.runResults[0].strip())
        elif self.reason == FailureReason.RETURN:
            return "Expected return value '{0}' but found '{1}'".format(self.config['exit'], self.process.returncode)
        elif self.reason == FailureReason.SETUP:
            return "Setup failed"

def main():
    global arguments

    parser = argparse.ArgumentParser()
    parser.add_argument("theofile",
            help="File(s) to search looking for tests",
            nargs="+")
    parser.add_argument("-o", "--output",
            help=argparse.SUPPRESS,
            default="nice")

    arguments = parser.parse_args()

    for file in arguments.theofile:
        try:
            suite = Suite(file)
            suite.runTests()
        except:
            pass

if __name__ == '__main__':
    exit(main())
