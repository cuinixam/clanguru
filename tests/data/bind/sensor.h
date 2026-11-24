#ifndef SENSOR_H
#define SENSOR_H

typedef enum { MODE_OFF = 0, MODE_ON = 2 } Mode;

typedef struct Point {
    int x;
    int y;
} Point;

struct node {
    struct node* next;
    int value;
};

struct handle;

int read_sensor(unsigned char channel);
extern int sensor_offset;
const char* sensor_name(void);
int log_message(const char* format, ...);
void register_callback(void (*callback)(int));

int measure(unsigned char channel);
int point_sum(const Point* point);
int list_length(const struct node* head);
const char* current_sensor_name(void);
int handle_is_null(const struct handle* handle);
void report(void);

extern Mode current_mode;

#endif
