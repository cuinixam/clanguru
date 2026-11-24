#include "sensor.h"

Mode current_mode = MODE_ON;

int measure(unsigned char channel) {
    return read_sensor(channel) + sensor_offset;
}

int point_sum(const Point* point) {
    return point->x + point->y;
}

int list_length(const struct node* head) {
    int length = 0;
    for (; head != 0; head = head->next) {
        length++;
    }
    return length;
}

const char* current_sensor_name(void) {
    return sensor_name();
}

int handle_is_null(const struct handle* handle) {
    return handle == 0;
}

void report(void) {
    log_message("%d", 1);
    register_callback(0);
}
