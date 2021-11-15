import pytest
import coverage
from os import startfile
import pathlib

cov = coverage.Coverage()
cov.start()

pytest.main([])

cov.stop()
cov.save()
cov.html_report()
path = __file__.rsplit("\\", 1)[0] + f"\\htmlcov\\index.html"
startfile(pathlib.WindowsPath(path))
