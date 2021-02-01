import sys
from cx_Freeze import setup, Executable
import wsdl

base = None
if sys.platform == "win32":
    base = "Win32GUI"

wsdl_path = 'wsdl'
for path in wsdl.__path__:
    wsdl_path = path

options = {"build_exe": {
    "include_files": [
        wsdl_path,
        ("images/default.jpg", "images/default.jpg")
    ],
    "packages": ["numpy"]
}}

executables = [Executable("ONVIFGUI.py", base=base)]

setup(
    name="simple_PyQt5",
    version="0.1",
    description="Sample cx_Freeze PyQt5 script",
    options=options,
    executables=executables,
)
