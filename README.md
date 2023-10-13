# OdfEdit
OdfEdit is an application (implemented in Python) permitting to edit an ODF (Organ Description File, extension .organ) for GrandOrgue in plain text mode, with objects/sections navigator by list or tree, syntax check and help included.
It can be run either directly with the Python file (OdfEdit.py and other files of the src folder) or by using the provided binary files (one for Windows and one for Linux)

Way to run directly the script file :
- install Python 3.x on your computer
- install the Python libraries pillow, lxml and audioplayer
- copy the content of the src folder in a local folder of your computer
- in the local src folder run the command : python3 OdfEdit.py (or in Linux : python3 ./OdfEdit.py)

The Windows binary has been tested in Windows 10
The Linux binary has been tested in Ubuntu 22.04.2 LTS in Oracle VM VirtualBox

From version 2.0, Hauptwerk sample sets can be loaded by OdfEdit which generates a GrandOrgue ODF permitting to use this sample set in GrandOrgue (with some limitations compared to what is possible in Hauptwerk).
