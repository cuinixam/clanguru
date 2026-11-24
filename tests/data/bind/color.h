#ifndef COLOR_H
#define COLOR_H

#include <stdint.h>

typedef struct {
    uint8_t red;
    uint8_t green;
    uint8_t blue;
} RGBColor;

uint8_t color_red(const RGBColor* color);
void set_light(RGBColor value);

#endif
