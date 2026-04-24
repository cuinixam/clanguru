/**
 * @file
 * GTest fixture used to exercise clanguru's doc generator against real
 * google-test macros (TEST, TEST_P). Expanded class names carry the
 * `_Test` suffix that gtest adds internally.
 */
#include <gtest/gtest.h>

/*!
 * @md
 * ```{test} {{ gtest.test }}
 *    :id: TS_PSP-001
 *    :tests: SWDD_PSP-001
 *
 * ```
 * @endmd
 */
TEST(power_signal_processing, test_power_stays_off)
{
    SUCCEED();
}

class BlinkPeriodTest : public ::testing::TestWithParam<int>
{
};

/*!
 * @docs
 * ```{test} BlinkPeriodTests/{{ gtest.test }}/*
 *    :id: TS_LC-003
 *    :tests: SWDD_LC-101
 *
 * ```
 * @enddocs
 */
TEST_P(BlinkPeriodTest, CalculatesCorrectBlinkPeriod)
{
    EXPECT_GE(GetParam(), 0);
}

INSTANTIATE_TEST_SUITE_P(BlinkPeriodTests, BlinkPeriodTest, ::testing::Values(1, 2));
