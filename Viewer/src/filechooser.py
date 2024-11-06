"""filechooser.py - FileChooserDialog implementation.

Copyright (C) 2011-2014 Robert Pastierovic
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

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
import os

try:
  from . import constants
  from . import fileprepare
except Exception:
  import constants
  import fileprepare

class FileChooserDialog(gtk.FileChooserDialog):
    
    """The normal filechooser dialog used with the "Open" toolbar item."""
    
    def __init__(self, window,
                       title='Open File',action=gtk.FileChooserAction.OPEN,
                       buttons=(gtk.STOCK_CANCEL,gtk.ResponseType.CANCEL,gtk.STOCK_OPEN,gtk.ResponseType.OK)):
        self._window = window
        gtk.FileChooserDialog.__init__(self, 'Open File', window, gtk.FileChooserAction.OPEN,
                                       buttons=(gtk.STOCK_CANCEL,gtk.ResponseType.CANCEL,gtk.STOCK_OPEN,gtk.ResponseType.OK))
        self.set_default_response(gtk.ResponseType.OK)
        self.set_current_folder(os.path.dirname(self._window.original_filename))

        # filter
        filter = gtk.FileFilter()
        filter.set_name("Comic files")
        filter.add_pattern("*.acbf")
        filter.add_pattern("*.acv")
        filter.add_pattern("*.cb7")
        filter.add_pattern("*.cbr")
        filter.add_pattern("*.cbt")
        filter.add_pattern("*.cbz")
        filter.add_pattern("*.7z")
        filter.add_pattern("*.tar")
        filter.add_pattern("*.zip")
        self.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        self.add_filter(filter)

        #
        self.connect('response', self.return_filename)
        self.run()

    def return_filename(self, widget, response):
        if response == gtk.ResponseType.OK:
          prepared_file = fileprepare.FilePrepare(self, self.get_filename(), self._window.tempdir, True)
          self._window.filename = prepared_file.filename
          self._window.original_filename = self.get_filename()
        self.destroy()

