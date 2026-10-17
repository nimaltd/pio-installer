/**
 * @file        demo.h
 * @brief       A library for pio-installer's end to end test.
 * @version     1.0.0
 */

#ifndef DEMO_H
#define DEMO_H

#include "demo_config.h"

/* From install.defines, through build_flags in platformio.ini: the project's
   own code, which includes this header, has to see it. */
#if !defined(DEMO_ON) || (DEMO_ON != 1)
#error "DEMO_ON from demo's installer.yml did not reach the code including demo.h"
#endif

#ifdef __cplusplus
extern "C"
{
#endif

int demo_answer(void);

#ifdef __cplusplus
}
#endif

#endif /* DEMO_H */
