DEADLAST
--------

Run the Windows game
--------------------
Double-click dist\DEADLAST.exe. The executable includes Python, Pygame, and the
game assets, so Python is not needed on the computer running the game.

The game stores high scores and settings in:
    %LOCALAPPDATA%\DEADLAST

Run from source
---------------
Install Python 3.12, then run:
    py -3.12 -m pip install -r requirements.txt
    py -3.12 main.py

Build the Windows executable
----------------------------
Install the requirements, then double-click build_exe.bat, or run:
    py -3.12 -m PyInstaller --clean --noconfirm --workpath build\DEADLAST main.spec

The one-file build is written to:
    dist\DEADLAST.exe
