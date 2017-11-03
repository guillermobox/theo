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

Also, theo is capable of finding this data in any other type of file. You only
have to write !theo in any line, and !theo again in another line after the
first one. Theo will take whatever is inside them, remove the prefix found
in the !theo line from the lines inbetween, and then create a suite for that
file. See `standalone.c` in the examples folder to understand it better. You
run it like with a yaml file:

    theo standalone.c

