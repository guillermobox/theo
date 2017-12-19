#!/usr/bin/python2
import argparse
import atexit
import signal

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

    def cleanup(rep):
        rep.stop()
        rep.join()

    def cleanme(*args, **kwargs):
        cleanup(reporter)
        exit(1)

    signal.signal(signal.SIGTERM, cleanme)
    signal.signal(signal.SIGINT, cleanme)

    try:
        for file in arguments.theofile:
            try:
                suite = Suite(file)
                suite.runTests()
            except ExceptionInvalidTheoFile:
                pass
    finally:
        cleanup(reporter)

if __name__ == '__main__':
    exit(main())
