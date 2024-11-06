"""main.py - Main window.

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


import sys
import os
import shutil
import random
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk as gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import re
from PIL import Image
from xml.sax.saxutils import escape, unescape
from time import sleep
import threading

try:
  from . import constants
  from . import toolbar
  from . import filechooser
  from . import fileprepare
  from . import acbfdocument
  from . import comicpage
  from . import preferences
  from . import prefsdialog
  from . import history
  from . import library
except Exception:
  import constants
  import toolbar
  import filechooser
  import fileprepare
  import acbfdocument
  import comicpage
  import preferences
  import prefsdialog
  import history
  import library

class MainWindow(gtk.Window):

    """The ACBF main window"""

    def __init__(self, fullscreen=False, open_path=None, open_page=1):
        # Preferences
        self.preferences = preferences.Preferences()
        self.history = history.History()
        self._window = self

        # Window properties
        gtk.Window.__init__(self, gtk.WindowType.TOPLEVEL)
        self.set_title('ACBF Viewer')
        self.set_size_request(730, 430)
        self.isFullscreen = fullscreen
        if self.isFullscreen:
          self.fullscreen()
        self.zoom_level = 1 #(1 = full page, 2 = fit width, 3 = frame level)
        self.zoom_list = [1,2,3,2]
        self.zoom_index = 0
        self.fit_width_start = self.fit_width_start_old = 0
        self.page_number = 1
        self.frame_number = 1
        self.PixBufImage_width = self.PixBufImage_height = 0
        self.filename = open_path
        self.is_rendering = False
        self.scroll_to_next_page = False
        self.scroll_to_prior_page = False
        self.scroll_value = 0
        self.show_all()

        self.reset_enhancement_values()

        # check if custom temp dir is defined
        self.tempdir_root = str(os.path.join(self.preferences.get_value("tmpfs"), 'acbfv'))
        if self.preferences.get_value("tmpfs") != 'False':
          print("Temporary directory override set to: " + self.tempdir_root)
        else:
          self.tempdir_root = constants.DATA_DIR

        self.tempdir =  str(os.path.join(self.tempdir_root, ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for i in range(10))))
        self.library_dir = str(os.path.join(self.tempdir_root, 'Library'))

        if not os.path.exists(self.tempdir):
          os.makedirs(self.tempdir, 0o700)
        
        if not os.path.exists(self.library_dir):
          os.makedirs(self.library_dir, 0o700)
        if not os.path.exists(os.path.join(constants.CONFIG_DIR, 'Covers')):
          os.makedirs(os.path.join(constants.CONFIG_DIR, 'Covers'), 0o700)

        if self.filename == None:
          self.filename = "/home/whale/Work/ACBF/trunk/Sample Comic Book/xDoctorow, Cory - Craphound.acbf"
          self.original_filename = self.filename
        else:
          prepared_file = fileprepare.FilePrepare(self, open_path, self.tempdir, True)
          self.filename = prepared_file.filename
          self.original_filename = open_path
        self.acbf_document = acbfdocument.ACBFDocument(self, self.filename)

        # get last reading position
        (self.page_number, self.frame_number, self.zoom_level, self.language_layer) = self.history.get_book_details(self.original_filename)
        if self.page_number > self.acbf_document.pages_total:
          self.page_number = 1
        if self.acbf_document.valid:
          try:
            self.set_title('%s - ACBF Viewer' % unescape(self.acbf_document.book_title[self.acbf_document.languages[self.language_layer][0]]))
          except:
            try:
              self.set_title('%s - ACBF Viewer' % unescape(self.acbf_document.book_title['en']))
            except:
              self.set_title('%s - ACBF Viewer' % unescape(self.acbf_document.book_title[list(self.acbf_document.book_title.items())[0][0]]))

        # Toolbar
        vbox = gtk.VBox(False, 0)
        self.toolbar = toolbar.Toolbar(self)
        self.toolbar.show_all()
        vbox.pack_start(self.toolbar, False, False, 0)

        # Comic Page box
        self.drawable_size = (730, 430 - self.toolbar.get_allocation().height)
        self.layout = gtk.Layout()
        self.layout.set_size(self.drawable_size[0], self.drawable_size[1])
        
        self.scrolled = gtk.ScrolledWindow()
        self.scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.NEVER)
        self.current_x = self.scrolled.get_hadjustment().get_value()
        self.current_y = self.scrolled.get_vadjustment().get_value()

        self.pixbuf = None
        self.scrolled.get_hscrollbar().hide()
        self.scrolled.get_vscrollbar().hide()
        
        self.comic_page_box = gtk.Image()
        try:
          self.scrolled.set_can_focus(True)
        except:
          None

        self.fixed = gtk.Fixed()

        self.bg_image = gtk.Image()
        self.bg_image.set_size_request(self.drawable_size[0], self.drawable_size[1])
        self.bg_image.modify_bg(gtk.StateType.NORMAL, None)
        self.fixed.put(self.bg_image, 0, 0)

        self.fixed.put(self.comic_page_box, 1000, 1000)
        self.scrolled.add(self.fixed)

        self.layout.put(self.scrolled, 0, 0)

        # Loading page icon
        self.loading_page_alignment = gtk.Alignment(xalign=1, yalign=1, xscale=0.0, yscale=0.0)
        self.loading_page_icon = gtk.Image()
        self.loading_page_icon.set_from_stock(gtk.STOCK_REFRESH, gtk.IconSize.SMALL_TOOLBAR)
        self.loading_page_alignment.add(self.loading_page_icon)
        self.layout.put(self.loading_page_alignment, 0, 0)

        # Comic page object
        self.comic_page = comicpage.ComicPage(self)

        # Progress bar
        self.progress_bar_alignment = gtk.Alignment(xalign=0, yalign=1, xscale=0.0, yscale=0.0)
        self.progress_bar_icon = gtk.Image()
        self.progress_bar_icon.set_from_pixbuf(comicpage.pil_to_pixbuf(Image.new("RGB", (1, 1), "#000"), "#000"))
        self.progress_bar_alignment.add(self.progress_bar_icon)
        self.layout.put(self.progress_bar_alignment, 0, 0)

        vbox.pack_start(self.layout, True, True, 0)
        vbox.show()
        self.add(vbox)

        # Events
        self.connect('delete_event', self.terminate_program)
        self.connect('size-allocate', self.configure_window)
        self.connect('key_press_event', self.key_pressed)
        self.connect('scroll-event', self.mouse_scroll)
        self.layout.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.layout.connect("button_press_event", self.mouse_clicked)
        self.scrolled.get_vadjustment().connect("value-changed", self.scroll_scrolled)

        # show
        self.loading_page_alignment.set_size_request(self.drawable_size[0] - 10, self.drawable_size[1] - 10)
        self.progress_bar_alignment.set_size_request(self.drawable_size[0], self.drawable_size[1])
        self.layout.grab_focus()

        self.toolbar.language.set_active(self.language_layer)

        self.show_all()
        self.set_size_request(729, 430)
        self.drawable_size = (730, 430 - self.toolbar.get_allocation().height)

        self.zoom_index = self.zoom_level - 1
        if self.zoom_index == 0:
          self.toolbar.zoom_button.set_stock_id(gtk.STOCK_ZOOM_IN)
        else:
          self.toolbar.zoom_button.set_stock_id(gtk.STOCK_ZOOM_OUT)

        self.loading_page_icon.hide()
        while gtk.events_pending():
          gtk.main_iteration()
        self.set_size_request(730, 430)


    # toolbar actions
    def open_file(self, *args):
      self.history.set_book_details(self.original_filename, self.page_number, self.frame_number, self.zoom_level, self.toolbar.language.get_active())
      filename_before = self.filename
      self.filechooser = filechooser.FileChooserDialog(self)
      if filename_before != self.filename and self.filename != None:
        self.acbf_document = acbfdocument.ACBFDocument(self, self.filename)
        self.toolbar.update()
        (self.page_number, self.frame_number, self.zoom_level, self.language_layer) = self.history.get_book_details(self.original_filename)
        if self.page_number > self.acbf_document.pages_total:
          self.page_number = 1
        try:
          self.set_title('%s - ACBF Viewer' % unescape(self.acbf_document.book_title[self.acbf_document.languages[self.language_layer][0]]))
        except:
          try:
            self.set_title('%s - ACBF Viewer' % unescape(self.acbf_document.book_title['en']))
          except:
            self.set_title('%s - ACBF Viewer' % unescape(self.acbf_document.book_title[list(self.acbf_document.book_title.items())[0][0]]))

        #set default language layer
        if self.preferences.get_value("default_language") != "0":
          for idx, doc_lang in enumerate(self.acbf_document.languages, start = 0):
            if doc_lang[1] == 'TRUE':
              for list_lang in constants.LANGUAGES:
                if doc_lang[0] == list_lang == constants.LANGUAGES[int(self.preferences.get_value("default_language"))]:
                  self.language_layer = idx

        self.zoom_index = self.zoom_level - 1
        if self.zoom_index == 0:
          self.toolbar.zoom_button.set_stock_id(gtk.STOCK_ZOOM_IN)
        else:
          self.toolbar.zoom_button.set_stock_id(gtk.STOCK_ZOOM_OUT)
        self.comic_page.rotation = self.fit_width_start = 0
        self.comic_page.text_areas = []
        self.reset_enhancement_values()

        self.set_size_request(self.get_allocation().width + 1, self.get_allocation().height)
        if self.language_layer == 0:
          self.toolbar.language.set_active(self.language_layer)
          self.display_page(True, None)
        else:
          self.toolbar.language.set_active(self.language_layer)

        self.drawable_size = (self.layout.get_allocation().width, self.layout.get_allocation().height)
        if self.zoom_level == 3:
          self.zoom_to_frame(self.frame_number, move=True)
        self.set_size_request(self.get_allocation().width - 1, self.get_allocation().height)

      else:
        self.acbf_document.valid = False
        self.acbf_document.coverpage = None
        self.acbf_document.cover_thumb = None
        self.acbf_document.pages_total = 0
        self.acbf_document.bg_color = '#000000'
        self.acbf_document.valid = False
        self.acbf_document.languages = [('??', 'FALSE')]
        self.acbf_document.contents_table = []
        self.set_title('ACBF Viewer')
        self.toolbar.language.set_active(0)
        self.display_page(False, None)
      return True

    def open_preferences(self, *args):
      self.prefs_dialog = prefsdialog.PrefsDialog(self)
      if self.prefs_dialog.isChanged:
        self.preferences.save_preferences()
        self.prefs_dialog.destroy()
        if self.acbf_document.valid:
          self.display_page(True, None)
      else:
        self.prefs_dialog.destroy()
      return

    def adjust_image(self, *args):
      dialog = gtk.Dialog('Image Adjustment', self, gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT,
                          (gtk.STOCK_CLOSE, gtk.ResponseType.CLOSE))
      dialog.set_resizable(False)
      dialog.set_border_width(8)

      # image brightness
      hbox = gtk.HBox(False, 0)
      hbox.set_border_width(5)

      self.brightness_button = gtk.CheckButton("Adjust brightness: ")
      self.brightness_button.connect("toggled", self.toggle_image_brightness)
      self.brightness_button.set_tooltip_text("The factor -1.0 gives a black image, 0.0 gives the original image, and a factor of 1.0 gives a bright image.")
      if self.brightness_button_toggle == True:
        self.brightness_button.set_active(True)
      else:
        self.brightness_button.set_active(False)
      hbox.pack_start(self.brightness_button, False, False, 0)

      brightness_adj = gtk.Adjustment(1.0, -0.9, 1, 0.1, 0.5, 0.0)
      self.image_brightness = gtk.SpinButton(adjustment=brightness_adj, climb_rate=0.1, digits=1)
      self.image_brightness.set_numeric(True)
      self.image_brightness.set_value(self.image_brightness_value)
      self.image_brightness.show()
      hbox.pack_start(self.image_brightness, False, False, 0)
      self.image_brightness.connect('value_changed', self.set_image_brightness)

      if self.brightness_button_toggle == True:
        self.image_brightness.set_sensitive(True)
      else:
        self.image_brightness.set_sensitive(False)

      dialog.vbox.pack_start(hbox, False, False, 0)

      # image contrast
      hbox = gtk.HBox(False, 0)
      hbox.set_border_width(5)

      self.contrast_button = gtk.CheckButton("Adjust contrast: ")
      self.contrast_button.connect("toggled", self.toggle_image_contrast)
      self.contrast_button.set_tooltip_text("The factor -1.0 solid grey image, factor 0.0 gives the original image, and a factor of 1.0 gives a high contrast image.")
      if self.contrast_button_toggle == True:
        self.contrast_button.set_active(True)
      else:
        self.contrast_button.set_active(False)
      hbox.pack_start(self.contrast_button, False, False, 0)

      contrast_adj = gtk.Adjustment(1.0, -0.9, 1, 0.1, 0.5, 0.0)
      self.image_contrast = gtk.SpinButton(adjustment=contrast_adj, climb_rate=0.1, digits=1)
      self.image_contrast.set_numeric(True)
      self.image_contrast.set_value(self.image_contrast_value)
      self.image_contrast.show()
      hbox.pack_start(self.image_contrast, False, False, 0)
      self.image_contrast.connect('value_changed', self.set_image_contrast)

      if self.contrast_button_toggle == True:
        self.image_contrast.set_sensitive(True)
      else:
        self.image_contrast.set_sensitive(False)

      dialog.vbox.pack_start(hbox, False, False, 0)

      # image sharpness
      hbox = gtk.HBox(False, 0)
      hbox.set_border_width(5)

      self.sharpness_button = gtk.CheckButton("Adjust sharpness: ")
      self.sharpness_button.connect("toggled", self.toggle_image_sharpness)
      self.sharpness_button.set_tooltip_text("The factor -2.0 gives a blurred image, 0.0 gives the original image, and a factor of 2.0 gives a sharpened image.")
      if self.sharpness_button_toggle == True:
        self.sharpness_button.set_active(True)
      else:
        self.sharpness_button.set_active(False)
      hbox.pack_start(self.sharpness_button, False, False, 0)

      sharpness_adj = gtk.Adjustment(1.0, -2, 2, 0.1, 0.5, 0.0)
      self.image_sharpness = gtk.SpinButton(adjustment=sharpness_adj, climb_rate=0.1, digits=1)
      self.image_sharpness.set_numeric(True)
      self.image_sharpness.set_value(self.image_sharpness_value)
      self.image_sharpness.show()
      hbox.pack_start(self.image_sharpness, False, False, 0)
      self.image_sharpness.connect('value_changed', self.set_image_sharpness)

      if self.sharpness_button_toggle == True:
        self.image_sharpness.set_sensitive(True)
      else:
        self.image_sharpness.set_sensitive(False)

      dialog.vbox.pack_start(hbox, False, False, 0)

      # image saturation
      hbox = gtk.HBox(False, 0)
      hbox.set_border_width(5)

      self.saturation_button = gtk.CheckButton("Adjust saturation: ")
      self.saturation_button.connect("toggled", self.toggle_image_saturation)
      self.saturation_button.set_tooltip_text("The factor -1.0 gives a black and white image, 0.0 gives the original image, and a factor of 1.0 gives a saturated image.")
      if self.saturation_button_toggle == True:
        self.saturation_button.set_active(True)
      else:
        self.saturation_button.set_active(False)
      hbox.pack_start(self.saturation_button, False, False, 0)

      saturation_adj = gtk.Adjustment(1.0, -1, 1, 0.1, 0.5, 0.0)
      self.image_saturation = gtk.SpinButton(adjustment=saturation_adj, climb_rate=0.1, digits=1)
      self.image_saturation.set_numeric(True)
      self.image_saturation.set_value(self.image_saturation_value)
      self.image_saturation.show()
      hbox.pack_start(self.image_saturation, False, False, 0)
      self.image_saturation.connect('value_changed', self.set_image_saturation)

      if self.saturation_button_toggle == True:
        self.image_saturation.set_sensitive(True)
      else:
        self.image_saturation.set_sensitive(False)

      dialog.vbox.pack_start(hbox, False, False, 0)

      # show it
      dialog.show_all()
      dialog.run()
      dialog.destroy()

      if self.acbf_document.valid:
        self.display_page(True, None)
      return

    def toggle_image_brightness(self, widget):
        if widget.get_active():
          self.image_brightness.set_sensitive(True)
          self.brightness_button_toggle = True
        else:
          self.image_brightness.set_sensitive(False)
          self.brightness_button_toggle = False
        return True

    def toggle_image_contrast(self, widget):
        if widget.get_active():
          self.image_contrast.set_sensitive(True)
          self.contrast_button_toggle = True
        else:
          self.image_contrast.set_sensitive(False)
          self.contrast_button_toggle = False
        return True

    def toggle_image_sharpness(self, widget):
        if widget.get_active():
          self.image_sharpness.set_sensitive(True)
          self.sharpness_button_toggle = True
        else:
          self.image_sharpness.set_sensitive(False)
          self.sharpness_button_toggle = False
        return True

    def toggle_image_saturation(self, widget):
        if widget.get_active():
          self.image_saturation.set_sensitive(True)
          self.saturation_button_toggle = True
        else:
          self.image_saturation.set_sensitive(False)
          self.saturation_button_toggle = False
        return True

    def set_image_brightness(self, widget):
        self.image_brightness_value = widget.get_value()

    def set_image_contrast(self, widget):
        self.image_contrast_value = widget.get_value()

    def set_image_sharpness(self, widget):
        self.image_sharpness_value = widget.get_value()

    def set_image_saturation(self, widget):
        self.image_saturation_value = widget.get_value()

    def reset_enhancement_values(self, *args):
        self.image_brightness_value = 0
        self.image_contrast_value = 0
        self.image_sharpness_value = 0
        self.image_saturation_value = 0
        self.brightness_button_toggle = False
        self.contrast_button_toggle = False
        self.sharpness_button_toggle = False
        self.saturation_button_toggle = False

    def open_library(self, *args):
      self.history.set_book_details(self.original_filename, self.page_number, self.frame_number, self.zoom_level, self.toolbar.language.get_active())
      self.history.save_history()
      filename_before = self.filename
      self.library_dialog = library.LibraryDialog(self)
      self.loading_page_icon.show()
      while gtk.events_pending():
        gtk.main_iteration()

      prepared_file = fileprepare.FilePrepare(self, self.filename, self.tempdir, True)
      self.filename = prepared_file.filename
      if filename_before != self.filename:
        self.acbf_document = acbfdocument.ACBFDocument(self, self.filename)
        self.toolbar.update()
        (self.page_number, self.frame_number, self.zoom_level, self.language_layer) = self.history.get_book_details(self.original_filename)
        if self.page_number > self.acbf_document.pages_total:
          self.page_number = 1
        try:
          self.set_title('%s - ACBF Viewer' % unescape(self.acbf_document.book_title[self.acbf_document.languages[self.language_layer][0]]))
        except:
          try:
            self.set_title('%s - ACBF Viewer' % unescape(self.acbf_document.book_title['en']))
          except:
            self.set_title('%s - ACBF Viewer' % unescape(self.acbf_document.book_title[list(self.acbf_document.book_title.items())[0][0]]))


        #set default language layer
        if self.preferences.get_value("default_language") != "0":
          for idx, doc_lang in enumerate(self.acbf_document.languages, start = 0):
            if doc_lang[1] == 'TRUE':
              for list_lang in constants.LANGUAGES:
                if doc_lang[0] == list_lang == constants.LANGUAGES[int(self.preferences.get_value("default_language"))]:
                  self.language_layer = idx

        self.zoom_index = self.zoom_level - 1
        self.comic_page.rotation = self.fit_width_start = 0
        if self.zoom_index == 0:
          self.toolbar.zoom_button.set_stock_id(gtk.STOCK_ZOOM_IN)
        else:
          self.toolbar.zoom_button.set_stock_id(gtk.STOCK_ZOOM_OUT)
        self.comic_page.text_areas = []
        self.reset_enhancement_values()

        self.set_size_request(self.get_allocation().width + 1, self.get_allocation().height)
        if self.language_layer == 0:
          self.toolbar.language.set_active(self.language_layer)
          self.display_page(True, None)
        else:
          self.toolbar.language.set_active(self.language_layer)
        self.drawable_size = (self.layout.get_allocation().width, self.layout.get_allocation().height)
        if self.zoom_level == 3:
          self.zoom_to_frame(self.frame_number, move=True)

        self.set_size_request(self.get_allocation().width - 1, self.get_allocation().height)

      self.loading_page_icon.hide()

      while gtk.events_pending():
        gtk.main_iteration()
      
      return True


    def show_about_window(self, *args):
      dialog = gtk.Dialog('About', self, gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT,
                          (gtk.STOCK_CLOSE, gtk.ResponseType.CLOSE))
      dialog.set_resizable(False)
      dialog.set_border_width(8)

      hbox = gtk.HBox(False, 10)

      # logo
      pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(os.path.join(constants.ICON_PATH, 'acbfv.png'), 64, 64)
      icon = gtk.Image()
      icon.set_from_pixbuf(pixbuf)
      hbox.pack_start(icon, True, True, 0)

      # labels
      label = gtk.Label()
      label.set_markup('<big><big><b><span foreground="#333333" style="italic">ACBF</span>' +
                       '<span foreground="#ee3300" style="oblique"> Viewer</span></b></big></big>\n' +
                      _('Version: ') + constants.VERSION)
      hbox.pack_start(label, True, True, 0)
      dialog.vbox.pack_start(hbox, True, True, 0)

      hbox = gtk.HBox(False, 10)
      info = gtk.Label()
      info.set_markup(_('\n<span>ACBF Viewer is a comic book viewer for comic books in ACBF, CBZ and ACV formats.') + '\n' +
                      _('ACBF Viewer is licensed under the GNU General Public License.') + '\n\n' +
                       '<small>Copyright 2011-2018 Robert Kubik\n' +
                       'https://launchpad.net/acbf\n' +
                       'http://acbf.wikia.com</small></span>')
      label.set_line_wrap(True)
      info.set_justify(gtk.Justification.CENTER)
      hbox.pack_start(info, True, True, 0)
      dialog.vbox.pack_start(hbox, True, True, 0)

      # show it
      dialog.show_all()
      dialog.run()
      dialog.destroy()
      return

    def set_geometry_hints_max(self, window, min_height, min_width, max_height, max_width):
        geometry = Gdk.Geometry()
        geometry.min_height = min_height
        geometry.min_width = min_width
        geometry.max_height = max_height
        geometry.max_width = max_width
        if max_height > 0:
          hints = Gdk.WindowHints.USER_POS | Gdk.WindowHints.MAX_SIZE | Gdk.WindowHints.USER_SIZE
        else:
          hints = Gdk.WindowHints.USER_POS | Gdk.WindowHints.BASE_SIZE | Gdk.WindowHints.USER_SIZE
        window.set_geometry_hints(window, geometry, hints)

    def show_metadata(self, *args):
      dialog = gtk.Dialog('Comic Book Metadata', self, gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT,
                          (gtk.STOCK_CLOSE, gtk.ResponseType.CLOSE))
      dialog.set_default_size(640, 350)
      self.set_geometry_hints_max(window=dialog, min_height=300, min_width=635, max_height=0, max_width=800)
      dialog.set_border_width(8)

      hbox = gtk.HBox(False, 10)

      # coverpage
      coverpage = gtk.Image()
      coverpage.set_from_pixbuf(comicpage.pil_to_pixbuf(self.acbf_document.cover_thumb, '#000'))
      coverpage.set_alignment(0, 0.5)
      hbox.pack_start(coverpage, True, True, 0)

      notebook = gtk.Notebook()
      hbox.pack_start(notebook, False, False, 0)
      notebook.set_border_width(3)

      # book-info
      scrolled = gtk.ScrolledWindow()
      scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
      tab = gtk.VBox(False, 0)
      tab.set_border_width(5)
      scrolled.add_with_viewport(tab)

      label = gtk.Label()

      try:
        label.set_markup('<b>Title</b>: ' + self.acbf_document.book_title[self.acbf_document.languages[self.language_layer][0]])
      except:
        try:
          label.set_markup('<b>Title</b>: ' + self.acbf_document.book_title['en'])
        except:
          label.set_markup('<b>Title</b>: ' + self.acbf_document.book_title[list(self.acbf_document.book_title.items())[0][0]])

      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>Author(s)</b>: ' + self.acbf_document.authors)
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      sequences = '<b>Series</b>: '
      for sequence in self.acbf_document.sequences:
        sequences = sequences + sequence[0] + ' (' + sequence[1] + '), '
      if len(sequences) > 16:
        sequences = sequences[:-2]
      label.set_markup(sequences)
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>Genre(s)</b>: ' + self.acbf_document.genres)
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>Characters</b>: ' + self.acbf_document.characters)
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      try:
        label.set_markup('<b>Annotation</b>: ' + self.acbf_document.annotation[self.acbf_document.languages[self.language_layer][0]])
      except:
        try:
          label.set_markup('<b>Annotation</b>: ' + self.acbf_document.annotation['en'])
        except:
          label.set_markup('<b>Annotation</b>: ')
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>Keywords</b>: ' + self.acbf_document.keywords)
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      languages = '<b>Languages</b>: '
      for language in self.acbf_document.languages:
        if language[1] == 'FALSE':
          languages = languages + language[0] + '(no text layer), '
        else:
          languages = languages + language[0] + ', '
      languages = languages[:-2]
      label.set_markup(languages)
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>Database Reference</b>: ' + self.acbf_document.databaseref)
      tab.pack_start(label, False, True, 0)


      for label in tab.get_children():
        label.set_alignment(0, 0)
        label.set_line_wrap(True)
        label.set_selectable(True)

      notebook.insert_page(scrolled, gtk.Label('Book-Info'), -1)

      # publish-info
      scrolled = gtk.ScrolledWindow()
      scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
      tab = gtk.VBox(False, 0)
      tab.set_border_width(5)
      scrolled.add_with_viewport(tab)
      label = gtk.Label()
      label.set_markup('<b>Publisher</b>: ' + self.acbf_document.publisher)
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>Publish Date</b>: ' + self.acbf_document.publish_date)
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>City</b>: ' + self.acbf_document.city)
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>ISBN</b>: ' + self.acbf_document.isbn)
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>License</b>: ' + self.acbf_document.license)
      tab.pack_start(label, False, True, 0)

      for label in tab.get_children():
        label.set_alignment(0, 0)
        label.set_line_wrap(True)
        label.set_selectable(True)

      notebook.insert_page(scrolled, gtk.Label('Publish-Info'), -1)

      # document-info
      scrolled = gtk.ScrolledWindow()
      scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
      tab = gtk.VBox(False, 0)
      tab.set_border_width(5)
      scrolled.add_with_viewport(tab)
      label = gtk.Label()
      label.set_markup('<b>Author(s)</b>: ' + self.acbf_document.doc_authors)
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>Creation Date</b>: ' + self.acbf_document.creation_date)
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>Source</b>: ' + self.acbf_document.source)
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>ID</b>: ' + self.acbf_document.id)
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>Version</b>: ' + self.acbf_document.version)
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>History</b>: ' + self.acbf_document.history)
      tab.pack_start(label, False, True, 0)

      for label in tab.get_children():
        label.set_alignment(0, 0)
        label.set_line_wrap(True)
        label.set_selectable(True)

      notebook.insert_page(scrolled, gtk.Label('Document-Info'), -1)

      # technical-info
      scrolled = gtk.ScrolledWindow()
      scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
      tab = gtk.VBox(False, 0)
      tab.set_border_width(5)
      scrolled.add_with_viewport(tab)
      label = gtk.Label()
      label.set_markup('<b>File Name</b>: ' + escape(os.path.basename(self.original_filename)))
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>Path</b>: ' + escape(os.path.dirname(self.original_filename)))
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>ACBF file</b>: ' + escape(os.path.basename(self.filename)))
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>File Size</b>: ' + str(round(float(os.path.getsize(self.original_filename))/1024/1024, 2)) + " MB")
      tab.pack_start(label, False, True, 0)

      label = gtk.Label()
      label.set_markup('<b>Number of pages</b>: ' + str(self.acbf_document.pages_total) + " + cover page")
      tab.pack_start(label, False, True, 0)

      for label in tab.get_children():
        label.set_alignment(0, 0)
        label.set_line_wrap(True)
        label.set_selectable(True)

      notebook.insert_page(scrolled, gtk.Label('Tech-Info'), -1)

      # show it
      dialog.vbox.pack_start(hbox, True, True, 0)
      dialog.show_all()
      dialog.run()
      dialog.destroy()
      return

    def show_help(self, *args):
      dialog = gtk.Dialog('Help', self, gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT, (gtk.STOCK_CLOSE, gtk.ResponseType.CLOSE))
      #dialog.set_geometry_hints(min_height=230)
      dialog.set_resizable(False)
      dialog.set_border_width(8)

      #Shortcuts
      hbox = gtk.HBox(False, 10)
      label = gtk.Label()
      label.set_markup('<b>Shortcuts</b>')
      hbox.pack_start(label, False, False, 0)
      dialog.vbox.pack_start(hbox, False, False, 10)

      # left side
      main_hbox = gtk.HBox(False, 3)
      left_vbox = gtk.VBox(False, 3)

      hbox = gtk.HBox(False, 3)
      button = gtk.ToolButton()
      button.set_stock_id(gtk.STOCK_OPEN)
      hbox.pack_start(button, False, False, 3)
      label = gtk.Label()
      label.set_markup('Open a File (CTRL + O)')
      hbox.pack_start(label, False, False, 3)
      left_vbox.pack_start(hbox, False, False, 0)

      hbox = gtk.HBox(False, 3)
      button = gtk.ToolButton()
      button.set_stock_id(gtk.STOCK_GOTO_FIRST)
      hbox.pack_start(button, False, False, 3)
      label = gtk.Label()
      label.set_markup('Go to First Page (HOME)')
      hbox.pack_start(label, False, False, 3)
      left_vbox.pack_start(hbox, False, False, 0)

      hbox = gtk.HBox(False, 3)
      button = gtk.ToolButton()
      button.set_stock_id(gtk.STOCK_GO_BACK)
      hbox.pack_start(button, False, False, 3)
      label = gtk.Label()
      label.set_markup('Go to Previous Page (LEFT or UP)')
      hbox.pack_start(label, False, False, 3)
      left_vbox.pack_start(hbox, False, False, 0)

      hbox = gtk.HBox(False, 3)
      button = gtk.ToolButton()
      button.set_stock_id(gtk.STOCK_ZOOM_IN)
      hbox.pack_start(button, False, False, 3)
      label = gtk.Label()
      label.set_markup('Zoom In (+)')
      hbox.pack_start(label, False, False, 3)
      left_vbox.pack_start(hbox, False, False, 0)

      hbox = gtk.HBox(False, 3)
      button = gtk.ToolButton()
      button.set_stock_id(gtk.STOCK_FULLSCREEN)
      hbox.pack_start(button, False, False, 3)
      label = gtk.Label()
      label.set_markup('Switch to Fullscreen (F)')
      hbox.pack_start(label, False, False, 3)
      left_vbox.pack_start(hbox, False, False, 0)

      main_hbox.pack_start(left_vbox, False, False, 10)

      # right side
      right_vbox = gtk.VBox(False, 3)

      hbox = gtk.HBox(False, 3)
      button = gtk.ToolButton()
      button.set_stock_id(gtk.STOCK_FIND)
      hbox.pack_start(button, False, False, 3)
      label = gtk.Label()
      label.set_markup('Open Library (F5)')
      hbox.pack_start(label, False, False, 3)
      right_vbox.pack_start(hbox, False, False, 0)

      hbox = gtk.HBox(False, 3)
      button = gtk.ToolButton()
      button.set_stock_id(gtk.STOCK_GOTO_LAST)
      hbox.pack_start(button, False, False, 3)
      label = gtk.Label()
      label.set_markup('Go to Last Page (END)')
      hbox.pack_start(label, False, False, 3)
      right_vbox.pack_start(hbox, False, False, 0)

      hbox = gtk.HBox(False, 3)
      button = gtk.ToolButton()
      button.set_stock_id(gtk.STOCK_GO_FORWARD)
      hbox.pack_start(button, False, False, 3)
      label = gtk.Label()
      label.set_markup('Go to Next Page (RIGHT or DOWN)')
      hbox.pack_start(label, False, False, 3)
      right_vbox.pack_start(hbox, False, False, 0)

      hbox = gtk.HBox(False, 3)
      button = gtk.ToolButton()
      button.set_stock_id(gtk.STOCK_ZOOM_OUT)
      hbox.pack_start(button, False, False, 3)
      label = gtk.Label()
      label.set_markup('Zoom Out (-)')
      hbox.pack_start(label, False, False, 3)
      right_vbox.pack_start(hbox, False, False, 0)

      main_hbox.pack_start(right_vbox, False, False, 10)

      dialog.vbox.pack_start(main_hbox, False, False, 0)

      dialog.get_action_area().get_children()[0].grab_focus()

      # show it
      dialog.show_all()
      dialog.run()
      if dialog != None:
        dialog.destroy()

      return

    def show_contents(self, *args):
      self.contents_dialog = gtk.Dialog('Table of Contents', self, gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT, (gtk.STOCK_CLOSE, gtk.ResponseType.CLOSE))
      #self.contents_dialog.set_geometry_hints(min_height=230)
      self.contents_dialog.set_resizable(False)
      self.contents_dialog.set_border_width(8)

      hbox = gtk.HBox(False, 10)

      # coverpage
      coverpage = gtk.Image()
      coverpage.set_from_pixbuf(comicpage.pil_to_pixbuf(self.acbf_document.cover_thumb, '#000'))
      coverpage.set_alignment(0, 0)
      hbox.pack_start(coverpage, True, True, 0)

      # book-info
      scrolled = gtk.ScrolledWindow()
      scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
      tab = gtk.VBox(False, 0)
      tab.set_border_width(5)
      scrolled.add_with_viewport(tab)

      # get max length of chapters
      max_length = 0
      for chapter in self.acbf_document.contents_table[self.toolbar.language.get_active()]:
        if len(chapter[0]) > max_length:
          max_length = len(chapter[0])

      # draw contents
      label = gtk.Label()
      label.set_markup('<big><b>Table of Contents</b></big>')
      tab.pack_start(label, False, True, 0)

      for chapter in self.acbf_document.contents_table[self.toolbar.language.get_active()]:
        chapter_padded = chapter[0] + ' '
        chapter_padded = chapter_padded.ljust(max_length + 3, '.').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        label = gtk.Label()
        label.set_markup('<a href="' + chapter[1] + '"><span font_desc="Mono" underline="none">' + chapter_padded + ' ' + chapter[1].rjust(2, ' ') + '</span></a>')
        label.connect('activate-link', self.goto_page)
        tab.pack_start(label, False, True, 0)

      for label in tab.get_children():
        label.set_alignment(0, 0)

      hbox.pack_start(scrolled, False, False, 0)

      # show it
      self.contents_dialog.vbox.pack_start(hbox, True, True, 0)
      self.contents_dialog.show_all()
      self.contents_dialog.run()
      if self.contents_dialog != None:
        self.contents_dialog.destroy()

      return

    def zoom_to_frame(self, frame_number, move=False):
      if self.comic_page.frames_total == 0:
        return
      self.is_rendering = True
      #print ('Current frame: ', frame_number - 1)
      window_width = self.drawable_size[0]
      window_height = self.drawable_size[1]
      #print ('Window size: ', window_width, window_height)

      frame_span = get_frame_span(self.acbf_document.load_page_frames(self.page_number)[frame_number - 1][0])
      frame_width = frame_span[2] - frame_span[0]
      frame_height = frame_span[3] - frame_span[1]
      #print ('Frame size: ', frame_width, frame_height)

      horizontal_scale = float(window_width / frame_width)
      vertical_scale = float(window_height / frame_height)
      min_scale = min((horizontal_scale, vertical_scale))

      scaled_frame_width = frame_width * min_scale
      scaled_frame_height = frame_height * min_scale
      new_x = (frame_span[0] * min_scale) - int((window_width - scaled_frame_width) / 2) + 1000
      new_y = (frame_span[1] * min_scale) - int((window_height - scaled_frame_height) / 2) + 1000

      if move or self.preferences.get_value("animation") == "False":
        new_image_width = int(self.original_pixbuf.get_width() * min_scale)
        new_image_height = int(self.original_pixbuf.get_height() * min_scale)
        self.pixbuf = self.original_pixbuf.scale_simple(new_image_width, new_image_height, GdkPixbuf.InterpType.NEAREST)
        self.image_width = self.pixbuf.get_width()
        self.image_height = self.pixbuf.get_height()
        self.comic_page_box.set_from_pixbuf(self.pixbuf)
        self.fixed.set_size_request(self.image_width + 2000, self.image_height + 2000)
        self.bg_image.set_size_request(self.fixed.get_size_request()[0], self.fixed.get_size_request()[1])
        self.current_x = new_x
        self.current_y = new_y
        self.scrolled.get_hadjustment().set_value(self.current_x)
        self.scrolled.get_vadjustment().set_value(self.current_y)
        limit = 0
        while self.current_x != self.scrolled.get_hadjustment().get_value() and limit < 1000:
          limit = limit + 1
          self.scrolled.get_hadjustment().set_value(self.current_x)
          self.scrolled.get_vadjustment().set_value(self.current_y)
          while gtk.events_pending():
            gtk.main_iteration()
                                                                          
      else:
        self.comic_page_box.set_from_pixbuf(self.pixbuf)
        self.fixed.set_size_request(self.pixbuf.get_width() + 2000, self.pixbuf.get_height() + 2000)
        self.bg_image.set_size_request(self.fixed.get_size_request()[0], self.fixed.get_size_request()[1])
        self.scrolled.get_hadjustment().set_value(self.current_x)
        self.scrolled.get_vadjustment().set_value(self.current_y)
        self.animate_to(min_scale, new_x, new_y)
      self.is_rendering = False

      return True
      
    def animate_to(self, min_scale, new_x, new_y):
      animation_steps = 25
      new_image_width = int(self.original_pixbuf.get_width() * min_scale)
      new_image_height = int(self.original_pixbuf.get_height() * min_scale)
      #print ('Animate to:', min_scale, new_image_width, new_image_height, new_x, new_y)

      image_width_step = (new_image_width - self.image_width) / animation_steps
      image_height_step = (new_image_height - self.image_height) / animation_steps
      #print ('Image step:', image_width_step, image_height_step)

      current_image_width = self.image_width
      current_image_height = self.image_height

      #print ('Current position', self.current_x, self.current_y, self.scrolled.get_hadjustment().get_value(), self.scrolled.get_vadjustment().get_value())
      #print ('Current image size', current_image_width, current_image_height)

      x_step = (self.current_x - new_x) / animation_steps
      y_step = (self.current_y - new_y) / animation_steps
      #print ('Move step:', x_step, y_step)

      for animation_frame in range(1, animation_steps):
        # scale_image
        current_image_width = int(current_image_width + image_width_step)
        current_image_height = int(current_image_height + image_height_step)
        #print (current_image_width, current_image_height)

        if animation_frame%2 == 1: # every odd step gets image resized
          t = threading.Thread(target=self.scale_image, args = (current_image_width, current_image_height))
          t.daemon = True
          t.start()
        
        # move image
        self.current_x = self.current_x - x_step
        self.current_x = min(self.current_x, self.scrolled.get_hadjustment().get_upper())
        self.current_x = max(self.current_x, 0)
        self.current_y = self.current_y - y_step
        self.current_y = min(self.current_y, self.scrolled.get_vadjustment().get_upper())
        self.current_y = max(self.current_y, 0)

        self.scrolled.get_hadjustment().set_value(self.current_x)
        self.scrolled.get_vadjustment().set_value(self.current_y)

        if animation_frame%2 == 0: # every even step gets image loaded
          while t.is_alive():
            #print ('thread')
            sleep(0.01)
          self.comic_page_box.set_from_pixbuf(self.new_image)

        slp = float(self.preferences.get_value("animation_delay"))/500
        sleep(slp)

        while gtk.events_pending():
          gtk.main_iteration()

      self.pixbuf = self.original_pixbuf.scale_simple(new_image_width, new_image_height, GdkPixbuf.InterpType.NEAREST)
      self.image_width = self.pixbuf.get_width()
      self.image_height = self.pixbuf.get_height()

      # final alignement 
      self.comic_page_box.set_from_pixbuf(self.pixbuf)
      self.fixed.set_size_request(self.pixbuf.get_width() + 2000, self.pixbuf.get_height() + 2000)
      self.current_x = new_x
      self.current_y = new_y
      self.scrolled.get_hadjustment().set_value(self.current_x)
      self.scrolled.get_vadjustment().set_value(self.current_y)

      #print ('End animation position', self.current_x, self.current_y)
      #print ('End image size', self.image_width, self.image_height)

    def scale_image(self, current_image_width, current_image_height):
      self.new_image = self.pixbuf.scale_simple(current_image_width, current_image_height, GdkPixbuf.InterpType.NEAREST)

    def goto_page(self, label, uri):
      if self.contents_dialog != None:
        self.contents_dialog.destroy()
      while gtk.events_pending():
        gtk.main_iteration()
      self.page_number = int(uri)
      self.frame_number = 1
      self.display_page(True, align='upper')
      return True

    def rotate_image(self, *args):
      if self.comic_page.rotation == 270:
        self.comic_page.rotation = 0
      else:
        self.comic_page.rotation = self.comic_page.rotation + 90
      if self.zoom_level == 2:
        if self.comic_page.rotation == 180:
          image_height = int(float(self.comic_page.PILBackgroundImageProcessed.size[1])/(float(self.comic_page.PILBackgroundImageProcessed.size[0])/float(self.drawable_size[0])))
          self.fit_width_start = 0 - image_height + self.drawable_size[1]
        elif self.comic_page.rotation == 270:
          image_height = int(float(self.comic_page.PILBackgroundImageProcessed.size[1])/(float(self.comic_page.PILBackgroundImageProcessed.size[0])/float(self.drawable_size[1])))
          self.fit_width_start = 0 - image_height + self.drawable_size[0]
        else:
          self.fit_width_start = 0
        self.comic_page.updated = False
      self.display_page(False, align='upper')
      return

    def zoom_page(self, *args):
      self.zoom_index = self.zoom_index + 1
      if self.zoom_index == 1 and self.comic_page.frames_total == 0:
        self.zoom_index = 3
      if self.zoom_index == 2 and self.comic_page.frames_total == 0:
        self.zoom_index = 0
      if self.zoom_index > 3:
        self.zoom_index = 0
      self.zoom_level = self.zoom_list[self.zoom_index]
      if self.zoom_level == 2:
        if self.comic_page.rotation == 180:
          image_height = int(float(self.comic_page.PILBackgroundImageProcessed.size[1])/(float(self.comic_page.PILBackgroundImageProcessed.size[0])/float(self.drawable_size[0])))
          self.fit_width_start = 0 - image_height + self.drawable_size[1]
        elif self.comic_page.rotation == 270:
          image_height = int(float(self.comic_page.PILBackgroundImageProcessed.size[1])/(float(self.comic_page.PILBackgroundImageProcessed.size[0])/float(self.drawable_size[1])))
          self.fit_width_start = 0 - image_height + self.drawable_size[0]
        else:
          self.fit_width_start = 0
        self.comic_page.updated = False
      self.display_page(False, align='upper')
      if self.zoom_level == 3 and self.comic_page.frames_total > 0:
        self.zoom_to_frame(self.frame_number, move=True)
      return

    def show_fullscreen(self, *args):
      if self.isFullscreen:
        self.unfullscreen()
        self.isFullscreen = False
      else:
        self.fullscreen()
        self.isFullscreen = True
      return

    def goto_first_page(self, *args):
      if self.page_number != 1:
        self.page_number = 1
        if self.zoom_level == 2:
          if self.comic_page.rotation == 180:
            image_height = int(float(self.comic_page.PILBackgroundImageProcessed.size[1])/(float(self.comic_page.PILBackgroundImageProcessed.size[0])/float(self.drawable_size[0])))
            self.fit_width_start = self.drawable_size[1] - image_height
          elif self.comic_page.rotation == 270:
            image_height = int(float(self.comic_page.PILBackgroundImageProcessed.size[1])/(float(self.comic_page.PILBackgroundImageProcessed.size[0])/float(self.drawable_size[1])))
            self.fit_width_start = 0 - image_height + self.drawable_size[0]
          else:
            self.fit_width_start = 0
        elif self.zoom_level == 3:
          self.frame_number = 1
        self.display_page(True, align='upper');
        if self.zoom_level == 3 and self.comic_page.frames_total > 0:
          self.zoom_to_frame(self.frame_number, move=True)
      return

    def goto_prev_page(self, *args):
      update = False
      if self.zoom_level == 3:
        if self.frame_number > 1:
          self.frame_number = self.frame_number - 1
          self.display_page(False, None)
          self.zoom_to_frame(self.frame_number)
        else:
          if self.page_number > 1:
            self.page_number = self.page_number - 1
            self.frame_number = len(self.acbf_document.load_page_frames(self.page_number))
            self.display_page(True, None)
            self.zoom_to_frame(self.frame_number, move=True)
      else:
        if self.page_number > 1:
          self.page_number = self.page_number - 1
          self.frame_number = 1
          self.display_page(True, align='lower')
      return True

    def goto_next_page(self, *args):
      update = False
      if self.zoom_level == 3:
        if self.frame_number < self.comic_page.frames_total:
          self.frame_number = self.frame_number + 1
          self.display_page(False, None)
          self.zoom_to_frame(self.frame_number)
        else: # going from page with no frames
          if self.page_number < self.acbf_document.pages_total + 1:
            self.page_number = self.page_number + 1
            self.frame_number = 1
            self.fit_width_start = 0
            self.display_page(True, None)
            self.zoom_to_frame(self.frame_number, move=True)
      else:
        if self.page_number < self.acbf_document.pages_total + 1:
          self.page_number = self.page_number + 1
          self.frame_number = 1
          self.fit_width_start = 0
          self.display_page(True, align='upper')
      return

    def goto_last_page(self, *args):
      update = False
      if self.zoom_level == 3:
        self.page_number = self.acbf_document.pages_total + 1
        self.frame_number = len(self.acbf_document.load_page_frames(self.page_number))
        update = True
      elif self.zoom_level == 2:
        self.page_number = self.acbf_document.pages_total + 1
        if self.comic_page.rotation == 180:
          image_height = int(float(self.comic_page.PILBackgroundImageProcessed.size[1])/(float(self.comic_page.PILBackgroundImageProcessed.size[0])/float(self.drawable_size[0])))
          self.fit_width_start = self.drawable_size[1] - image_height
        elif self.comic_page.rotation == 270:
          image_height = int(float(self.comic_page.PILBackgroundImageProcessed.size[1])/(float(self.comic_page.PILBackgroundImageProcessed.size[0])/float(self.drawable_size[1])))
          self.fit_width_start = 0 - image_height + self.drawable_size[0]
        else:
          self.fit_width_start = 0
        update = True
      else:
        if self.page_number < self.acbf_document.pages_total + 1:
          self.zoom_level == 1
          self.page_number = self.acbf_document.pages_total + 1
          self.frame_number = 1
          self.fit_width_start = 0
          update = True

      self.display_page(update, None)
      if self.zoom_level == 3 and self.comic_page.frames_total > 0:
        self.zoom_to_frame(self.frame_number, move=True)

      return

    def set_page_from_entry(self, *args):
      try:
        entry_value = int(self.toolbar.entry.get_text())
        if (entry_value > 0 and entry_value < self.acbf_document.pages_total + 2 and entry_value != self.page_number):
          self.page_number = int(self.toolbar.entry.get_text())
          self.frame_number = 1
          self.display_page(True, align='upper')
          if self.zoom_level == 3 and self.comic_page.frames_total > 0:
            self.zoom_to_frame(self.frame_number, move=True)
      except:
        self.toolbar.entry.set_text(str(self.page_number))

    def change_language(self, *args):
      self.display_page(True, None)
      self.language_layer = self.toolbar.language.get_active()
      if len(self.acbf_document.contents_table[self.toolbar.language.get_active()]) == 0:
        self.toolbar.index_button.set_sensitive(False)
      else:
        self.toolbar.index_button.set_sensitive(True)
      if self.zoom_level == 3 and self.comic_page.frames_total > 0:
            self.zoom_to_frame(self.frame_number, move=True)
      return

    # events handling
    def configure_window(self, widget, event):
      #print(Gdk.Window.get_frame_extents(gtk.Widget.get_window(widget)).width, Gdk.Window.get_frame_extents(gtk.Widget.get_window(widget)).height)
      #print(event.width, event.height)
      #print(self.layout.get_allocation().width, self.layout.get_allocation().height)
      if self.is_rendering:
        return
      if (bool(self.drawable_size != (self.layout.get_allocation().width, self.layout.get_allocation().height)) and
          bool(self.drawable_size != (Gdk.Window.get_frame_extents(gtk.Widget.get_window(widget)).width, Gdk.Window.get_frame_extents(gtk.Widget.get_window(widget)).height))):
        if (self.isFullscreen and self.preferences.get_value("fullscreen_toolbar_hiding") == "True"):
          self.drawable_size = (Gdk.Window.get_frame_extents(gtk.Widget.get_window(widget)).width, Gdk.Window.get_frame_extents(gtk.Widget.get_window(widget)).height)
        elif (self.isFullscreen and self.preferences.get_value("fullscreen_toolbar_hiding") != "True"):
          self.drawable_size = (Gdk.Window.get_frame_extents(gtk.Widget.get_window(widget)).width, self.layout.get_allocation().height)
        else:
          self.drawable_size = (self.layout.get_allocation().width, self.layout.get_allocation().height)

        self.comic_page.updated = False
        self.display_page(False, None)
        if self.zoom_level == 3:
          self.zoom_to_frame(self.frame_number, move=True)
      return

    def scroll_scrolled(self, *args):
      #print ('Scrolling')
      if self.zoom_level == 2:
        self.scrolled.get_vadjustment().set_value(self.scroll_value)
        self.scrolled.grab_focus()
      return True

    def mouse_scroll(self, button, event):
      value = int(self.scrolled.get_vadjustment().get_value())
      increment = int(self.scrolled.get_vadjustment().get_step_increment()) * 2
      upper = int(self.scrolled.get_vadjustment().get_upper())
      page_size = int(self.scrolled.get_vadjustment().get_page_size())
      #print (upper, self.scrolled.get_vadjustment().get_value(), value)
      if self.is_rendering:
        return True
      if event.direction == Gdk.ScrollDirection.DOWN:
        self.scroll_to_prior_page = False
        if self.zoom_level != 2:
          self.goto_next_page()
        else:
          #print (value, upper, increment, page_size, page_size + value)
          if self.scroll_to_next_page:
            self.scroll_value = upper - page_size
            self.scrolled.get_vadjustment().set_value(self.scroll_value)
            self.goto_next_page()
            self.scroll_to_next_page = False
          elif (page_size + value) >= upper:
            self.scroll_value = upper - page_size
            self.scrolled.get_vadjustment().set_value(self.scroll_value)
            self.scroll_to_next_page = True
          else:
            self.scroll_value = self.scroll_value + increment
            self.scroll_to_next_page = False
            self.scrolled.get_vadjustment().set_value(self.scroll_value)
      elif event.direction == Gdk.ScrollDirection.UP:
        self.scroll_to_next_page = False
        if self.zoom_level != 2:
          self.goto_prev_page()
        else:
          #print (value, 0, increment, page_size + value)
          if self.scroll_to_prior_page:
            #self.scrolled.get_vadjustment().set_value(0)
            self.goto_prev_page()
            self.scroll_to_prior_page = False
          elif value <= 0:
            self.scrolled.get_vadjustment().set_value(0)
            self.scroll_to_prior_page = True
          else:
            self.scroll_value = self.scroll_value - increment
            self.scroll_to_prior_page = False
            self.scrolled.get_vadjustment().set_value(self.scroll_value)
      return True

    def key_pressed(self, widget, event):
      """print dir(gtk.keysyms)"""
      if self.is_rendering:
        return False
      # ALT + key
      if event.state == Gdk.ModifierType.MOD1_MASK:
        if (event.keyval == Gdk.KEY_Page_Down or event.keyval == Gdk.KEY_Page_Up):
          self.show_fullscreen()
      # CTRL + key
      if event.state == Gdk.ModifierType.CONTROL_MASK:
        if event.keyval in (Gdk.KEY_O, Gdk.KEY_o):
          self.open_file()
      else:
      # the rest
        if event.keyval in (Gdk.KEY_F, Gdk.KEY_f):
          self.show_fullscreen()
        elif event.keyval in (Gdk.KEY_R, Gdk.KEY_r):
          self.rotate_image()
        elif (event.keyval == Gdk.KEY_Escape and self.isFullscreen):
          self.show_fullscreen()
        elif event.keyval in (Gdk.KEY_Page_Up, Gdk.KEY_Left, Gdk.KEY_Up):
          if self.zoom_level != 2:
            self.goto_prev_page()
          else:
            value = self.scrolled.get_vadjustment().get_value()
            increment = self.scrolled.get_vadjustment().get_step_increment()
            page_size = self.scrolled.get_vadjustment().get_page_size()
            if value <= 0:
              self.goto_prev_page()
            else:
              self.scroll_value = value - increment
              self.scrolled.get_vadjustment().set_value(self.scroll_value)
        elif event.keyval in (Gdk.KEY_Page_Down, Gdk.KEY_Right, Gdk.KEY_Down, Gdk.KEY_space):
          if self.zoom_level != 2:
            self.goto_next_page()
          else:
            value = self.scrolled.get_vadjustment().get_value()
            increment = self.scrolled.get_vadjustment().get_step_increment()
            upper = self.scrolled.get_vadjustment().get_upper()
            page_size = self.scrolled.get_vadjustment().get_page_size()
            if (page_size + value) >= upper:
              self.goto_next_page()
            else:
              self.scroll_value = value + increment
              self.scrolled.get_vadjustment().set_value(self.scroll_value)
        elif event.keyval == Gdk.KEY_Home:
          self.goto_first_page()
        elif event.keyval == Gdk.KEY_End:
          self.goto_last_page()
        elif event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
          self.set_page_from_entry()
        elif event.keyval in (Gdk.KEY_KP_Add, Gdk.KEY_plus, Gdk.KEY_KP_Subtract, Gdk.KEY_minus):
          self.zoom_page()
        elif event.keyval == Gdk.KEY_F1:
          self.show_help()
        elif event.keyval == Gdk.KEY_F5:
          self.open_library()

      #print gtk.gdk.keyval_name(event.keyval)
      return

    def mouse_clicked(self, widget, event):
       if self.is_rendering:
         return False
       # check if clicked on reference
       if self.comic_page.references != [] and self.zoom_level != 3:
         x_resize = int(event.x) - self.comic_page_box.get_allocation().x
         y_resize = int(event.y) - self.comic_page_box.get_allocation().y
         x_ratio = float(float(self.comic_page.PILBackgroundImage.size[0])/self.comic_page_box.get_allocation().width)
         y_ratio = float(float(self.comic_page.PILBackgroundImage.size[1])/self.comic_page_box.get_allocation().height)
         x_original = x_resize * x_ratio
         y_original = y_resize * y_ratio

         for reference in self.comic_page.references:
           if len(reference) == 3:
             if comicpage.point_inside_polygon(int(x_original), int(y_original), reference[2]):
               self.popup_dialog = gtk.Dialog('Reference', self, gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT,
                                              (gtk.STOCK_CLOSE, gtk.ResponseType.CLOSE))
               self.popup_dialog.set_resizable(False)
               self.popup_dialog.set_border_width(8)
               self.popup_dialog.set_decorated(False)

               hbox = gtk.HBox(False, 10)
               label = gtk.Label()
               display_text = reference[1]
               label.set_markup(display_text)
               label.set_alignment(0, 0)
               label.set_line_wrap(True)
               label.set_selectable(True)
               hbox.pack_start(label, True, True, 0)
               self.popup_dialog.vbox.pack_start(hbox, True, True, 0)
               self.popup_dialog.connect("button_press_event", self.destroy_popup_dialog)
               self.popup_dialog.show_all()
               self.popup_dialog.run()
               self.popup_dialog.destroy()
               return

       if self.zoom_level == 2:
         if self.comic_page.rotation == 0:
           if event.y > (self.drawable_size[1]*0.66):
             self.goto_next_page()
           elif event.y < (self.drawable_size[1]*0.33):
             self.goto_prev_page()
         if self.comic_page.rotation == 180:
           if event.y > (self.drawable_size[1]*0.66):
             self.goto_prev_page()
           elif event.y < (self.drawable_size[1]*0.33):
             self.goto_next_page()
         if self.comic_page.rotation == 90:
           if event.x > (self.drawable_size[0]*0.66):
             self.goto_next_page()
           elif event.x < (self.drawable_size[0]*0.33):
             self.goto_prev_page()
         if self.comic_page.rotation == 270:
           if event.x > (self.drawable_size[0]*0.66):
             self.goto_prev_page()
           elif event.x < (self.drawable_size[0]*0.33):
             self.goto_next_page()
       else:
         if self.comic_page.rotation in (0, 90):
           if event.x > (self.drawable_size[0]*0.66):
             self.goto_next_page()
           elif event.x < (self.drawable_size[0]*0.33):
             self.goto_prev_page()
         else:
           if event.x > (self.drawable_size[0]*0.66):
             self.goto_prev_page()
           elif event.x < (self.drawable_size[0]*0.33):
             self.goto_next_page()

       if (event.x < (self.drawable_size[0]*0.66) and
           event.x > (self.drawable_size[0]*0.33) and
           event.y < (self.drawable_size[1]*0.66) and
           event.y > (self.drawable_size[1]*0.33) and
           self.isFullscreen):
         self.show_fullscreen()

    def destroy_popup_dialog(self, *args):
      self.popup_dialog.destroy()
      return

    def display_page(self, update, align):
      self.is_rendering = True
      PixBufImage = self.comic_page_box.get_pixbuf()

      if (self.isFullscreen and self.preferences.get_value("fullscreen_toolbar_hiding") == 'True'):
        self.toolbar.hide()

      if update:
        self.loading_page_alignment.set_size_request(self.drawable_size[0] - 10, self.drawable_size[1] - 10)
        self.progress_bar_alignment.set_size_request(self.drawable_size[0], self.drawable_size[1])
        self.loading_page_icon.show()
        # force loading_page_icon to redraw now
        while gtk.events_pending():
          gtk.main_iteration()
        t = threading.Thread(target=self.comic_page.update)
        t.daemon = True
        t.start()

      # fade out effect
      if self.zoom_level in (1, 2, 3) and self.preferences.get_value("animation") != "False" and self.acbf_document.valid and PixBufImage != None and update:
        for opacity in reversed([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]):
          self.comic_page_box.set_opacity(opacity/10)
          while gtk.events_pending():
            gtk.main_iteration()
          slp = round(float(self.preferences.get_value("animation_delay"))/100, 2)
          sleep(slp)

      if update:
        while t.is_alive():
          sleep(0.01)

      if self.zoom_level != 2 or not self.comic_page.updated:
        # load new image
        if self.zoom_level == 3 and self.comic_page.frames_total == 0:
          PixBufImage, self.PixBufImage_width, self.PixBufImage_height, bg_color = comicpage.get_PixBufImage(self.comic_page, self.drawable_size, 1)
        else:
          PixBufImage, self.PixBufImage_width, self.PixBufImage_height, bg_color = comicpage.get_PixBufImage(self.comic_page, self.drawable_size, self.zoom_level)
        self.original_pixbuf = PixBufImage
        if update:
          self.pixbuf = PixBufImage
        if self.pixbuf != None:
          self.image_width = self.pixbuf.get_width()
          self.image_height = self.pixbuf.get_height()

        self.comic_page_box.set_from_pixbuf(PixBufImage)
        self.fixed.set_size_request(self.PixBufImage_width, self.PixBufImage_height)

      if self.zoom_level == 1 or (self.zoom_level == 3 and self.comic_page.frames_total == 0):
        self.scrolled.set_size_request(self.PixBufImage_width, self.PixBufImage_height)
        self.scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.NEVER)
      else:
        self.scrolled.set_size_request(self.drawable_size[0], self.drawable_size[1])
        self.scrolled.set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)

      # set layout background color
      if (self.zoom_level == 3 and self.comic_page.frames_total > 0):
        self.bg_image.modify_bg(gtk.StateType.NORMAL, Gdk.color_parse(bg_color))
      else:
        self.bg_image.modify_bg(gtk.StateType.NORMAL, None)

      # center image inside the layout
      if self.zoom_level == 1 or (self.zoom_level == 3 and self.comic_page.frames_total == 0):
        self.layout.move(self.scrolled, (self.drawable_size[0] - self.PixBufImage_width)/2, (self.drawable_size[1] - self.PixBufImage_height)/2)
        self.fixed.move(self.comic_page_box, 0, 0)
      elif self.zoom_level == 3:
        self.layout.move(self.scrolled, 0, 0)
        self.fixed.set_size_request(self.PixBufImage_width + 2000, self.PixBufImage_height + 2000)
        self.fixed.move(self.comic_page_box, 1000, 1000)
      else:
        self.layout.move(self.scrolled, 0, 0)
        self.fixed.move(self.comic_page_box, 0, 0)
        self.fixed.set_size_request(self.PixBufImage_width, self.PixBufImage_height)
      self.bg_image.set_size_request(self.fixed.get_size_request()[0], self.fixed.get_size_request()[1])

      # scroll to start/end page
      if self.zoom_level == 2:
        while gtk.events_pending():
          gtk.main_iteration()
        if align == 'lower':
          upper = self.scrolled.get_vadjustment().get_upper()
          page_size = self.scrolled.get_vadjustment().get_page_size()
          self.scroll_value = upper - page_size
          self.scrolled.get_vadjustment().set_value(self.scroll_value)
        else:
          self.scroll_value = 0
          self.scrolled.get_vadjustment().set_value(self.scroll_value)

      # fade in effect
      if self.zoom_level in (1, 2, 3) and self.preferences.get_value("animation") != "False" and self.acbf_document.valid and update:
        if self.zoom_level == 3:
          self.zoom_to_frame(self.frame_number, move=True)
        for opacity in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
          self.comic_page_box.set_opacity(opacity/10)
          while gtk.events_pending():
            gtk.main_iteration()
          slp = round(float(self.preferences.get_value("animation_delay"))/100, 2)
          sleep(slp)

      # update toolbar icons sensitivity
      self.toolbar.entry.set_text(str(self.page_number))
      if self.zoom_index == 0 or (self.zoom_index == 1 and self.comic_page.frames_total > 0):
        self.toolbar.zoom_button.set_stock_id(gtk.STOCK_ZOOM_IN)
      else:
        self.toolbar.zoom_button.set_stock_id(gtk.STOCK_ZOOM_OUT)

      if (self.zoom_level == 3 and self.frame_number == self.comic_page.frames_total and self.page_number == self.acbf_document.pages_total + 1 or
          self.zoom_level == 3 and self.comic_page.frames_total == 0 and self.page_number == self.acbf_document.pages_total + 1 or
          not self.zoom_level == 3 and self.page_number == self.acbf_document.pages_total + 1):
        self.toolbar.last_button.set_sensitive(False)
        self.toolbar.next_button.set_sensitive(False)
      else:
        self.toolbar.last_button.set_sensitive(True)
        self.toolbar.next_button.set_sensitive(True)

      if self.page_number == 1:
        self.toolbar.first_button.set_sensitive(False)
        self.toolbar.prev_button.set_sensitive(False)
      else:
        self.toolbar.first_button.set_sensitive(True)
        self.toolbar.prev_button.set_sensitive(True)

      if not self.acbf_document.valid:
        self.toolbar.zoom_button.set_sensitive(False)
        self.toolbar.rotate_button.set_sensitive(False)
        self.toolbar.full_screen_button.set_sensitive(False)
        self.toolbar.metadata_button.set_sensitive(False)
        self.toolbar.entry.set_sensitive(False)
        self.toolbar.adjustment_button.set_sensitive(False)
      else:
        self.toolbar.zoom_button.set_sensitive(True)
        self.toolbar.rotate_button.set_sensitive(True)
        self.toolbar.full_screen_button.set_sensitive(True)
        self.toolbar.metadata_button.set_sensitive(True)
        self.toolbar.entry.set_sensitive(True)
        self.toolbar.adjustment_button.set_sensitive(True)

      if len(self.acbf_document.contents_table) == 0:
        self.toolbar.index_button.set_sensitive(False)
      elif len(self.acbf_document.contents_table[0]) == 0:
        self.toolbar.index_button.set_sensitive(False)
      else:
        self.toolbar.index_button.set_sensitive(True)

      # show it
      self.show_all()

      if (self.isFullscreen and self.preferences.get_value("fullscreen_toolbar_hiding") == 'True'):
        self.toolbar.hide()
      self.layout.grab_focus()

      if self.preferences.get_value("progress_bar_showing") != 'True':
        self.progress_bar_alignment.hide()
      elif (self.acbf_document.pages_total > 0 and self.preferences.get_value("progress_bar_showing") == 'True'):
        self.progress_bar_alignment.set_size_request(self.drawable_size[0], self.drawable_size[1])
        progress_bar_length = float(self.page_number) / float(self.acbf_document.pages_total + 1) * float(self.layout.get_allocation().width)
        if self.comic_page.frames_total > 0:
          progress_bar_length = progress_bar_length + (float(1) / float(self.acbf_document.pages_total + 1) * float(self.layout.get_allocation().width) / self.comic_page.frames_total * (self.frame_number - 1))

        if progress_bar_length < 1:
          progress_bar_length = 1
        progress_bar_width = int(self.preferences.get_value("progress_bar_width"))
        progress_bar_color = self.preferences.get_value("progress_bar_color")
        if len(progress_bar_color) == 13:
          progress_bar_color = '#' + progress_bar_color[1:3] + progress_bar_color[5:7] + progress_bar_color[9:11]
        ProgressBarImage = comicpage.pil_to_pixbuf(Image.new("RGB", (int(progress_bar_length), progress_bar_width), progress_bar_color), "#000")

        self.progress_bar_icon.set_from_pixbuf(ProgressBarImage)

      self.loading_page_icon.hide()
      self.is_rendering = False

      return True

    def terminate_program(self, *args):
      self.history.set_book_details(self.original_filename, self.page_number, self.frame_number, self.zoom_level, self.toolbar.language.get_active())
      self.history.save_history()

      # clear temp directory
      for root, dirs, files in os.walk(self.tempdir):
        for f in files:
          os.unlink(os.path.join(root, f))
        for d in dirs:
          shutil.rmtree(os.path.join(root, d))
      shutil.rmtree(self.tempdir)

      gtk.main_quit()
      return False

def get_frame_span(frame_coordinates):
    """returns x_min, y_min, x_max, y_max coordinates of a frame"""
    x_min = 100000000
    x_max = -1
    y_min = 100000000
    y_max = -1
    for frame_tuple in frame_coordinates:
      if x_min > frame_tuple[0]:
        x_min = frame_tuple[0]
      if y_min > frame_tuple[1]:
        y_min = frame_tuple[1]
      if x_max < frame_tuple[0]:
        x_max = frame_tuple[0]
      if y_max < frame_tuple[1]:
        y_max = frame_tuple[1]
    return (int(x_min), int(y_min), int(x_max), int(y_max))
