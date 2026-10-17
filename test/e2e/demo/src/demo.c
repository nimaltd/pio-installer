#include "demo.h"
#include "demo_port.h"
#include "helper.h"

int demo_answer(void)
{
    return helper_forty() + (DEMO_PLUS * DEMO_PORT_TIMES);
}
