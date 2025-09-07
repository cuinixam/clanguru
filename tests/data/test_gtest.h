/*





















*/
class MyMock
{
public:
    int someMethod() { return 42; }
};
#define CREATE_MOCK(name) MyMock name
