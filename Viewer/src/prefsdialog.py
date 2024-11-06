"""prefsdialog.py - Preferences Dialog.

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


import os

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk

try:
  from . import constants
  from . import fontselectiondialog
except Exception:
  import constants
  import fontselectiondialog

class PrefsDialog(gtk.Dialog):
    
    """Preferences dialog."""
    
    def __init__(self, window):
        self._window = window
        gtk.Dialog.__init__(self, 'Preferences', window, gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT,
                                  (gtk.STOCK_CLOSE, gtk.ResponseType.CLOSE))
        self.set_resizable(True)
        self.set_border_width(8)
        self.isChanged = False

        notebook = gtk.Notebook()
        notebook.set_border_width(3)

        ## Layout
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(500, 290)
        tab = gtk.VBox(False, 0)
        tab.set_border_width(5)
        scrolled.add_with_viewport(tab)

        # fulscreen toolbar hiding
        button = gtk.CheckButton("Fulscreen Toolbar Hiding")
        button.set_tooltip_text("Hide toolbar when Viewer is in fullscreen mode.")
        button.set_border_width(5)
        if self._window.preferences.get_value("fullscreen_toolbar_hiding") == 'True':
          button.set_active(True)
        else:
          button.set_active(False)
        button.connect("toggled", self.set_toolbar_hiding)

        tab.pack_start(button, False, False, 0)

        # progress bar showing
        button = gtk.CheckButton("Show Progress Bar")
        button.set_border_width(5)
        button.set_tooltip_text("Show progress bar at the bottom to indicate current position inside the comic book.")
        button.connect("toggled", self.set_progressbar_showing)

        tab.pack_start(button, False, False, 0)

        # progress bar width & color
        self.progress_bar_hbox = gtk.HBox(False, 0)
        self.progress_bar_hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('  Progress Bar Width: ')
        self.progress_bar_hbox.pack_start(label, False, False, 0)

        adj = gtk.Adjustment(3, 1, 10, 1.0, 5.0, 0.0)
        progress_bar_width = gtk.SpinButton(adjustment=adj, climb_rate=0, digits=0)        
        progress_bar_width.set_numeric(True)
        progress_bar_width.set_value(int(self._window.preferences.get_value("progress_bar_width")))
        progress_bar_width.show()
        self.progress_bar_hbox.pack_start(progress_bar_width, False, False, 0)
        progress_bar_width.connect('value_changed', self.set_progress_bar_width)

        label = gtk.Label()
        label.set_markup('  Color: ')
        self.progress_bar_hbox.pack_start(label, False, False, 0)

        color = Gdk.RGBA()
        Gdk.RGBA.parse(color, self._window.preferences.get_value("progress_bar_color"))
        
        color_button = gtk.ColorButton()
        color_button.set_rgba(color)
        color_button.set_title('Select Color')
        color_button.connect("color-set", self.set_progress_bar_color)
        self.progress_bar_hbox.pack_start(color_button, False, False, 0)

        if self._window.preferences.get_value("progress_bar_showing") == 'True':
          button.set_active(True)
        else:
          button.set_active(False)
          self.progress_bar_hbox.set_sensitive(False)

        tab.pack_start(self.progress_bar_hbox, False, False, 0)

        # scroll step
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Scroll Step (fit width zoom level): ')
        label.set_tooltip_text("Scrolling step (in pixels) to move comic book page when in fit width zoom mode.")
        hbox.pack_start(label, False, False, 0)

        self.scroll_step = gtk.ComboBoxText()
        self.scroll_step.append_text('5%')
        self.scroll_step.append_text('10%')
        self.scroll_step.append_text('15%')
        self.scroll_step.append_text('20%')
        self.scroll_step.append_text('25%')
        self.scroll_step.append_text('30%')
        self.scroll_step.append_text('35%')
        self.scroll_step.append_text('40%')
        self.scroll_step.append_text('45%')
        self.scroll_step.append_text('50%')
        self.scroll_step.set_active(int(self._window.preferences.get_value("scroll_step")))
        hbox.pack_start(self.scroll_step, False, False, 0)
        self.scroll_step.connect('changed', self.set_scroll_step)

        tab.pack_start(hbox, False, False, 0)

        # default language layer
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Default language layer: ')
        label.set_tooltip_text("Default language layer with which books are opened. This setting also has effect on book titles/annotations displayed in library.")
        hbox.pack_start(label, False, False, 0)

        self.default_language = gtk.ComboBoxText()
        for lang in constants.LANGUAGES:
          self.default_language.append_text(lang.replace('??#', 'None'))
        self.default_language.set_active(int(self._window.preferences.get_value("default_language")))
        hbox.pack_start(self.default_language, False, False, 0)
        self.default_language.connect('changed', self.set_default_language)

        tab.pack_start(hbox, False, False, 0)

        notebook.insert_page(scrolled, gtk.Label('Layout'), -1)

        ## fonts
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(400, 150)
        tab = gtk.VBox(False, 0)
        tab.set_border_width(5)
        scrolled.add_with_viewport(tab)

        # Normal Font
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)
        
        label = gtk.Label()
        label.set_markup('Normal: ')
        label.set_tooltip_text("Default font to be used for drawing text layer.")
        hbox.pack_start(label, False, False, 0)


        self.normal_font = gtk.Button()
        self.normal_font.font_idx = 0
        for idx, font in enumerate(constants.FONTS_LIST, start = 0):
          if font[0] == self._window.preferences.get_value("normal_font"):
            self.normal_font.font_idx = idx
            self.normal_font.set_label(font[0].replace('.ttf', '').replace('.TTF', '').replace('.otf', '').replace('.OTF', ''))

        hbox.pack_start(self.normal_font, False, False, 0)
        self.normal_font.connect("clicked", self.set_normal_font)
        tab.pack_start(hbox, False, False, 0)

        # Emphasis Font
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Emphasis: ')
        label.set_tooltip_text("Font to be used for drawing text inside <emphasis> element.")
        hbox.pack_start(label, False, False, 0)


        self.emphasis_font = gtk.Button()
        self.emphasis_font.font_idx = 0
        for idx, font in enumerate(constants.FONTS_LIST, start = 0):
          if font[0] == self._window.preferences.get_value("emphasis_font"):
            self.emphasis_font.font_idx = idx
            self.emphasis_font.set_label(font[0].replace('.ttf', '').replace('.TTF', '').replace('.otf', '').replace('.OTF', ''))

        hbox.pack_start(self.emphasis_font, False, False, 0)
        self.emphasis_font.connect("clicked", self.set_emphasis_font)
        tab.pack_start(hbox, False, False, 0)

        # Strong Font
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Strong: ')
        label.set_tooltip_text("Font to be used for drawing text inside <strong> element.")
        hbox.pack_start(label, False, False, 0)


        self.strong_font = gtk.Button()
        self.strong_font.font_idx = 0
        for idx, font in enumerate(constants.FONTS_LIST, start = 0):
          if font[0] == self._window.preferences.get_value("strong_font"):
            self.strong_font.font_idx = idx
            self.strong_font.set_label(font[0].replace('.ttf', '').replace('.TTF', '').replace('.otf', '').replace('.OTF', ''))

        hbox.pack_start(self.strong_font, False, False, 0)
        self.strong_font.connect("clicked", self.set_strong_font)
        tab.pack_start(hbox, False, False, 0)

        # Code Font
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Code: ')
        label.set_tooltip_text("Font used to draw text inside <code> element.")
        hbox.pack_start(label, False, False, 0)

        self.code_font = gtk.Button()
        self.code_font.font_idx = 0
        for idx, font in enumerate(constants.FONTS_LIST, start = 0):
          if font[0] == self._window.preferences.get_value("code_font"):
            self.code_font.font_idx = idx
            self.code_font.set_label(font[0].replace('.ttf', '').replace('.TTF', '').replace('.otf', '').replace('.OTF', ''))

        hbox.pack_start(self.code_font, False, False, 0)
        self.code_font.connect("clicked", self.set_code_font)
        tab.pack_start(hbox, False, False, 0)

        # Commentary Font
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Commentary: ')
        label.set_tooltip_text("Font used to draw text inside <commentary> element if no other semantic tag is used.")
        hbox.pack_start(label, False, False, 0)

        self.commentary_font = gtk.Button()
        self.commentary_font.font_idx = 0
        for idx, font in enumerate(constants.FONTS_LIST, start = 0):
          if font[0] == self._window.preferences.get_value("commentary_font"):
            self.commentary_font.font_idx = idx
            self.commentary_font.set_label(font[0].replace('.ttf', '').replace('.TTF', '').replace('.otf', '').replace('.OTF', ''))

        hbox.pack_start(self.commentary_font, False, False, 0)
        self.commentary_font.connect("clicked", self.set_commentary_font)
        tab.pack_start(hbox, False, False, 0)

        # font colors
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Font colors:   Default: ')
        label.set_tooltip_text("Default font color to be used for drawing text layer and font color to be used for drawing text inside <inverted> element.")
        hbox.pack_start(label, False, False, 0)

        color = Gdk.RGBA()
        Gdk.RGBA.parse(color, self._window.preferences.get_value("font_color_default"))
        
        color_button = gtk.ColorButton()
        color_button.set_rgba(color)
        color_button.set_title('Select Color')
        color_button.connect("color-set", self.set_font_color_default)
        hbox.pack_start(color_button, False, False, 0)

        label_i = gtk.Label()
        label_i.set_markup(' Inverted: ')
        hbox.pack_start(label_i, False, False, 0)

        color = Gdk.RGBA()
        Gdk.RGBA.parse(color, self._window.preferences.get_value("font_color_inverted"))
        
        color_button_i = gtk.ColorButton()
        color_button_i.set_rgba(color)
        color_button_i.set_title('Select Color')
        color_button_i.connect("color-set", self.set_font_color_inverted)
        hbox.pack_start(color_button_i, False, False, 0)

        tab.pack_start(hbox, False, False, 0)

        #
        notebook.insert_page(scrolled, gtk.Label('Fonts'), -1)

        ## Image
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(400, 180)
        tab = gtk.VBox(False, 0)
        tab.set_border_width(5)
        scrolled.add_with_viewport(tab)

        # stretch image
        button = gtk.CheckButton("Image stretch")
        button.set_border_width(5)
        button.set_tooltip_text("Stretch image to the whole window area in case the the image is smaller. Applies to frame zoom level.")
        if self._window.preferences.get_value("image_stretch") == 'True':
          button.set_active(True)
        else:
          button.set_active(False)
        button.connect("toggled", self.set_image_stretch)

        tab.pack_start(button, False, False, 0)

        # remove border
        button = gtk.CheckButton("Remove border")
        button.set_border_width(5)
        button.set_tooltip_text("Crop image automatically to remove borders.")
        if self._window.preferences.get_value("crop_border") == 'True':
          button.set_active(True)
        else:
          button.set_active(False)
        button.connect("toggled", self.set_crop_border)

        tab.pack_start(button, False, False, 0)

        # autorotate image
        button = gtk.CheckButton("Autorotate image")
        button.set_border_width(5)
        button.set_tooltip_text("Automatically rotate image to best fit into available drawing space.")
        if self._window.preferences.get_value("autorotate") == 'True':
          button.set_active(True)
        else:
          button.set_active(False)
        button.connect("toggled", self.set_autorotate)

        tab.pack_start(button, False, False, 0)

        # resize quality
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Image Resize Filter: ')
        hbox.pack_start(label, False, False, 0)

        self.image_filter = gtk.ComboBoxText()
        self.image_filter.append_text('Nearest (fastest)')
        self.image_filter.append_text('Bilinear')
        self.image_filter.append_text('Bicubic')
        self.image_filter.append_text('Antialias (slowest)')
        self.image_filter.set_active(int(self._window.preferences.get_value("image_resize_filter")))
        hbox.pack_start(self.image_filter, False, False, 0)
        self.image_filter.connect('changed', self.set_image_resize_filter)

        tab.pack_start(hbox, False, False, 0)

        # Animations
        self.animations_hbox = gtk.HBox(False, 0)
        self.animations_hbox.set_border_width(5)

        button = gtk.CheckButton("Animations")
        button.set_border_width(5)
        button.set_tooltip_text("Fade in effect and animated movement between frames.")
        if self._window.preferences.get_value("animation") == 'True':
          button.set_active(True)
        else:
          button.set_active(False)
        button.connect("toggled", self.set_animation)
        self.animations_hbox.pack_start(button, False, False, 0)

        label = gtk.Label()
        label.set_markup('  Delay: ')
        self.animations_hbox.pack_start(label, False, False, 0)

        adj = gtk.Adjustment(3, 1, 10, 1.0, 5.0, 0.0)
        delay = gtk.SpinButton(adjustment=adj, climb_rate=0, digits=0)        
        delay.set_numeric(True)
        delay.set_value(int(self._window.preferences.get_value("animation_delay")))
        delay.show()
        self.animations_hbox.pack_start(delay, False, False, 0)
        delay.connect('value_changed', self.set_animation_delay)

        tab.pack_start(self.animations_hbox, False, False, 0)

        #
        notebook.insert_page(scrolled, gtk.Label('Image'), -1)

        ## Library
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(400, 180)
        tab = gtk.VBox(False, 0)
        tab.set_border_width(5)
        scrolled.add_with_viewport(tab)

        # Library layout
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Default library layout: ')
        hbox.pack_start(label, False, False, 0)

        self.library_layout = gtk.ComboBoxText()
        self.library_layout.append_text('Normal')
        self.library_layout.append_text('Compact')
        self.library_layout.append_text('List')
        self.library_layout.set_active(int(self._window.preferences.get_value("library_layout")))
        hbox.pack_start(self.library_layout, False, False, 0)
        self.library_layout.connect('changed', self.set_library_layout)

        tab.pack_start(hbox, False, False, 0)

        # Books per page
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Books per page: ')
        hbox.pack_start(label, False, False, 0)

        adj = gtk.Adjustment(10, 1, 100, 1.0, 5.0, 0.0)
        self.books_per_page = gtk.SpinButton(adjustment=adj, climb_rate=0, digits=0)        
        self.books_per_page.set_numeric(True)
        self.books_per_page.set_value(int(self._window.preferences.get_value("library_books_per_page")))
        self.books_per_page.show()
        hbox.pack_start(self.books_per_page, False, False, 0)
        self.books_per_page.connect('value_changed', self.set_books_per_page)

        tab.pack_start(hbox, False, False, 0)

        # Library default sort order
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Default Sort Order: ')
        hbox.pack_start(label, False, False, 0)

        self.library_order = gtk.ComboBoxText()
        for sort_item in ['Title', 'Series', 'Author(s)', 'Publisher', 'Publish Date', 'Languages', 'Rating']:
          self.library_order.append_text(sort_item)
        self.library_order.set_active(int(self._window.preferences.get_value("library_default_sort_order")))
        hbox.pack_start(self.library_order, False, False, 0)
        self.library_order.connect('changed', self.set_library_order)

        tab.pack_start(hbox, False, False, 0)

        # Library cleanup
        button = gtk.CheckButton("Remove non-existing books")
        button.set_border_width(5)
        button.set_tooltip_text("Removes books that no longer exist at location from where they were imported. Books are checked on library startup.")
        if self._window.preferences.get_value("library_cleanup") == 'True':
          button.set_active(True)
        else:
          button.set_active(False)
        button.connect("toggled", self.set_library_cleanup)

        tab.pack_start(button, False, False, 0)

        #
        notebook.insert_page(scrolled, gtk.Label('Library'), -1)

        # show it
        self.vbox.pack_start(notebook, False, False, 0)
        self.show_all()

        self.isChanged = False

        self.run()

    def set_default_language(self, widget):
        self._window.preferences.set_value("default_language", str(self.default_language.get_active()))
        self.isChanged = True
        return True

    def set_library_layout(self, widget):
        self._window.preferences.set_value("library_layout", str(self.library_layout.get_active()))
        self.isChanged = True
        return True

    def set_library_order(self, widget):
        self._window.preferences.set_value("library_default_sort_order", str(self.library_order.get_active()))
        self.isChanged = True
        return True

    def set_bg_color(self, widget):
        self._window.preferences.set_value("bg_color", widget.get_color().to_string())
        self.isChanged = True
        return True

    def set_progress_bar_color(self, widget):
        self._window.preferences.set_value("progress_bar_color", widget.get_color().to_string())
        self.isChanged = True
        return True

    def set_toolbar_hiding(self, widget):
        if widget.get_active():
          self._window.preferences.set_value("fullscreen_toolbar_hiding", "True")
        else:
          self._window.preferences.set_value("fullscreen_toolbar_hiding", "False")
        self.isChanged = True
        return True

    def set_progressbar_showing(self, widget):
        if widget.get_active():
          self._window.preferences.set_value("progress_bar_showing", "True")
          self.progress_bar_hbox.set_sensitive(True)
        else:
          self._window.preferences.set_value("progress_bar_showing", "False")
          self.progress_bar_hbox.set_sensitive(False)
        self.isChanged = True
        return True

    def set_hidpi(self, widget):
        if widget.get_active():
          self._window.preferences.set_value("hidpi", "True")
        else:
          self._window.preferences.set_value("hidpi", "False")
        self.isChanged = True
        return True

    def set_progress_bar_width(self, widget):
        self._window.preferences.set_value("progress_bar_width", str(widget.get_value_as_int()))
        self.isChanged = True
        return True

    def set_animation_delay(self, widget):
        self._window.preferences.set_value("animation_delay", str(widget.get_value_as_int()))
        self.isChanged = True
        return True
      
    def set_image_stretch(self, widget):
        if widget.get_active():
          self._window.preferences.set_value("image_stretch", "True")
        else:
          self._window.preferences.set_value("image_stretch", "False")
        self.isChanged = True
        return True

    def set_crop_border(self, widget):
        if widget.get_active():
          self._window.preferences.set_value("crop_border", "True")
        else:
          self._window.preferences.set_value("crop_border", "False")
        self.isChanged = True
        return True

    def set_autorotate(self, widget):
        if widget.get_active():
          self._window.preferences.set_value("autorotate", "True")
        else:
          self._window.preferences.set_value("autorotate", "False")
        self.isChanged = True
        return True

    def set_image_resize_filter(self, widget):
        self._window.preferences.set_value("image_resize_filter", str(self.image_filter.get_active()))
        self.isChanged = True
        return True

    def set_animation(self, widget):
        if widget.get_active():
          self._window.preferences.set_value("animation", "True")
        else:
          self._window.preferences.set_value("animation", "False")
        self.isChanged = True
        return True

    def set_scroll_step(self, widget):
        self._window.preferences.set_value("scroll_step", str(self.scroll_step.get_active()))
        self.isChanged = True
        return True

    def set_normal_font(self, widget):
        self.font_dialog = fontselectiondialog.FontSelectionDialog(self, "normal_font", self.normal_font.font_idx)
        self.normal_font.set_label(self._window.preferences.get_value("normal_font").replace('.ttf', '').replace('.TTF', '').replace('.otf', '').replace('.OTF', ''))
        for idx, font in enumerate(constants.FONTS_LIST, start = 0):
          if font[0] == self._window.preferences.get_value("normal_font"):
            self.normal_font.font_idx = idx
        self.isChanged = True
        return True

    def set_emphasis_font(self, widget):
        self.font_dialog = fontselectiondialog.FontSelectionDialog(self, "emphasis_font", self.emphasis_font.font_idx)
        self.emphasis_font.set_label(self._window.preferences.get_value("emphasis_font").replace('.ttf', '').replace('.TTF', '').replace('.otf', '').replace('.OTF', ''))
        for idx, font in enumerate(constants.FONTS_LIST, start = 0):
          if font[0] == self._window.preferences.get_value("emphasis_font"):
            self.emphasis_font.font_idx = idx
        self.isChanged = True
        return True

    def set_strong_font(self, widget):
        self.font_dialog = fontselectiondialog.FontSelectionDialog(self, "strong_font", self.strong_font.font_idx)
        self.strong_font.set_label(self._window.preferences.get_value("strong_font").replace('.ttf', '').replace('.TTF', '').replace('.otf', '').replace('.OTF', ''))
        for idx, font in enumerate(constants.FONTS_LIST, start = 0):
          if font[0] == self._window.preferences.get_value("strong_font"):
            self.strong_font.font_idx = idx
        self.isChanged = True
        return True

    def set_code_font(self, widget):
        self.font_dialog = fontselectiondialog.FontSelectionDialog(self, "code_font", self.code_font.font_idx)
        self.code_font.set_label(self._window.preferences.get_value("code_font").replace('.ttf', '').replace('.TTF', '').replace('.otf', '').replace('.OTF', ''))
        for idx, font in enumerate(constants.FONTS_LIST, start = 0):
          if font[0] == self._window.preferences.get_value("code_font"):
            self.code_font.font_idx = idx
        self.isChanged = True
        return True

    def set_commentary_font(self, widget):
        self.font_dialog = fontselectiondialog.FontSelectionDialog(self, "commentary_font", self.commentary_font.font_idx)
        self.commentary_font.set_label(self._window.preferences.get_value("commentary_font").replace('.ttf', '').replace('.TTF', '').replace('.otf', '').replace('.OTF', ''))
        for idx, font in enumerate(constants.FONTS_LIST, start = 0):
          if font[0] == self._window.preferences.get_value("commentary_font"):
            self.commentary_font.font_idx = idx
        self.isChanged = True
        return True

    def set_font_color_default(self, widget):
        self._window.preferences.set_value("font_color_default", widget.get_color().to_string())
        self.isChanged = True
        return True

    def set_font_color_inverted(self, widget):
        self._window.preferences.set_value("font_color_inverted", widget.get_color().to_string())
        self.isChanged = True
        return True

    def set_books_per_page(self, widget):
        self._window.preferences.set_value("library_books_per_page", str(widget.get_value_as_int()))
        self.isChanged = True
        return True

    def set_library_cleanup(self, widget):
        if widget.get_active():
          self._window.preferences.set_value("library_cleanup", "True")
        else:
          self._window.preferences.set_value("library_cleanup", "False")
        self.isChanged = True
        return True
    
