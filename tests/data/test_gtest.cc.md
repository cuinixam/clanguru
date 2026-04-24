# test_gtest.cc

## Functions

### RUN_ALL_TESTS

```{code-block} c
:linenos:
:lineno-start: 2334

inline int RUN_ALL_TESTS() { return ::testing::UnitTest::GetInstance()->Run(); }
```

### gtest_BlinkPeriodTestsBlinkPeriodTest_EvalGenerator_

```{code-block} c
:linenos:
:lineno-start: 41

INSTANTIATE_TEST_SUITE_P(BlinkPeriodTests, BlinkPeriodTest, ::testing::Values(1, 2))
```

### gtest_BlinkPeriodTestsBlinkPeriodTest_EvalGenerateName_

```{code-block} c
:linenos:
:lineno-start: 41

INSTANTIATE_TEST_SUITE_P(BlinkPeriodTests, BlinkPeriodTest, ::testing::Values(1, 2))
```

## Classes

### power_signal_processing_test_power_stays_off_Test

```{test} power_signal_processing.test_power_stays_off
   :id: TS_PSP-001
   :tests: SWDD_PSP-001

```

```{code-block} c
:linenos:
:lineno-start: 18

TEST(power_signal_processing, test_power_stays_off)
```

### BlinkPeriodTest

```{code-block} c
:linenos:
:lineno-start: 23

class BlinkPeriodTest : public ::testing::TestWithParam<int>
{
}
```

### BlinkPeriodTest_CalculatesCorrectBlinkPeriod_Test

```{test} BlinkPeriodTests/BlinkPeriodTest.CalculatesCorrectBlinkPeriod/*
   :id: TS_LC-003
   :tests: SWDD_LC-101

```

```{code-block} c
:linenos:
:lineno-start: 36

TEST_P(BlinkPeriodTest, CalculatesCorrectBlinkPeriod)
```
