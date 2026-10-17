/*
 * Prints demo's answer: 52 once CI has set DEMO_PLUS to 12 in demo's
 * configuration header and installed again, which shows the update kept it.
 */

#include <stdio.h>
#include "demo.h"

int main(void)
{
    printf("demo says %d\n", demo_answer());

    return 0;
}
