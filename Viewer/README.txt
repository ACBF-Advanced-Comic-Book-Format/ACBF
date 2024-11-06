ACBF Viewer - GTK Comic Book Viewer for ACBF and CBZ files

Copyright (C) 2011-2016 Robert Pastierovic
https://launchpad.net/acbf
http://acbf.wikia.com

# -------------------------------------------------------------------------
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# -------------------------------------------------------------------------

ACBF Viewer is capable of displaying comic books in 3 viewing modes (one page,
zoom to page width and zoom on a certain frame/comic book panel), it displays 
various comic book metadata, table of contents, can easily switch between different 
text-layers (translations). Text-layers are drawn automatically to fit into defined 
text-areas (bubbles), different fonts can be defined for semantic tags used on 
text-layers. Comic book library can be filled with comic books which than can be 
sorted and filtered by different kinds of available metadata.

Dependencies
============
ACBF Viewer uses/depends on following libraries:

    GTK (pygtk) to draw user interface
    lxml (python-lxml) to work with XML files
    Python Imaging Library (PIL) to work with images 
    matplotlib for drawing charts in library info dialog 


Download and Installation
=========================
You can download ACBF Viewer from project page at: https://launchpad.net/acbf/+download

Windows
-------
No installation is needed for Windows version. Just download the windows ACBF Viewer package 
(e.g. ACBFViewer-1.03_win32.zip), extract it and run acbfv.exe.

Ubuntu Linux
------------
You will need to install required libraries first:

sudo apt-get install python-lxml python-imaging python-matplotlib

Download and extract linux installation package (for example ACBFViewer-1.03_linux.tar.gz). 
Then navigate to the directory where you extracted it and run:

sudo ./install.py install

After install finishes properly you should be able to find ACBF Viewer in Applications Launcher.

To uninstall run:

sudo ./install.py uninstall
