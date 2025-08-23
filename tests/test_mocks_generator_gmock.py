import textwrap
from pathlib import Path
from textwrap import dedent

from clanguru.mock_generator import MocksGenerator, MockType


def write_source(tmp_path: Path) -> Path:
    header = tmp_path / "api.h"
    header.write_text(
        dedent(
            """
            extern int foo(int a, int b);
            extern int global_counter;
            """
        )
    )
    source = tmp_path / "impl.c"
    source.write_text(
        dedent(
            """
            #include "api.h"
            int foo(int a, int b) { return a + b; }
            int global_counter = 0;
            """
        )
    )
    return source


def test_generate_gmock(tmp_path: Path) -> None:
    source = write_source(tmp_path)
    outdir = tmp_path / "out"
    gen = MocksGenerator([source], ["foo", "global_counter"], outdir, "mock_my_comp", MockType.GMOCK, None)
    gen.generate()
    header = outdir / "mock_my_comp.h"
    source_code = outdir / "mock_my_comp.cc"

    assert header.read_text() == textwrap.dedent(f"""\
        #ifndef mock_my_comp_h
        #define mock_my_comp_h

        #include "gmock/gmock.h"

        extern "C" {{
        #include "{tmp_path.joinpath("api.h")}"
        }} /* extern "C" */

        class class_mockup;
        typedef class_mockup* mock_ptr_t;
        extern mock_ptr_t mockup_global_ptr;

        class class_mockup {{

        public:
           class_mockup()  {{ mockup_global_ptr = this; }}
           ~class_mockup() {{ mockup_global_ptr = nullptr; }}
           MOCK_METHOD((int), foo, (int a, int b));
        }}; /* class_mockup */

        /* Version A: Create a local object that is destroyed when out of scope */
        #define CREATE_MOCK(name)   class_mockup name

        /* Version B: Allocate an object that will be only explicitly deallocated */
        #define CREATE_PERSISTENT_MOCK()     new class_mockup
        #define DESTROY_PERSISTENT_MOCK()    {{if(mockup_global_ptr) delete mockup_global_ptr;}}

        #endif /* mock_my_comp_h */
        """)

    assert source_code.read_text() == textwrap.dedent("""\
        #include "mock_my_comp.h"

        mock_ptr_t mockup_global_ptr = nullptr;

        int global_counter;

        extern "C" {

        int foo(int a, int b){
            if(mockup_global_ptr)
                return mockup_global_ptr->foo(a, b);
            else
                return (int)0;
        } /* foo */
        }
        """)
