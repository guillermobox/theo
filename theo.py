#!/usr/bin/python2
import yaml
import subprocess
import threading
import tempfile
import shutil
import os
import sys

def readlist(dict, key):
    if not key in dict:
        return []
    ret = dict[key]
    if type(ret) != list:
        ret = [ret]
    return ret

class TestStatus:
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
    def __init__(self, path):

        with open(path, 'r') as testfile:
            try:
                suite = yaml.load(testfile)
            except yaml.scanner.ScannerError as e:
                raise Exception("Input file is not YAML, error at line %d"%(e.problem_mark.line,))

        self.name,_ = os.path.splitext(os.path.basename(path))

        self.configuration = dict()
        self.tests = list()

        if 'configuration' in suite:
            self.parseConfiguration(suite['configuration'])
        if 'tests' in suite:
            self.parseTests(suite['tests'])

    def parseConfiguration(self, config):
        config['environment'] = readlist(config, 'environment')
        config['volatile'] = readlist(config, 'volatile')
        self.configuration.update(config)

    def parseTests(self, configlist):
        for config in configlist:
            self.tests.append(Test(config, self))

    def runTests(self):

        print '\033[7m{0:39} {1:4} {2:4} {3:30}\033[0m'.format('Test name','Test','Valg','Message')

        for test in self.tests:
            self.setup()
            err = test.run()
            self.show_test_results(test)
            self.setdown()

        failed = [test for test in self.tests if test.abortmsg != None]

        if len(failed) == 0:
            msg = 'All tests completed successfully'
        else:
            msg = 'Failed {0} tests of {1}'.format(len(failed), len(self.tests))

        print '\033[7m{0:^80}\033[0m'.format(msg)

        for test in failed:
            print "{0}: {1}".format(test.name, test.showDiagnostics())

    def show_test_results(self, test):
        print '{0:39}'.format(test.name),

        if test.statusTest == TestStatus.PASS:
            print "\033[32mPASS\033[0m",
        elif test.statusTest == TestStatus.ERROR:
            print "\033[31mFAIL\033[0m",
        elif test.statusTest == TestStatus.NOTRUN:
            print "----",

        if test.statusValgrind == TestStatus.PASS:
            print "\033[32mPASS\033[0m",
        elif test.statusValgrind == TestStatus.ERROR:
            print "\033[31mFAIL\033[0m",
        elif test.statusValgrind == TestStatus.NOTRUN:
            print "----",

        if test.abortmsg:
            print test.abortmsg,

        print

    def setup(self):
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

    def setdown(self):
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
    default_configuration = dict(
        input= None,
        output= None,
        timeout= 10,
        exit = None,
        valgrind = False
    )
    def __init__(self, config, suite):

        self.config = Test.default_configuration.copy()
        self.config.update(config)

        self.suite = suite

        self.name = config['name']
        self.config['setup'] = readlist(config,'setup')

        self.statusSetup = TestStatus.NOTRUN
        self.statusTest = TestStatus.NOTRUN
        self.statusValgrind = TestStatus.NOTRUN

        self.abortmsg = None

    def abort(self, msg, reason):
        self.abortmsg = msg
        self.reason = reason
        return msg

    def setup(self):
        self.statusSetup = TestStatus.RUNNING
        for command in self.config['setup']:
            if subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                self.statusSetup = TestStatus.ERROR
                return self.abort("Setup failed", FailureReason.SETUP)
        self.statusSetup = TestStatus.PASS

    def run(self):
        if self.setup():
            return FailureReason.SETUP

        self.statusTest = TestStatus.RUNNING
        self.process = subprocess.Popen("exec " + self.config['run'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

        def target():
            (stdout, stderr) = self.process.communicate(self.config['input'])
            self.runResults = (stdout, stderr)

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(self.config['timeout'])
        if thread.is_alive():
            process.kill()
            thread.join()
            self.statusTest = TestStatus.ERROR
            return self.abort("Timeout of %d seconds"%(self.config['timeout'],), FailureReason.TIME)

        if self.config['output'] != None and str(self.config['output']).strip() != self.runResults[0].strip():
            self.statusTest = TestStatus.ERROR
            return self.abort("Wrong output", FailureReason.OUTPUT)

        if self.config['exit'] != None and self.config['exit'] != self.process.returncode:
            self.statusTest = TestStatus.ERROR
            return self.abort("Wrong return value", FailureReason.RETURN)

        self.statusTest = TestStatus.PASS

        if self.suite.configuration['valgrind'] != True:
            return None

        self.setup()

        xmlfile = tempfile.NamedTemporaryFile()

        self.statusValgrind = TestStatus.RUNNING
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
            self.statusValgrind = TestStatus.ERROR
            return self.abort("Timeout of %d seconds"%(self.config['timeout'],), FailureReason.TIME)

        from lxml import etree
        tree = etree.parse(xmlfile)
        errors = tree.xpath('/valgrindoutput/error')
        if errors:
            self.statusValgrind = TestStatus.ERROR
            self.valgrind = len(errors)
            shutil.copyfile(xmlfile.name, self.name + '.valgrind')
        else:
            self.statusValgrind = TestStatus.PASS
        xmlfile.close()

    def showDiagnostics(self):
        if self.reason == FailureReason.OUTPUT:
            return "Expected output '{0}' but found '{1}'".format(str(self.config['output']).strip(), self.runResults[0].strip())
        elif self.reason == FailureReason.RETURN:
            return "Expected return value '{0}' but found '{1}'".format(self.config['exit'], self.process.returncode)
        elif self.reason == FailureReason.SETUP:
            return "Setup failed"

def main():
    suite = Suite(sys.argv[1])
    suite.runTests()

if __name__ == '__main__':
    exit(main())
