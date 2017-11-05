#!/usr/bin/python2
import argparse

from parser import ExceptionInvalidTheoFile
from reporter import NiceReporter, EventsReporter
from suite import Suite

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("theofile",
            help="File(s) to search looking for tests",
            nargs="+")
    parser.add_argument("-o", "--output",
            help=argparse.SUPPRESS,
            default="nice")

    arguments = parser.parse_args()

    if arguments.output == 'nice':
        reporter = NiceReporter()
    else:
        reporter = EventsReporter()

    reporter.start()

    for file in arguments.theofile:
        try:
            suite = Suite(file)
            suite.runTests()
        except ExceptionInvalidTheoFile:
            pass

    reporter.stop()
    reporter.join()

if __name__ == '__main__':
    exit(main())
