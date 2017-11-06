/*
 * !theo
 * configuration:
 *   setup: make standalone
 *   valgrind: true
 *
 * tests:
 *   - name: ANumberandItself
 *     run: ./standalone 7 7
 *     output: 7
 *
 *   - name: TwoBigNumbers
 *     run: ./standalone 1394 2414
 *     output: 34
 *
 *   - name: TwoHugeIntegers
 *     run: ./standalone 290272158 608635170
 *     output: 9363618
 *
 *   - name: TwoPrimes
 *     run: ./standalone 23 91
 *     output: 1
 *
 *   - name: Zero
 *     run: ./standalone 0 0
 *     output: 0
 *
 *   - name: SecondZero
 *     run: ./standalone 125 0
 *     output: 125
 *
 *   - name: FirstZero
 *     run: ./standalone 0 125
 *     output: 125
 *
 *   - name: FirstOne
 *     run: ./standalone 1 99
 *     output: 1
 *
 *   - name: SecondOne
 *     run: ./standalone 99 1
 *     output: 1
 * !theo
 */

#include <stdio.h>
#include <stdlib.h>

/*
 * I'll test this small function that calculates the mcd of two numbers
 * using theo. The test specification in in the comment above.
 */
int mcd(int a, int b) {
	if (b == 0) return a;
	else return mcd(b, a%b);
};

int main(int argc, char *argv[])
{
	int a, b;

	a = atoi(argv[1]);
	b = atoi(argv[2]);
	printf("%d\n", mcd(a,b));

	return EXIT_SUCCESS;
};
