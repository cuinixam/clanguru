#ifndef TABLE_H
#define TABLE_H

extern int table[3];
extern void (*handler)(int);

int table_at(int index);
void fire(int value);

#endif
