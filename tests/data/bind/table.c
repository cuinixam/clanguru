#include "table.h"

int table_at(int index) {
    return table[index];
}

void fire(int value) {
    if (handler) {
        handler(value);
    }
}
