#!/usr/bin/env python3

"""ACBF Viewer - GTK Comic Book Viewer for ACBF and CBZ files

Copyright (C) 2011-2019 Robert Kubik
https://launchpad.net/~just-me
"""

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

import os
import sys
import gettext
import getopt

#Check for PyGTK and PIL dependencies.
try:
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk
    from gi.repository import GObject
    gtk_version = (Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version())
    assert GObject.pygobject_version >= (3, 20, 0)
    assert gtk_version >= (3, 20, 0)
except AssertionError:
    print ("You don't have the required versions of GTK+ and/or pyGObject installed.")
    print(('Installed GTK+ version is: %s' % (
        '.'.join([str(n) for n in gtk_version]))))
    print ('Required GTK+ version is: 3.0.0 or higher\n')
    print(('Installed pyGObject version is: %s' % (
        '.'.join([str(n) for n in GObject.pygobject_version]))))
    print ('Required pyGObject version is: 3.0.0 or higher')
    sys.exit(1)
except ImportError:
    print ('pyGObject version 3.0.0 or higher is required to run ACBF Viewer.')
    print ('No version of pyGObject was found on your system.')
    sys.exit(1)

try:
    from PIL import Image
    try:
      im_ver = Image.__version__
    except AttributeError:
      im_ver = Image.VERSION
    assert im_ver >= '1.1.5'
except AssertionError:
    print ("You don't have the required version of the Python Imaging Library (PIL) installed.")
    print(('Installed PIL version is: %s' % Image.VERSION))
    print ('Required PIL version is: 1.1.5 or higher')
    sys.exit(1)
except ImportError:
    print ('Python Imaging Library (PIL) 1.1.5 or higher is required.')
    print ('No version of the Python Imaging Library was found on your system.')
    sys.exit(1)

try:
    import matplotlib
    assert matplotlib.__version__ >= '0.99'
except AssertionError:
    print ("You don't have the required version of the matplotlibl ibrary installed.")
    print(('Installed matplotlib version is: %s' % matplotlib.__version__))
    print ('Required matplotlib version is: 0.99 or higher')
    sys.exit(1)
except ImportError:
    print ('matplotlib version 0.99 or higher is required.')
    print ('No version of matplotlib was found on your system.')
    sys.exit(1)

try:
    import patoolib
except ImportError:
    print("You don't have the required patool library installed.")
    sys.exit(1)

try:
  from . import constants
  from . import main
except Exception:
  import constants
  import main

def print_help():
    print ('Usage:')
    print ('  acbfv [OPTION...] [PATH_TO_FILENAME]')
    print ('\nView acbf comic book documents.\n')
    print ('Options:')
    print ('  -h, --help              Show this help and exit.')
    print ('  -f, --fullscreen        Start the application in fullscreen mode.')
    sys.exit(1)

def run():
    """Run the program."""
    # Use gettext translations as found in the source dir, otherwise based on
    # the install path.

    """print exec_path
    print constants.DATA_DIR
    print constants.CONFIG_DIR
    print constants.HOME_DIR"""

    if os.path.isdir(os.path.join(constants.BASE_DIR, 'messages')):
        gettext.install('acbfv', os.path.join(constants.BASE_DIR, 'messages'))
    else:
        gettext.install('acbfv', os.path.join(constants.BASE_DIR, 'share/locale'))

    fullscreen = False
    show_library = False
    open_path = None
    open_page = 1

    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], 'fh',
            ['fullscreen', 'help'])
    except getopt.GetoptError:
        print_help()
    for opt, value in opts:
        if opt in ('-h', '--help'):
            print_help()
        elif opt in ('-f', '--fullscreen'):
            fullscreen = True

    # Create data (/tmp/acbfv) and config (~/.config/acbfv) directories
    if not os.path.exists(constants.DATA_DIR):
        os.makedirs(constants.DATA_DIR, 0o777)
    if not os.path.exists(constants.CONFIG_DIR):
        os.makedirs(constants.CONFIG_DIR, 0o777)

    if len(args) >= 1:
        open_path = os.path.abspath(args[0])

    # draw main window
    window = main.MainWindow(fullscreen=fullscreen, open_path=open_path, open_page=open_page)
    # set main window icon
    window.set_icon_from_file(os.path.join(constants.ICON_PATH,'acbfv.png'))

    try:
        Gtk.main()
    except KeyboardInterrupt:
        window.terminate_program()

if __name__ in ('__main__', 'share.acbfv.src.acbfv'):
    run()

