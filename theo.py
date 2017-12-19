#!/usr/bin/python2
import argparse
import atexit
import os
import signal

from parser import ExceptionInvalidTheoFile
from reporter import NiceReporter, EventsReporter
from suite import Suite

def expand(path):
    if os.path.isdir(path):
        paths = [p for p in os.listdir(path) if not p.startswith('.')]
        contents = [os.path.join(path, filename) for filename in paths]
        return filter(os.path.isfile, contents)
    else:
        if not path.startswith('.'):
            return [path]
        else:
            return []

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
        files = set()
        for file in arguments.theofile:
            files.update(expand(file))

        for file in files:
            try:
                suite = Suite(file)
                suite.runTests()
            except ExceptionInvalidTheoFile:
                pass
    finally:
        cleanup(reporter)

if __name__ == '__main__':
    exit(main())
