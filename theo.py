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

class FailureReason:
    PASS = 0
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
        self.parseConfiguration(suite['configuration'])
        self.parseTests(suite['tests'])
        self.failedTests = []
        self.completedTests = []

    def parseConfiguration(self, config):
        self.environment = readlist(config, 'environment')
        self.volatile = readlist(config, 'volatile')

    def parseTests(self, configlist):
        self.tests = []
        for config in configlist:
            self.newTest(config)

    def newTest(self, configuration):
        self.tests.append(Test(configuration))

    def runTests(self):

        print '\033[7m{0:^39} {1:4} {2:4} {3:^30}\033[0m'.format('Test name','Test','Valg','Message')

        for test in self.tests:
            self.setup()
            err = test.run()
            test.run_valgrind()
            if err:
                self.failedTests.append(test)
            else:
                self.completedTests.append(test)
            self.show_test_results(test)
            self.setdown()

        if len(self.failedTests) == 0:
            msg = 'All tests completed successfully'
        else:
            msg = 'Failed {0} tests of {1}'.format(len(self.failedTests), len(self.tests))

        print '\033[7m{0:^80}\033[0m'.format(msg)

        for test in self.failedTests:
            print self.name + '.' + test.name, test.showDiagnostics()

    def show_test_results(self, test):
        print '{0:39}'.format(test.name),

        if test.abortmsg:
            print "\033[7;31mFAIL\033[0m ---- {0}".format(test.abortmsg),
        else:
            print "\033[32m OK \033[0m",
            if test.valgrind:
                print "\033[31mFAIL\033[0m {0} valgrind errors".format(test.valgrind),
            else:
                print "\033[32m OK \033[0m",
        print


    def setup(self):
        self.savedEnvironment = dict()
        for pair in self.environment:
            key,_,value = pair.partition('=')
            if key in os.environ:
                self.savedEnvironment[key] = os.environ[key]
            os.environ[key] = value

        for path in self.volatile:
            try:
                os.remove(path)
            except:
                pass

    def setdown(self):
        for pair in self.environment:
            key,_,value = pair.partition('=')
            if key in self.savedEnvironment:
                os.environ[key] = self.savedEnvironment[key]
            else:
                del os.environ[key]

        for path in self.volatile:
            try:
                os.remove(path)
            except:
                pass

class Test(object):
    def __init__(self, config):
        self.name = config['name']
        self.command = config['run']
        self.setup = config['setup'] if 'setup' in config else []
        if type(self.setup) != list:
            self.setup = [self.setup]
        self.input = str(config['input']) if 'input' in config else None

        if 'output' in config:
            self.stdout = config['output'] or ""
        else:
            self.stdout = None

        self.retval = config['return'] if 'return' in config else None
        self.timeout = int(config['timeout']) if 'timeout' in config else 10

        self.abortmsg = None
        self.valgrind = None

    def abort(self, msg, reason):
        self.abortmsg = msg
        self.reason = reason
        return msg

    def run(self):
        for command in self.setup:
            if subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                return self.abort("Setup failed", FailureReason.SETUP)

        self.process = subprocess.Popen("exec " + self.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

        def target():
            (stdout, stderr) = self.process.communicate(self.input)
            self.runResults = (stdout, stderr)

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(self.timeout)
        if thread.is_alive():
            process.kill()
            thread.join()
            return self.abort("Timeout of %d seconds"%(self.timeout,), FailureReason.TIME)

        if self.stdout != None and str(self.stdout).strip() != self.runResults[0].strip():
            return self.abort("Wrong output", FailureReason.OUTPUT)

        if self.retval != None and self.retval != self.process.returncode:
            return self.abort("Wrong return value", FailureReason.RETURN)

        return None

    def run_valgrind(self):
        for command in self.setup:
            if subprocess.call(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
                return self.abort("Setup failed", FailureReason.SETUP)

        xmlfile = tempfile.NamedTemporaryFile()

        valgrindstr="valgrind --error-exitcode=127 --xml-file="+xmlfile.name+" --xml=yes --leak-check=full";
        self.process = subprocess.Popen("exec " + valgrindstr + " " + self.command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

        def target():
            (stdout, stderr) = self.process.communicate(self.input)
            self.runResults = (stdout, stderr)

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(self.timeout)
        if thread.is_alive():
            process.kill()
            thread.join()
            return self.abort("Timeout of %d seconds"%(self.timeout,), FailureReason.TIME)

        from lxml import etree
        tree = etree.parse(xmlfile)
        errors = tree.xpath('/valgrindoutput/error')
        if errors:
            self.valgrind = len(errors)
            shutil.copyfile(xmlfile.name, self.name + '.valgrind')
        xmlfile.close()

    def showDiagnostics(self):
        if self.reason == FailureReason.OUTPUT:
            return "Expected output '{0}' but found '{1}'".format(str(self.stdout).strip(), self.runResults[0].strip())
        elif self.reason == FailureReason.RETURN:
            return "Expected return value '{0}' but found '{1}'".format(self.retval, self.process.returncode)

def main():
    suite = Suite(sys.argv[1])
    suite.runTests()

if __name__ == '__main__':
    exit(main())
