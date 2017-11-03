#!/usr/bin/python2
import argparse

from suite import Suite, ExceptionInvalidTheoFile
from reporter import Reporter, NiceReporter, EventsReporter, Event, Dispatcher


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("theofile",
            help="File(s) to search looking for tests",
            nargs="+")
    parser.add_argument("-o", "--output",
            help=argparse.SUPPRESS,
            default="nice")

    arguments = parser.parse_args()

    reporter = NiceReporter()
    dispatcher = Dispatcher()
    reporter.start()

    for file in arguments.theofile:
        try:
            suite = Suite(file, arguments)
            suite.runTests()
        except ExceptionInvalidTheoFile:
            pass

    dispatcher.put((Event.Exit, None))
    reporter.join()

if __name__ == '__main__':
    exit(main())
