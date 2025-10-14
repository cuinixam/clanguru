# CHANGELOG


## v0.15.0 (2025-10-14)

### Features

- Add search field to html report
  ([`38f93ca`](https://github.com/cuinixam/clanguru/commit/38f93ca420800cc6559e431f1e5ed45280427f55))


## v0.14.0 (2025-10-14)

### Features

- Add option to exclude irrelevant objects
  ([`22cccda`](https://github.com/cuinixam/clanguru/commit/22cccdab6beac525a1c27a2f1fd3080524f55644))

- Display source files in the object analysis html report
  ([`2d4c27d`](https://github.com/cuinixam/clanguru/commit/2d4c27d9a2c5f48a2abe4ed3bb34a4749ee1ef24))


## v0.13.1 (2025-10-02)

### Bug Fixes

- Same symbols are mocked multiple times
  ([`a31c50f`](https://github.com/cuinixam/clanguru/commit/a31c50f17ed2462ef2158e7970bd6dff9858897a))


## v0.13.0 (2025-09-25)

### Features

- Add option to disable objects traceability matrix
  ([`0dcec99`](https://github.com/cuinixam/clanguru/commit/0dcec9960be79fa452933affe1c93d273db455fc))

- Add option to exclude symbols for object analysis report
  ([`b210312`](https://github.com/cuinixam/clanguru/commit/b2103123453b626e3111184ac2347960b0186506))


## v0.12.5 (2025-09-15)

### Bug Fixes

- Links in pypi are wrong
  ([`4f962df`](https://github.com/cuinixam/clanguru/commit/4f962df315e212d087c1c0877a5d5cf1d72733e4))


## v0.12.4 (2025-09-15)

### Bug Fixes

- Pyyaml dependency is missing
  ([`2111a97`](https://github.com/cuinixam/clanguru/commit/2111a970d894b3303fdd338d966a47f0f179cbd3))

fixes #1


## v0.12.3 (2025-09-12)

### Bug Fixes

- No code block generated for classes sections
  ([`e992f26`](https://github.com/cuinixam/clanguru/commit/e992f2687f1fc84d312f1a0cf82ff27e1ba98802))


## v0.12.2 (2025-09-07)

### Bug Fixes

- Wrong comment allocated to class declaration
  ([`23b9532`](https://github.com/cuinixam/clanguru/commit/23b9532f25f4f13f48aa0674bef58365fdd04f6f))


## v0.12.1 (2025-09-07)

### Bug Fixes

- Comments are not correct if the source has windows newlines
  ([`0fd676f`](https://github.com/cuinixam/clanguru/commit/0fd676fc07ea149b86c3de2ca87472af815df3a0))


## v0.12.0 (2025-09-07)

### Features

- Show error message when file can not be parsed
  ([`970efbf`](https://github.com/cuinixam/clanguru/commit/970efbf75afb4e98ae92d2f5589d007289c8fd7b))


## v0.11.0 (2025-09-07)

### Features

- Get code block location in source file
  ([`53541e9`](https://github.com/cuinixam/clanguru/commit/53541e9bb4bf4927d6b2aed82ca2d938930bc62f))


## v0.10.0 (2025-09-07)

### Bug Fixes

- Function bodies are not correct if the source has windows newlines
  ([`31b4eb2`](https://github.com/cuinixam/clanguru/commit/31b4eb2176a4166e09ef3cf1ef008820890a51f0))

### Features

- Rename docs command and support myst markdown formatter
  ([`7b1b4ab`](https://github.com/cuinixam/clanguru/commit/7b1b4abe0be46acd8fe7dad120565cb74b4de742))


## v0.9.0 (2025-08-28)

### Features

- Add table formatter for docs generator
  ([`b235405`](https://github.com/cuinixam/clanguru/commit/b2354056aaa718cc21b3bf6584dc426bd950c7cf))


## v0.8.1 (2025-08-26)

### Bug Fixes

- Compile commands json export is invalid
  ([`ff13606`](https://github.com/cuinixam/clanguru/commit/ff136067da32298093d3f0a53951b5a19af2f381))


## v0.8.0 (2025-08-25)

### Features

- Filter compile database for source files
  ([`635831f`](https://github.com/cuinixam/clanguru/commit/635831fe9fb1dd667569e7664dd24e1bb851843a))


## v0.7.0 (2025-08-23)

### Features

- Add mock configuration file option
  ([`6b993fa`](https://github.com/cuinixam/clanguru/commit/6b993faef1e2e1453d2cc9c521943dea800ede02))

- Add mock exclude patterns
  ([`9e51ec6`](https://github.com/cuinixam/clanguru/commit/9e51ec6b60466d143e13a915eac4e9b217c96478))

- Add mock generate command for gmock files
  ([`830a442`](https://github.com/cuinixam/clanguru/commit/830a4426eec5f4fb61d0970f8c3ac3b7dbd0f645))

- Add mock partial link object argument
  ([`05a5735`](https://github.com/cuinixam/clanguru/commit/05a5735f92233b69966c0bef0fd9d6b47a951a89))

- Find symbols in translation units
  ([`1cfebcc`](https://github.com/cuinixam/clanguru/commit/1cfebcc97e0c5f456dc06789798f6b3d579ee880))

- Generate mock log file per execution
  ([`9e67022`](https://github.com/cuinixam/clanguru/commit/9e6702296b1277a5cc9a9f19c32bc4165c54e82e))


## v0.6.2 (2025-07-07)

### Bug Fixes

- Explicit jinja2 dependency missing
  ([`a820d94`](https://github.com/cuinixam/clanguru/commit/a820d944adf6265e70b6062a2cd38195d44ab291))


## v0.6.1 (2025-07-07)

### Bug Fixes

- No apps associated with package clanguru
  ([`414f697`](https://github.com/cuinixam/clanguru/commit/414f69701e8fe07f890fed951888768ecdb7e6bb))


## v0.6.0 (2025-07-07)

### Features

- Add column for dependencies to the excel report objects sheet
  ([`a869a9e`](https://github.com/cuinixam/clanguru/commit/a869a9e8e31adf0f8d047dc87a6fca2f318073e3))

- Fixed headers while scrolling in excel report
  ([`8567caf`](https://github.com/cuinixam/clanguru/commit/8567caf244b3f854701eb74cea32e0bc166c2232))


## v0.5.0 (2025-07-07)

### Features

- Add objects data excel report generator
  ([`e9adab2`](https://github.com/cuinixam/clanguru/commit/e9adab2aa5cb953e7c07296dcc78c0c7ad957b53))


## v0.4.0 (2025-04-18)

### Features

- Create objects parent structure
  ([`9bf7b3a`](https://github.com/cuinixam/clanguru/commit/9bf7b3ae95985022d869f1873c51c0e20aca5299))


## v0.3.0 (2025-04-18)

### Features

- Support morel nm symbol types
  ([`f08ffda`](https://github.com/cuinixam/clanguru/commit/f08ffda8d77f0735d5e6c3a5ae55534d57622db6))


## v0.2.0 (2025-04-17)

### Features

- Add objects analyzer report
  ([`118a1ab`](https://github.com/cuinixam/clanguru/commit/118a1ab6b23569d5b5a0e63854fd204c0c3a3e5a))


## v0.1.0 (2024-10-01)

### Features

- Add basic doc generator
  ([`97cd5eb`](https://github.com/cuinixam/clanguru/commit/97cd5eb10ea6db65082acb9021c1feaa3657e303))

- Collect variables
  ([`07f507d`](https://github.com/cuinixam/clanguru/commit/07f507da310f04a2abb369092b1e20b7edab8975))
