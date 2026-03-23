"""
WeasyPrint setup guide for Windows (project helper file).

This file is documentation in Python format so it can live in the repo.
It does not need to be executed.

---------------------------------------------------------------------------
1) Install Python (if needed)
---------------------------------------------------------------------------
- Download: https://www.python.org/downloads/
- During install, enable: "Add Python to PATH"

---------------------------------------------------------------------------
2) Install GTK runtime dependencies (required by WeasyPrint on Windows)
---------------------------------------------------------------------------
Recommended method: MSYS2

- Download MSYS2: https://www.msys2.org/
- Install it, then open "MSYS2 UCRT64" terminal and run:

    pacman -Syu

  (If it asks to close/reopen terminal, do it, then run:)

    pacman -S mingw-w64-ucrt-x86_64-gtk3

---------------------------------------------------------------------------
3) Add GTK binaries to Windows PATH
---------------------------------------------------------------------------
Add this folder to your Windows PATH:

    C:\\msys64\\ucrt64\\bin

Path settings:
- System Properties -> Environment Variables -> Path -> New

---------------------------------------------------------------------------
4) Create virtualenv and install project dependencies
---------------------------------------------------------------------------
From the project folder in PowerShell:

    py -3 -m venv venv
    .\\venv\\Scripts\\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt

---------------------------------------------------------------------------
5) Verify WeasyPrint works
---------------------------------------------------------------------------
Run:

    python -c "from weasyprint import HTML; HTML(string='<h1>OK</h1>').write_pdf('test_weasy.pdf'); print('ok')"

Expected:
- Prints "ok"
- Creates "test_weasy.pdf" in current directory

---------------------------------------------------------------------------
Troubleshooting
---------------------------------------------------------------------------
If you see DLL errors (cannot load library...):
- Verify GTK is installed via MSYS2
- Verify C:\\msys64\\ucrt64\\bin is in PATH
- Restart terminal after PATH changes
"""

