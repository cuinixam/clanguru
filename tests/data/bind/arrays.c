#include "arrays.h"

int fill_sum(void) {
    int buffer[4] = {1, 2, 3, 4};
    return fill(buffer);
}

int sum4(const int values[4]) {
    return values[0] + values[1] + values[2] + values[3];
}
