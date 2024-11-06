"""toolbar.py - Toolbar for main window.

Copyright (C) 2011-2018 Robert Kubik
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

class Toolbar(gtk.Toolbar):

    def __init__(self, window):
        gtk.Toolbar.__init__(self)
        self._window = window

        self.set_orientation(gtk.Orientation.HORIZONTAL)
        self.set_style(gtk.ToolbarStyle.ICONS)
        self.set_icon_size(gtk.IconSize.SMALL_TOOLBAR)
        self.set_border_width(5)

        tool_button = gtk.ToolButton()
        tool_button.set_stock_id(gtk.STOCK_OPEN)
        tool_button.set_tooltip_text('Open File')
        tool_button.connect("clicked", self._window.open_file)
        self.insert(tool_button, 0)

        tool_button = gtk.ToolButton()
        tool_button.set_stock_id(gtk.STOCK_PREFERENCES)
        tool_button.set_tooltip_text('Preferences')
        tool_button.connect("clicked", self._window.open_preferences)
        self.insert(tool_button, 1)

        tool_button = gtk.ToolButton()
        tool_button.set_stock_id(gtk.STOCK_ABOUT)
        tool_button.set_tooltip_text('About')
        tool_button.connect("clicked", self._window.show_about_window)
        self.insert(tool_button, 2)

        self.insert(gtk.SeparatorToolItem(), 3)

        self.metadata_button = gtk.ToolButton()
        self.metadata_button.set_stock_id(gtk.STOCK_INFO)
        self.metadata_button.set_tooltip_text('Comic Book Meta-Data')
        self.metadata_button.connect("clicked", self._window.show_metadata)
        self.insert(self.metadata_button, 4)

        self.index_button = gtk.ToolButton()
        self.index_button.set_stock_id(gtk.STOCK_INDEX)
        self.index_button.set_tooltip_text('Table of Contents')
        self.index_button.connect("clicked", self._window.show_contents)
        self.insert(self.index_button, 5)

        self.adjustment_button = gtk.ToolButton()
        self.adjustment_button.set_stock_id(gtk.STOCK_SELECT_COLOR)
        self.adjustment_button.set_tooltip_text('Image Adjustment')
        self.adjustment_button.connect("clicked", self._window.adjust_image)
        self.insert(self.adjustment_button, 6)

        self.library_button = gtk.ToolButton()
        self.library_button.set_stock_id(gtk.STOCK_FIND)
        self.library_button.set_tooltip_text('Comic Books Library')
        self.library_button.connect("clicked", self._window.open_library)
        self.insert(self.library_button, 7)

        self.insert(gtk.SeparatorToolItem(), 8)

        self.first_button = gtk.ToolButton()
        self.first_button.set_stock_id(gtk.STOCK_GOTO_FIRST)
        self.first_button.connect("clicked", self._window.goto_first_page)
        self.insert(self.first_button, 9)

        self.prev_button = gtk.ToolButton()
        self.prev_button.set_stock_id(gtk.STOCK_GO_BACK)
        self.prev_button.connect("clicked", self._window.goto_prev_page)
        self.insert(self.prev_button, 10)

        self.entry = gtk.Entry()
        self.entry.set_width_chars(4)
        self.entry.set_text('1')
        self.entry.show()
        entry_toolitem = gtk.ToolItem()
        entry_toolitem.add(self.entry)
        self.insert(entry_toolitem, 11)

        self.next_button = gtk.ToolButton()
        self.next_button.set_stock_id(gtk.STOCK_GO_FORWARD)
        self.next_button.connect("clicked", self._window.goto_next_page)
        self.insert(self.next_button, 12)

        self.last_button = gtk.ToolButton()
        self.last_button.set_stock_id(gtk.STOCK_GOTO_LAST)
        self.last_button.connect("clicked", self._window.goto_last_page)
        self.insert(self.last_button, 13)

        self.insert(gtk.SeparatorToolItem(), 14)

        self.full_screen_button = gtk.ToolButton()
        self.full_screen_button.set_stock_id(gtk.STOCK_FULLSCREEN)
        self.full_screen_button.set_tooltip_text('Fullscreen')
        self.full_screen_button.connect("clicked", self._window.show_fullscreen)
        self.insert(self.full_screen_button, 15)

        self.zoom_button = gtk.ToolButton()
        self.zoom_button.set_stock_id(gtk.STOCK_ZOOM_IN)
        self.zoom_button.set_tooltip_text('Zoom In/Out')
        self.zoom_button.connect("clicked", self._window.zoom_page)
        self.insert(self.zoom_button, 16)

        self.rotate_button = gtk.ToolButton()
        self.rotate_button.set_stock_id(gtk.STOCK_REFRESH)
        self.rotate_button.set_tooltip_text('Rotate Page')
        self.rotate_button.connect("clicked", self._window.rotate_image)
        self.insert(self.rotate_button, 17)

        self.insert(gtk.SeparatorToolItem(), 18)

        self.language = gtk.ComboBoxText()
        for lang in self._window.acbf_document.languages:
          if lang[1] == 'TRUE':
            self.language.append_text(lang[0])
          else:
            self.language.append_text(lang[0] + '#')
        self.language.set_active(0)
        self.language.connect('changed', self._window.change_language)
        language_toolitem = gtk.ToolItem()
        language_toolitem.add(self.language)
        self.insert(language_toolitem, 19)

        self.show_all()

    def update(self):
        self.language.destroy()
        self.language = gtk.ComboBoxText()
        for lang in self._window.acbf_document.languages:
          if lang[1] == 'TRUE':
            self.language.append_text(lang[0])
          else:
            self.language.append_text(lang[0] + '#')
        self.language.set_active(0)
        self.language.connect('changed', self._window.change_language)
        language_toolitem = gtk.ToolItem()
        language_toolitem.add(self.language)
        self.insert(language_toolitem, 19)

        self.show_all()
