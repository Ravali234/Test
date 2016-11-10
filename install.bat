@ECHO off

REM This batch file just starts the python server with default settings
REM It also makes sure that we start in the right directory.

ECHO Welcome to High Q Tool Automation Program!!!!

easy_install flufl.enum==4.0
easy_install pyvisa
easy_install quantities
easy_install Bison
pip install flex
pip install -U sphinx

PAUSE

