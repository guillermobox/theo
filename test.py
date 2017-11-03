import subprocess
import tempfile
import threading

from reporter import Dispatcher, Event
from lxml import etree

dispatcher = Dispatcher()

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
        dispatcher.put((Event.TestFinished, self))
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
        dispatcher.put((Event.TestStart, self))

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
            dispatcher.put((Event.TestFinished, self))
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

        tree = etree.parse(xmlfile)
        errors = tree.xpath('/valgrindoutput/error')
        if errors:
            self.statusValgrind = Status.ERROR
            self.valgrind = len(errors)
            shutil.copyfile(xmlfile.name, self.config['name'] + '.valgrind')
        else:
            self.statusValgrind = Status.PASS
        xmlfile.close()
        dispatcher.put((Event.TestFinished, self))

    def failureMessage(self):
        '''This is the short failure message for the user.'''
        if self.reason == FailureReason.OUTPUT:
            return "Expected output '{0}' but found '{1}'".format(str(self.config['output']).strip(), self.runResults[0].strip())
        elif self.reason == FailureReason.RETURN:
            return "Expected return value '{0}' but found '{1}'".format(self.config['exit'], self.process.returncode)
        elif self.reason == FailureReason.SETUP:
            return "Setup failed"


