/**
 * @file
 */

#define TEST(suite_NAME, test_NAME)              \
    class suite_NAME##_##test_NAME               \
    {                                            \
    protected:                                   \
        void SetUp();                            \
        void TearDown();                         \
                                                 \
    private:                                     \
        void TestBody();                         \
    };                                           \
    void suite_NAME##_##test_NAME::SetUp() {}    \
    void suite_NAME##_##test_NAME::TearDown() {} \
    void suite_NAME##_##test_NAME::TestBody()

#include "test_gtest.h"

/*!
 * @md
 * ```{test} power_signal_processing.test_power_stays_off
 *    :id: TS_PSP-001
 *    :tests: SWDD_PSP-001
 *
 * ```
 * @endmd
 */
TEST(power_signal_processing, test_power_stays_off)
{
    CREATE_MOCK(mymock);
}

// TODO add more tests
