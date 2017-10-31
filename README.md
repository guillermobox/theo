Theo the Tester
===============

This is a harness to retrieve and launch tests that I use, personally, for
some of my projects. The idea is to be language agnostic, and lightweight.
Nothing fancy, just easier to write than to learn another testing suite :)

In examples, there are some files that can be used as input for theo. The
idea is to define a test with a command to run, and the expected output
or exit value. Valgrind can be used also to check that the command does not
have memory leaks or similar.

By running:

    theo simple.yaml

Theo will load the yaml file, parse the tests, and run them. Reporting when
any of the tests failed.

