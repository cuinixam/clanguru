#include "color.h"

uint8_t color_red(const RGBColor* color) {
    set_light(*color);
    return color->red;
}
