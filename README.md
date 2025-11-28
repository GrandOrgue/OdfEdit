# OdfEdit

OdfEdit is an application (implemented in Python) permitting to edit an ODF (Organ Description File, extension .organ) for GrandOrgue in plain text mode, with objects/sections navigator by list or tree, syntax check, images files / wav files / panels viewer and help included.
It can be run either directly with the Python file (OdfEdit.py and other files of the src folder) or by using the binary files provided in https://github.com/GrandOrgue/OdfEdit/releases (one for Windows and one for Linux)

Releases notes can be found in github : https://github.com/GrandOrgue/OdfEdit/releases

Way to run directly the script file :

- install Python >=3.10 on your computer (from https://www.python.org/downloads/ to make sure it contains tkinter)
  - on Linux, run `sudo apt-get install python3-tkinter python3-pillow-tk python3-gobject` (replace `apt-get` with your package manager command)
- clone this repository or download its contents (https://github.com/GrandOrgue/OdfEdit/archive/refs/heads/main.zip)
- install and run the application with one of the following methods:
  - automated:
    - in the command line (on Windows, use Git Bash), go to the repository root folder and run `./install.sh`, then `./odfedit.sh`
  - manual:
    - install the Python libraries pillow, lxml, audioplayer and sounddevice
    - install the project with pip : pip install OdfEdit
    - in the local src folder run the command : python3 OdfEdit.py (or in Linux : python3 ./OdfEdit.py)

The Windows binary has been tested in Windows 10
The Linux binary has been tested in Ubuntu 22.04.2 LTS in Oracle VM VirtualBox

From version 2.0, Hauptwerk sample sets can be loaded by OdfEdit which generates a GrandOrgue ODF permitting to use this sample set in GrandOrgue (with some limitations compared to what is possible in Hauptwerk).
Here are elements which can be converted by OdfEdit v2.9 from Hauptwerk to GrandOrgue ODF :

- general organ informations (church name/address, builder, build date, pitch tuning, gain)
- panels
- images, labels
- manuals
- stops, couplers, switches (which can be managed in GrandOrgue)
- combinations (Set, General cancel, General, Divisonal)
- tremulants (wave based or synthesized)
- enclosures (including volume tuning sliders)
- windchests (with associated ranks/tremulants/enclosures)
- ranks (attack/release samples, gain, harmonic number, pitch tuning, loop crossfade length, release crossfade length)
- noises (blower, manuals keys press/release, drawstops engage/disengage)
