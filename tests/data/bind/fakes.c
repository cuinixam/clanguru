#include "sensor.h"

int log_message(const char* format, ...) {
    (void)format;
    return 0;
}

void register_callback(void (*callback)(int)) {
    (void)callback;
}
