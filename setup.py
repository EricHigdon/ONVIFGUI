import sys
from cx_Freeze import setup, Executable

wsdl_path = 'wsdl'

base = None
if sys.platform == "win32":
    base = "Win32GUI"
    wsdl_path = 'C:\\Users\\ehigdon\\AppData\\Local\\Packages\\PythonSoftwareFoundation.Python.3.9_qbz5n2kfra8p0\\LocalCache\\local-packages\\Lib\\site-packages\\wsdl'

try:
    import wsdl
    for path in wsdl.__path__:
        wsdl_path = path
except ModuleNotFoundError:
    pass

options = {"build_exe": {
    "include_files": [
        wsdl_path,
        ("images/default.jpg", "images/default.jpg")
    ],
    "packages": ["numpy"]
}}

executables = [Executable("ONVIFGUI.py", base=base)]

setup(
    name="ONVIFGUI",
    version="0.1",
    description="ONVIF GUI Application",
    options=options,
    executables=executables,
)
