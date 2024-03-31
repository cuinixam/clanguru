from pathlib import Path

from py_app_dev.core.docs_utils import fulfills
from py_app_dev.core.logging import logger


class MyApp:
    def __init__(self, project_dir: Path) -> None:
        self.project_dir = project_dir
        self.logger = logger.bind()

    @fulfills("REQ-MY_APP_PROJECT_DIR-0.0.1")
    def run(self) -> None:
        self.logger.info(f"Running {self.__class__.__name__} in  '{self.project_dir}'")
