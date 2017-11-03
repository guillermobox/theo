#!/usr/bin/python2
import argparse

from suite import Suite, ExceptionInvalidTheoFile

def main():
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
            suite = Suite(file, arguments)
            suite.runTests()
        except ExceptionInvalidTheoFile:
            print file, 'is an invalid theo file, skipping'

if __name__ == '__main__':
    exit(main())
