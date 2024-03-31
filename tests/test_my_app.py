from pathlib import Path

from py_app_dev.core.docs_utils import validates

from clanguru.my_app import MyApp


@validates("REQ-MY_APP_PROJECT_DIR-0.0.1")
def test_my_app_run(tmp_path: Path) -> None:
    my_app = MyApp(tmp_path)
    my_app.run()
    assert my_app.project_dir == tmp_path
