#include "anon.h"

int anon_sum(const Anon* value) {
    return value->a + value->inner.b;
}
