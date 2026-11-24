#ifndef ANON_H
#define ANON_H

typedef struct {
    int a;
    struct {
        int b;
    } inner;
} Anon;

int anon_sum(const Anon* value);

#endif
