"""library.py - Library Dialog.

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
from gi.repository import Gdk
from gi.repository import GdkPixbuf
import os.path
import lxml.etree as xml
import zipfile
import shutil
from PIL import Image
import io
import base64
from xml.sax.saxutils import escape, unescape
from random import randint
import sqlite3

try:
  from . import constants
  from . import filechooser
  from . import fileprepare
  from . import acbfdocument
  from . import library_info
  from . import preferences
except Exception:
  import constants
  import filechooser
  import fileprepare
  import acbfdocument
  import library_info
  import preferences

class LibraryDialog(gtk.Dialog):
    
    """Library dialog."""
    
    def __init__(self, window):
        self._window = window
        self.library = Library()
        gtk.Dialog.__init__(self, 'Comic Books Library', window, gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT)
        self.set_resizable(True)
        self.set_border_width(8)
        self.set_default_size(900, 600)
        self.set_geometry_hints_max(window=self, min_height=360, min_width=635, max_height=0, max_width=800)
        self.isChanged = False
        self.preferences = preferences.Preferences()

        self.connect('key_press_event', self.key_pressed)
        self.connect('check-resize', self.resize_library)
        self.connect('delete_event', self.close_dialog)
        self.old_window_size = self.get_size()
        self.isResizing = False

        # Default settings
        self.books_per_page = int(self._window.preferences.get_value("library_books_per_page"))
        self.library_layout = int(self._window.preferences.get_value("library_layout"))
        self.books_start_number = 1
        self.filter_title = self.filter_characters = self.filter_authors = ''
        self.filter_license = self.filter_genres = self.filter_languages = self.filter_series = self.filter_rating = self.filter_publisher = self.filter_publishdate = self.filter_read = self.filter_frames = self.filter_im_formats = 0
        self.read = ["Do Not Filter", "True", "False"]
        self.frames_def = ["Do Not Filter", "True", "False"]
        self.populate_filter_lists()
        self.custom_filters = gtk.ComboBoxText()

        # action area
        self.toggle_button_hbox = gtk.HBox(True, 0)
        button = gtk.Button("N")
        button.set_tooltip_text('Normal Layout')
        if self.library_layout == 0:
          button.set_sensitive(False)
        button.connect("clicked", self.change_library_layout, "N")
        self.toggle_button_hbox.pack_start(button, True, True, 0)
        button = gtk.Button("C")
        button.set_tooltip_text('Compact Layout')
        if self.library_layout == 1:
          button.set_sensitive(False)
        button.connect("clicked", self.change_library_layout, "C")
        self.toggle_button_hbox.pack_start(button, True, True, 0)
        button = gtk.Button("L")
        button.set_tooltip_text('List Layout')
        if self.library_layout == 2:
          button.set_sensitive(False)
        button.connect("clicked", self.change_library_layout, "L")
        self.toggle_button_hbox.pack_start(button, True, True, 0)

        self.get_action_area().add(self.toggle_button_hbox)

        self.add_button(gtk.STOCK_CLOSE, gtk.ResponseType.CLOSE)
        self.get_action_area().set_layout(gtk.ButtonBoxStyle.EDGE)
        
        # Toolbar
        self.toolbar = gtk.Toolbar()
        self.toolbar.set_orientation(gtk.Orientation.HORIZONTAL)
        self.toolbar.set_style(gtk.ToolbarStyle.ICONS)
        self.toolbar.set_icon_size(gtk.IconSize.SMALL_TOOLBAR)
        self.toolbar.set_border_width(5)

        tool_button = gtk.ToolButton()
        tool_button.set_stock_id(gtk.STOCK_ADD)
        tool_button.set_tooltip_text('Add Comic Book')
        tool_button.connect("clicked", self.add_book)
        self.toolbar.insert(tool_button, 0)

        tool_button = gtk.ToolButton()
        tool_button.set_stock_id(gtk.STOCK_DIRECTORY)
        tool_button.set_tooltip_text('Add Comic Book Folder')
        tool_button.connect("clicked", self.add_book_folder)
        self.toolbar.insert(tool_button, 1)

        tool_button = gtk.ToolButton()
        tool_button.set_stock_id(gtk.STOCK_SAVE)
        tool_button.set_tooltip_text('Export to CSV file')
        tool_button.connect("clicked", self.export_to_csv)
        self.toolbar.insert(tool_button, 2)

        self.toolbar.insert(gtk.SeparatorToolItem(), 3)

        self.library_info_button = gtk.ToolButton()
        self.library_info_button.set_stock_id(gtk.STOCK_INFO)
        self.library_info_button.set_tooltip_text('Library Info')
        self.library_info_button.connect("clicked", self.show_info)
        self.toolbar.insert(self.library_info_button, 4)

        self.toolbar.insert(gtk.SeparatorToolItem(), 5)

        self.goto_first_button = gtk.ToolButton()
        self.goto_first_button.set_stock_id(gtk.STOCK_GOTO_FIRST)
        self.goto_first_button.connect("clicked", self.goto_first_page)
        self.toolbar.insert(self.goto_first_button, 6)

        self.goto_prev_button = gtk.ToolButton()
        self.goto_prev_button.set_stock_id(gtk.STOCK_GO_BACK)
        self.goto_prev_button.connect("clicked", self.goto_previous_page)
        self.toolbar.insert(self.goto_prev_button, 7)

        self.entry = gtk.Entry()
        self.entry.set_width_chars(7)
        self.entry.set_text('X/X')
        self.entry.set_sensitive(False)
        self.entry.show()
        entry_toolitem = gtk.ToolItem()
        entry_toolitem.add(self.entry)
        self.toolbar.insert(entry_toolitem, 8)

        self.goto_next_button = gtk.ToolButton()
        self.goto_next_button.set_stock_id(gtk.STOCK_GO_FORWARD)
        self.goto_next_button.connect("clicked", self.goto_next_page)
        self.toolbar.insert(self.goto_next_button, 9)

        self.goto_last_button = gtk.ToolButton()
        self.goto_last_button.set_stock_id(gtk.STOCK_GOTO_LAST)
        self.goto_last_button.connect("clicked", self.goto_last_page)
        self.toolbar.insert(self.goto_last_button, 10)

        self.toolbar.insert(gtk.SeparatorToolItem(), 11)

        tool_button = gtk.MenuToolButton(gtk.STOCK_PAGE_SETUP)
        tool_button.set_tooltip_text('Set Filter')
        tool_button.set_arrow_tooltip_text('List of Custom Filters')
        tool_button.connect("clicked", self.set_filter)

        self.filter_menu = gtk.Menu()
        self.load_custom_filters()
        tool_button.set_menu(self.filter_menu)
        self.toolbar.insert(tool_button, 12)

        sort_by_box = gtk.HBox(False, 0)
        sort_by_box.set_border_width(2)
        label = gtk.Label()
        label.set_markup('<b>Sort by:</b>')
        self.sort_by = gtk.ComboBoxText()
        for sort_item in ['Title', 'Series', 'Author(s)', 'Publisher', 'Publish Date', 'Languages', 'Rating']:
          self.sort_by.append_text(sort_item)
        self.sort_by.set_active(int(self._window.preferences.get_value("library_default_sort_order")))
        self.sort_by.connect('changed', self.change_sort_order)
        sort_by_box.pack_start(label, False, False, 3)
        sort_by_box.pack_start(self.sort_by, False, False, 3)
        sort_toolitem = gtk.ToolItem()
        sort_toolitem.add(sort_by_box)
        self.toolbar.insert(sort_toolitem, 13)

        self.toolbar.show()
        self.vbox.pack_start(self.toolbar, False, False, 0)

        # book list window
        self.scrolled = gtk.ScrolledWindow()
        self.vbox.pack_start(self.scrolled, True, True, 0)

        self.book_list = gtk.VBox(False, 5)
        self.scrolled.add_with_viewport(self.book_list)

        # check if all books exist on their path
        if self._window.preferences.get_value("library_cleanup") == "True":
          self.check_books()

        self.library.cursor.execute('SELECT count(*) FROM books')
        self.total_books = self.library.cursor.fetchone()[0]
        
        self.number_of_pages = int(round((self.total_books/float(self.books_per_page)) + 0.49999, 0))
        self.entry.set_width_chars(len(str(self.number_of_pages))*2 + 2)

        self.change_sort_order()
        self.scrolled.grab_focus()

        # show it
        self.set_geometry_hints_max(window=window, min_height=360, min_width=635, max_height=-1, max_width=-1)
        self.set_resizable(True)
        self.show_all()
        
        self.run()
        self.destroy()

    def close_dialog(self, *args):
        self.library.conn.close()

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

    def export_to_csv(self, *args):
      filechooser = gtk.FileChooserDialog(parent=self, title='Save File ...', action=gtk.FileChooserAction.SAVE,
                                buttons=(gtk.STOCK_CANCEL,gtk.ResponseType.CANCEL,gtk.STOCK_SAVE,gtk.ResponseType.OK))
      filechooser.set_current_name('library.csv')
      filechooser.set_do_overwrite_confirmation(True)

      filter = gtk.FileFilter()
      filter.set_name("CSV files")
      filter.add_pattern("*.csv")
      filechooser.add_filter(filter)

      filter = gtk.FileFilter()
      filter.set_name("All files")
      filter.add_pattern("*")
      filechooser.add_filter(filter)

      response = filechooser.run()
      if response != gtk.ResponseType.OK:
        filechooser.destroy()
        return

      return_filename = str(filechooser.get_filename())
      filechooser.destroy()

      f = open(return_filename, encoding='utf-8', mode='w')
      line = '"Title","Publish Date","Rating","Publisher","Authors","Series","Genres","Languages","Annotation","Characters","Image Formats","Pages",'
      line = line + '"License","Has Panels","Finished reading"\n'
      f.write(line)
      books = []
      for book in self.library.cursor.execute("SELECT file_path, publish_date, publisher, authors, \
                                                      characters, pages, license, rating, has_frames, finished \
                                               FROM books"):
        books.append(book)

      for opened_book in books:
        file_path = opened_book[0]
        publish_date = opened_book[1]
        publisher = opened_book[2]
        authors = opened_book[3]
        characters = opened_book[4]
        pages = opened_book[5]
        license = opened_book[6]
        rating = opened_book[7]
        has_frames = opened_book[8]
        finished = opened_book[9]
        title, annotation, sequences, genres, languages, im_formats = self.get_book_details(file_path)

        rating_str = ''
        for asterisk in range(rating):
          rating_str = rating_str + '*'

        line = '"' + title + '","' + publish_date + '","' + rating_str + '","' + publisher + '","' + authors + '","' + sequences + '","' + genres + '","' + languages
        line = line + '","' + annotation + '","' + characters + '","' + im_formats + '","' + str(pages) + '","' + license + '","' + has_frames + '","' + finished
        line = line + '"\n'
        f.write(line)
      f.close()
    
    def resize_library(self, *args):
        if self.library_layout == 1 and self.old_window_size[0] != self.get_size()[0] and not self.isResizing:
          self.isResizing = True
          self.old_window_size = self.get_size()
          self.display_books()
          self.show_all()
          self.isResizing = False
        return False

    def key_pressed(self, widget, event):
        if event.keyval == Gdk.KEY_Left and self.books_start_number > 1:
          self.goto_previous_page()
        elif event.keyval in (Gdk.KEY_Right, Gdk.KEY_space) and self.books_start_number < self.total_books - self.books_per_page + 1:
          self.goto_next_page()
        elif event.keyval == Gdk.KEY_Home:
          self.goto_first_page()
        elif event.keyval == Gdk.KEY_End:
          self.goto_last_page()

        self.scrolled.grab_focus()
        return

    def show_info(self, *args):
        library_dialog = library_info.LibraryInfoDialog(self)
        return

    def remove_custom_filter(self, widget):
        message = gtk.MessageDialog(parent=None, flags=0, type=gtk.MessageType.QUESTION, buttons=gtk.ButtonsType.YES_NO, message_format=None)
        message.set_markup("Are you sure you want to remove this filter from the list?\n\n" + '<b>' + self.custom_filters.get_active_text() + '</b>')
        response = message.run()
        if response == gtk.ResponseType.YES:
          self._window.preferences.remove_library_filter(self.custom_filters.get_active_text())
        self._window.preferences.save_preferences()
        self.load_custom_filters()
        self.remove_button.set_sensitive(False)
        message.destroy()


    def save_custom_filter(self, widget):
        naming_dialog = gtk.Dialog('Save Filter as ...', self, gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT,
                        (gtk.STOCK_OK, gtk.ResponseType.OK))
        naming_dialog.set_resizable(False)
        naming_dialog.set_border_width(8)

        # filter name
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('New Filter Name: ')
        hbox.pack_start(label, False, False, 0)

        entry = gtk.Entry()
        entry.set_width_chars(30)
        if self.custom_filters.get_active_text() != None:
          entry.set_text(self.custom_filters.get_active_text())
        entry.show()
        hbox.pack_start(entry, False, False, 0)

        naming_dialog.vbox.pack_start(hbox, False, False, 0)
        naming_dialog.show_all()
        response = naming_dialog.run()

        # save filter to preferences
        if response == gtk.ResponseType.OK and entry.get_text() != '':
          self._window.preferences.save_library_filter(entry.get_text(),
                                                       str(self.title_entry.get_text()),
                                                       str(self.authors_entry.get_text()),
                                                       str(self.series_filter.get_active_text()),
                                                       self.genres_filter.get_active_text(),
                                                       str(self.rating_filter.get_active()),
                                                       str(self.characters_entry.get_text()),
                                                       self.languages_filter.get_active_text(),
                                                       self.publishdate_filter.get_active_text(),
                                                       str(self.publisher_filter.get_active_text()),
                                                       str(self.license_filter.get_active_text()),
                                                       str(self.read_filter.get_active()),
                                                       str(self.frames_filter.get_active()),
                                                       str(self.im_formats_filter.get_active_text())
                                                       )
          self._window.preferences.save_preferences()
          self.load_custom_filters()
        naming_dialog.destroy()
        
        return

    def set_custom_filter(self, widget, title, authors, series, genres, rating, characters, languages, publishdate, publisher, license, read, has_frames, im_format):
        self.filter_title = title
        self.filter_authors = authors
        
        for idx, item in enumerate(self.series):
          if item == series:
            self.filter_series = idx

        if license != None:
          for idx, item in enumerate(self.licenses):
            if item == license:
              self.filter_license = idx
        else:
          self.filter_license = 0

        for idx, item in enumerate(self.genres):
          if item == genres:
            self.filter_genres = idx

        self.filter_rating = int(rating)

        if read != None:
          self.filter_read = int(read)
        else:
          self.filter_read = 0

        if has_frames != None:
          self.filter_frames = int(has_frames)
        else:
          self.filter_frames = 0

        self.filter_characters = characters

        for idx, item in enumerate(self.languages):
          if item == languages:
            self.filter_languages = idx

        for idx, item in enumerate(self.publishdates):
          if item == publishdate:
            self.filter_publishdate = idx

        for idx, item in enumerate(self.publishers):
          if item == publisher:
            self.filter_publisher = idx

        for idx, item in enumerate(self.im_formats):
          if item == im_format:
            self.filter_im_formats = idx
        
        if widget.get_name() == 'GtkMenuItem':
          self.goto_first_page()

    def set_custom_filter_combo(self, widget):
      self.remove_button.set_sensitive(True)
      for custom_filter in self._window.preferences.tree.find('library_custom_filters').findall('filter'):
        if custom_filter.get("name") == widget.get_active_text():
          self.set_custom_filter(widget, custom_filter.get("title"), custom_filter.get("authors"), custom_filter.get("series"),
                                 custom_filter.get("genres"), custom_filter.get("rating"), custom_filter.get("characters"),
                                 custom_filter.get("languages"), custom_filter.get("publishdate"), custom_filter.get("publisher"),
                                 custom_filter.get("license"), custom_filter.get("read"), custom_filter.get("has_frames"),
                                 custom_filter.get("im_format"))
          self.title_entry.set_text(self.filter_title)
          self.authors_entry.set_text(self.filter_authors)
          self.series_filter.set_active(self.filter_series)
          self.genres_filter.set_active(self.filter_genres)
          self.rating_filter.set_active(self.filter_rating)
          self.characters_entry.set_text(self.filter_characters)
          self.languages_filter.set_active(self.filter_languages)
          self.publishdate_filter.set_active(self.filter_publishdate)
          self.publisher_filter.set_active(self.filter_publisher)
          self.license_filter.set_active(self.filter_license)
          self.read_filter.set_active(self.filter_read)
          self.frames_filter.set_active(self.filter_frames)
          self.im_formats_filter.set_active(self.filter_im_formats)

    def load_custom_filters(self, *args):
        for filter_menu_item in self.filter_menu.get_children():
          filter_menu_item.destroy()

        for i in range(len(self._window.preferences.tree.find('library_custom_filters').findall('filter')) + 1):
          self.custom_filters.remove(0)

        for custom_filter in sorted(self._window.preferences.tree.find('library_custom_filters').findall('filter'), key=lambda order: order.get("name")):
          menuitem = gtk.MenuItem(custom_filter.get("name"))
          menuitem.connect("activate", self.set_custom_filter, custom_filter.get("title"), custom_filter.get("authors"), custom_filter.get("series"),
                           custom_filter.get("genres"), custom_filter.get("rating"), custom_filter.get("characters"), custom_filter.get("languages"),
                           custom_filter.get("publishdate"), custom_filter.get("publisher"), custom_filter.get("license"), custom_filter.get("read"),
                           custom_filter.get("has_frames"), custom_filter.get("im_format"))
          self.filter_menu.add(menuitem)
          self.custom_filters.append_text(custom_filter.get("name"))


        self.filter_menu.show_all()

    def populate_filter_lists(self, *args):
        self.languages = []
        self.languages.append('all languages')
        t = ('??', )
        for row in self.library.cursor.execute('SELECT DISTINCT lang, show FROM languages WHERE lang != ? ORDER BY lang, show', t):
          if row[1] == 'FALSE':
            self.languages.append(row[0] + '(no text layer)')
          else:
            self.languages.append(row[0])
        self.languages.append('??(no text layer)')

        self.series = []
        self.series.append('all series')
        for row in self.library.cursor.execute('SELECT DISTINCT sequence_title FROM sequences ORDER BY sequence_title'):
          self.series.append(row[0])

        self.genres = []
        self.genres.append('all genres')
        for row in self.library.cursor.execute("SELECT DISTINCT genre FROM genres ORDER BY CASE WHEN genre = 'unknown' THEN 1 ELSE 0 END, genre"):
          self.genres.append(row[0])

        self.licenses = []
        self.licenses.append('all licenses')
        t = ('', )
        for row in self.library.cursor.execute('SELECT DISTINCT license FROM books WHERE license != ? ORDER BY license', t):
          self.licenses.append(row[0])

        self.publishers = []
        self.publishers.append('all publishers')
        t = ('', )
        for row in self.library.cursor.execute('SELECT DISTINCT publisher FROM books WHERE publisher != ? ORDER BY publisher', t):
          self.publishers.append(row[0])

        self.publishdates = []
        self.publishdates.append('all publish dates')
        for row in self.library.cursor.execute('SELECT DISTINCT substr(publish_date, 1, 4) FROM books ORDER BY substr(publish_date, 1, 4)'):
          self.publishdates.append(row[0])

        self.im_formats = []
        self.im_formats.append('all formats')
        for row in self.library.cursor.execute('SELECT DISTINCT format FROM image_formats ORDER BY format'):
          self.im_formats.append(row[0]) 

    def set_filter(self, *args):
        self.filter_dialog = gtk.Dialog('Set Filter', self, gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT,
                          (gtk.STOCK_APPLY, gtk.ResponseType.OK))
        self.filter_dialog.set_resizable(False)
        self.filter_dialog.set_border_width(8)

        # clear filter button
        clear_button = gtk.Button(stock=gtk.STOCK_CLEAR)
        clear_button.connect("clicked", self.clear_filter)
        self.filter_dialog.get_action_area().add(clear_button)
        self.filter_dialog.get_action_area().reorder_child(clear_button, 0)

        self.filter_dialog.connect('key_press_event', self.filter_key_pressed)

        # populate lists
        self.populate_filter_lists()

        # customs filters
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        self.custom_filters = gtk.ComboBoxText()
        self.custom_filters.set_tooltip_text('List of Custom Filters')
        self.load_custom_filters()
        self.custom_filters.connect("changed", self.set_custom_filter_combo)
        hbox.pack_start(self.custom_filters, False, False, 0)

        save_button = gtk.ToolButton(gtk.STOCK_SAVE)
        save_button.set_tooltip_text('Save Current Filter As ...')
        save_button.connect("clicked", self.save_custom_filter)
        hbox.pack_start(save_button, False, False, 0)

        self.remove_button = gtk.ToolButton(gtk.STOCK_REMOVE)
        self.remove_button.set_tooltip_text('Remove Custom Filter')
        self.remove_button.connect("clicked", self.remove_custom_filter)
        self.remove_button.set_sensitive(False)
        hbox.pack_start(self.remove_button, False, False, 0)

        self.filter_dialog.vbox.pack_start(hbox, False, False, 0)

        # separator
        separator = gtk.HSeparator()
        self.filter_dialog.vbox.pack_start(separator, False, False, 0)


        # Title
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Title (contains): ')
        hbox.pack_start(label, False, False, 0)

        self.title_entry = gtk.Entry()
        self.title_entry.set_width_chars(30)
        self.title_entry.set_text(self.filter_title)
        self.title_entry.show()
        hbox.pack_start(self.title_entry, False, False, 0)

        self.filter_dialog.vbox.pack_start(hbox, False, False, 0)

        # Authors
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Author(s) (contain): ')
        hbox.pack_start(label, False, False, 0)

        self.authors_entry = gtk.Entry()
        self.authors_entry.set_width_chars(30)
        self.authors_entry.set_text(self.filter_authors)
        self.authors_entry.show()
        hbox.pack_start(self.authors_entry, False, False, 0)

        self.filter_dialog.vbox.pack_start(hbox, False, False, 0)

        # Series
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Series: ')
        hbox.pack_start(label, False, False, 0)

        self.series_filter = gtk.ComboBoxText()
        for serie in self.series:
          self.series_filter.append_text(serie)
        self.series_filter.set_active(self.filter_series)
        hbox.pack_start(self.series_filter, False, False, 0)
        self.series_filter.connect('changed', self.set_series_filter)

        self.filter_dialog.vbox.pack_start(hbox, False, False, 0)

        # Genres & Rating
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Genre: ')
        hbox.pack_start(label, False, False, 0)

        self.genres_filter = gtk.ComboBoxText()
        for genre in self.genres:
          self.genres_filter.append_text(genre)
        self.genres_filter.set_active(self.filter_genres)
        hbox.pack_start(self.genres_filter, False, False, 0)
        self.genres_filter.connect('changed', self.set_genres_filter)

        label = gtk.Label()
        label.set_markup('    Rating: ')
        hbox.pack_start(label, False, False, 0)

        self.rating_filter = gtk.ComboBoxText()
        self.rating_filter.append_text('Do not filter')
        self.rating_filter.append_text('Without rating')
        self.rating_filter.append_text('*')
        self.rating_filter.append_text('**')
        self.rating_filter.append_text('***')
        self.rating_filter.append_text('****')
        self.rating_filter.append_text('*****')
        self.rating_filter.set_active(self.filter_rating)
        hbox.pack_start(self.rating_filter, False, False, 0)
        self.rating_filter.connect('changed', self.set_rating_filter)

        self.filter_dialog.vbox.pack_start(hbox, False, False, 0)

        # Characters & read
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Characters (contain): ')
        hbox.pack_start(label, False, False, 0)

        self.characters_entry = gtk.Entry()
        self.characters_entry.set_width_chars(15)
        self.characters_entry.set_text(self.filter_characters)
        self.characters_entry.show()
        hbox.pack_start(self.characters_entry, False, False, 0)

        label = gtk.Label()
        label.set_markup('    Read: ')
        hbox.pack_start(label, False, False, 0)

        self.read_filter = gtk.ComboBoxText()
        for read in self.read:
          self.read_filter.append_text(read)
        self.read_filter.set_active(self.filter_read)
        hbox.pack_start(self.read_filter, False, False, 0)
        self.read_filter.connect('changed', self.set_read_filter)

        self.filter_dialog.vbox.pack_start(hbox, False, False, 0)

        # Languages & Frames
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Language: ')
        hbox.pack_start(label, False, False, 0)

        self.languages_filter = gtk.ComboBoxText()
        for language in self.languages:
          self.languages_filter.append_text(language)
        self.languages_filter.set_active(self.filter_languages)
        hbox.pack_start(self.languages_filter, False, False, 0)
        self.languages_filter.connect('changed', self.set_languages_filter)

        label = gtk.Label()
        label.set_markup('    Frames definition: ')
        hbox.pack_start(label, False, False, 0)

        self.frames_filter = gtk.ComboBoxText()
        for frame_def in self.frames_def:
          self.frames_filter.append_text(frame_def)
        self.frames_filter.set_active(self.filter_frames)
        hbox.pack_start(self.frames_filter, False, False, 0)
        self.frames_filter.connect('changed', self.set_frames_filter)

        self.filter_dialog.vbox.pack_start(hbox, False, False, 0)

        # Publisher & Publish date
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Publisher: ')
        hbox.pack_start(label, False, False, 0)

        self.publisher_filter = gtk.ComboBoxText()
        for publisher in self.publishers:
          self.publisher_filter.append_text(publisher)
        self.publisher_filter.set_active(self.filter_publisher)
        hbox.pack_start(self.publisher_filter, False, False, 0)
        self.publisher_filter.connect('changed', self.set_publisher_filter)

        label = gtk.Label()
        label.set_markup('    Publish date: ')
        hbox.pack_start(label, False, False, 0)

        self.publishdate_filter = gtk.ComboBoxText()
        for publishdate in self.publishdates:
          self.publishdate_filter.append_text(publishdate)
        self.publishdate_filter.set_active(self.filter_publishdate)
        hbox.pack_start(self.publishdate_filter, False, False, 0)
        self.publishdate_filter.connect('changed', self.set_publishdate_filter)

        self.filter_dialog.vbox.pack_start(hbox, False, False, 0)

        # License
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('License: ')
        hbox.pack_start(label, False, False, 0)

        self.license_filter = gtk.ComboBoxText()
        for license in self.licenses:
          self.license_filter.append_text(license)
        self.license_filter.set_active(self.filter_license)
        hbox.pack_start(self.license_filter, False, False, 0)
        self.license_filter.connect('changed', self.set_license_filter)

        self.filter_dialog.vbox.pack_start(hbox, False, False, 0)

        # Image Formats
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)

        label = gtk.Label()
        label.set_markup('Image Format: ')
        hbox.pack_start(label, False, False, 0)

        self.im_formats_filter = gtk.ComboBoxText()
        for im_format in self.im_formats:
          self.im_formats_filter.append_text(im_format)
        self.im_formats_filter.set_active(self.filter_im_formats)
        hbox.pack_start(self.im_formats_filter, False, False, 0)
        self.im_formats_filter.connect('changed', self.set_im_formats_filter)

        self.filter_dialog.vbox.pack_start(hbox, False, False, 0)
        
        # show it
        self.filter_dialog.show_all()
        response = self.filter_dialog.run()

        if response == gtk.ResponseType.OK:
          self.filter_title = self.title_entry.get_text()
          self.filter_characters = self.characters_entry.get_text()
          self.filter_authors = self.authors_entry.get_text()
        
        self.filter_dialog.destroy()

        if response == gtk.ResponseType.OK:
          self.goto_first_page()
        
        return

    def filter_key_pressed(self, widget, event):
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
          self.filter_dialog.response(gtk.ResponseType.OK)

    def set_series_filter(self, widget, *args):
        self.filter_series = widget.get_active()
        return

    def set_license_filter(self, widget, *args):
        self.filter_license = widget.get_active()
        return

    def set_publishdate_filter(self, widget, *args):
        self.filter_publishdate = widget.get_active()
        return

    def set_publisher_filter(self, widget, *args):
        self.filter_publisher = widget.get_active()
        return

    def set_rating_filter(self, widget, *args):
        self.filter_rating = widget.get_active()
        return

    def set_read_filter(self, widget, *args):
        self.filter_read = widget.get_active()
        return

    def set_frames_filter(self, widget, *args):
        self.filter_frames = widget.get_active()
        return

    def set_genres_filter(self, widget, *args):
        self.filter_genres = widget.get_active()
        return

    def set_languages_filter(self, widget, *args):
        self.filter_languages = widget.get_active()
        return

    def set_im_formats_filter(self, widget, *args):
        self.filter_im_formats = widget.get_active()
        return

    def clear_filter(self, widget):
        self.title_entry.set_text('')
        self.authors_entry.set_text('')
        self.characters_entry.set_text('')
        self.series_filter.set_active(0)
        self.license_filter.set_active(0)
        self.genres_filter.set_active(0)
        self.rating_filter.set_active(0)
        self.read_filter.set_active(0)
        self.frames_filter.set_active(0)
        self.languages_filter.set_active(0)
        self.publishdate_filter.set_active(0)
        self.publisher_filter.set_active(0)
        self.im_formats_filter.set_active(0)
        self.filter_title = self.filter_characters = self.filter_authors = ''
        return

    def change_library_layout(self, widget, layout):
        if layout == 'N':
          self.library_layout = 0
        elif layout == 'C':
          self.library_layout = 1
        elif layout == 'L':
          self.library_layout = 2
        for button in self.toggle_button_hbox.get_children():
          if button.get_label() != layout:
            button.set_sensitive(True)
          else:
            button.set_sensitive(False)
        self.display_books()
        self.update_entry()
        self.show_all()

    def change_sort_order(self, *args):
        self.display_books()
        self.update_entry()
        if self.total_books > 0:
          self.library_info_button.set_sensitive(True)
        else:
          self.library_info_button.set_sensitive(False)
        self.show_all()

        return

    def update_entry(self, *args):
        current_page = str(int(round((self.books_start_number - 1)/self.books_per_page + 1, 0)))
        entry_text = ' ' + current_page + '/' + str(self.number_of_pages) + ' '
        self.entry.set_text(entry_text)

    def goto_first_page(self, *args):
        self.books_start_number = 1
        self.display_books()
        self.update_entry()
        self.show_all()
        return

    def goto_previous_page(self, *args):
        self.books_start_number = self.books_start_number - self.books_per_page
        self.update_entry()
        self.display_books()
        self.show_all()
        return

    def goto_next_page(self, *args):
        self.books_start_number = self.books_start_number + self.books_per_page
        self.update_entry()
        self.display_books()
        self.show_all()
        return

    def goto_last_page(self, *args):
        self.books_start_number = (self.number_of_pages - 1) * self.books_per_page + 1
        self.update_entry()
        self.display_books()
        self.show_all()
        return

    def get_book_details(self, filename):
        #default book language
        if self.preferences.get_value("default_language") != "0":
          default_language = constants.LANGUAGES[int(self.preferences.get_value("default_language"))]
        else:
          default_language = ''
        
        self.library.cursor.execute("SELECT lang \
                                     FROM languages \
                                     WHERE file_path = ? AND lang = ? \
                                     UNION ALL \
                                     SELECT lang \
                                     FROM languages \
                                     WHERE file_path = ? AND lang = 'en' \
                                     UNION ALL \
                                     SELECT max(lang) \
                                     FROM languages \
                                     WHERE file_path = ?", (filename, default_language, filename, filename))
        book_language = self.library.cursor.fetchone()
        if book_language == None:
          book_language = '??'

        #meta-data
        self.library.cursor.execute("SELECT title \
                                     FROM titles \
                                     WHERE file_path = ? \
                                       AND (lang = ? OR lang IS NULL)", (filename, book_language[0]))
        title = self.library.cursor.fetchone()
        if title == None or title == (None,):
          title = ['']
        
        self.library.cursor.execute("SELECT annotation \
                                     FROM annotations \
                                     WHERE file_path = ? \
                                       AND (lang = ? OR lang IS NULL)", (filename, book_language[0]))
        annotation = self.library.cursor.fetchone()
        if annotation == None or annotation == (None,):
          annotation = ['']

        sequences = ''
        for row in self.library.cursor.execute("SELECT sequence_title || ' (' || sequence_number || ')' \
                                                FROM sequences \
                                                WHERE file_path = ?", (filename, )):
          sequences = sequences + ', ' + row[0]
        sequences = sequences[2:]

        genres = ''
        for row in self.library.cursor.execute("SELECT genre \
                                                FROM genres \
                                                WHERE file_path = ?", (filename, )):
          genres = genres + ', ' + row[0]
        genres = genres[2:]

        languages = ''
        for row in self.library.cursor.execute("SELECT lang, show \
                                                FROM languages \
                                                WHERE file_path = ?", (filename, )):
          if row[1] == 'FALSE':
            languages = languages + ', ' + row[0] + '(no text layer)'
          else:
            languages = languages + ', ' + row[0]
        languages = languages[2:]

        im_formats = ''
        for row in self.library.cursor.execute("SELECT format \
                                                FROM image_formats \
                                                WHERE file_path = ?", (filename, )):
          im_formats = im_formats + ', ' + row[0]
        im_formats = im_formats[2:]

        return title[0], annotation[0], sequences, genres, languages, im_formats
        

    def open_book(self, widget, event, filename):
        dialog = gtk.Dialog('Comic Book', self, gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT,
                          (gtk.STOCK_REMOVE, gtk.ResponseType.REJECT, gtk.STOCK_OK, gtk.ResponseType.OK))
        self.set_geometry_hints_max(window=dialog, min_height=500, min_width=700, max_width=800, max_height=0)
        dialog.set_resizable(False)
        #dialog.set_size_request(700, 500)
        dialog.set_border_width(8)

        hbox = gtk.HBox(False, 0)

        open_button = gtk.Button(stock=gtk.STOCK_OPEN)
        dialog.add_action_widget(open_button, gtk.ResponseType.APPLY)
        open_button.grab_focus()

        title, annotation, sequences, genres, languages, im_formats = self.get_book_details(filename)

        #meta-data
        self.library.cursor.execute("SELECT coverpage, publish_date, publisher, authors, \
                                            characters, pages, license, rating, has_frames, finished \
                                     FROM books \
                                     WHERE books.file_path = ?", (filename, ))
        opened_book = self.library.cursor.fetchone()
        
        coverpage_path = opened_book[0]
        publish_date = " (" + opened_book[1][0:4] + ")"
        publisher = opened_book[2]
        authors = opened_book[3]
        characters = opened_book[4]
        pages = opened_book[5]
        license = opened_book[6]
        rating = opened_book[7]
        has_frames = opened_book[8]
        finished = opened_book[9]

        ## show
        # coverpage
        coverpage = gtk.Image()
        cover_pix = GdkPixbuf.Pixbuf.new_from_file_at_size(coverpage_path, 200, 200)
        coverpage.set_from_pixbuf(cover_pix)
        coverpage.set_alignment(0, 0)

        vbox = gtk.VBox(False, 5)
        vbox.set_border_width(8)
        vbox.pack_start(coverpage, False, False, 0)

        # rating
        self.rating_box = gtk.HBox(False, 5)
        self.rating_box.rating = rating
        self.rate_book(None, None, filename, self.rating_box.rating)
        vbox.pack_start(self.rating_box, False, False, 0)

        # progress
        x_progress = 0
        (page_number, frame_number, zoom_level, language_layer) = self._window.history.get_book_details(filename)
        if page_number > 1:
          progress = int(float(page_number)/(pages + 1)*100)
        else:
          progress = 0

        if finished == "True":
          x_progress = 100
        else:
          x_progress = progress

        self.read_button = gtk.CheckButton('Read: ' + str(x_progress) + '%')
        self.read_button.connect("toggled", self.set_read_button, filename, progress)
        if finished == "True":
          self.read_button.set_active(True)

        vbox.pack_start(self.read_button, False, False, 0)

        hbox.pack_start(vbox, False, False, 0)

        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(480, 300)
        book_details = gtk.VBox(False, 0)
        book_details.set_border_width(5)
        scrolled.add_with_viewport(book_details)

        # book meta-data
        label = gtk.Label()
              
        markup = '<big><b>' + title + publish_date + '</b></big>' + '\n<b>Author(s): </b> ' + authors
        if sequences != '':
          markup = markup + '\n<b>Series: </b> ' + sequences
        markup = markup + '\n<b>Publisher: </b> ' + publisher
        if license != '':
          markup = markup + '\n<b>License: </b> ' + license
        markup = markup + '\n<b>Genre(s): </b> ' + genres
        if characters != '':
          markup = markup + '\n<b>Characters: </b> ' + characters
        markup = markup + '\n<b>Annotation: </b> ' + annotation + '\n<b>Frames definitions: </b> '
        if has_frames == '':
          markup = markup + 'False'
        else:
          markup = markup + has_frames
        markup = markup + '\n<b>Languages: </b> ' + languages
        if im_formats != '':
          markup = markup + '\n<b>Image Format(s): </b> ' + im_formats
        markup = markup + '\n<b>Filename: </b> ' + escape(filename)

        label.set_markup(markup)
        book_details.pack_start(label, False, True, 0)

        for label in book_details.get_children():
          label.set_alignment(0, 0)
          label.set_line_wrap(True)
          label.set_selectable(True)

        hbox.pack_end(scrolled, True, True, 0)

        dialog.vbox.pack_start(hbox, False, False, 0)
        #self.set_geometry_hints_max(dialog, min_height=200, min_width=635, max_width = -1, max_height = -1)
        dialog.show_all()
        response = dialog.run()

        if response == gtk.ResponseType.APPLY:
          self._window.filename = filename
          self._window.original_filename = filename
          self.library.conn.close()
          dialog.destroy()
          self.destroy()
        elif response == gtk.ResponseType.REJECT:
          self.remove_book(filename, title)
          dialog.destroy()
        elif response == gtk.ResponseType.OK:
          dialog.destroy()
          if self.rating_box.rating != rating:
            t = (self.rating_box.rating, filename)
            self.library.cursor.execute('UPDATE books SET rating=? WHERE file_path=?', t)
            self.library.conn.commit()
            
            self.change_sort_order()
          if ((finished != "True" and self.read_button.get_active()) or
              (finished == "True" and not self.read_button.get_active())):
            if self.read_button.get_active():
              self.library.cursor.execute("UPDATE books SET finished='True' WHERE file_path=?", (filename, ))
              self.library.conn.commit()
            else:
              self.library.cursor.execute("UPDATE books SET finished='False' WHERE file_path=?", (filename, ))
              self.library.conn.commit()
            self.change_sort_order()
        else:
          dialog.destroy()

        return

    def remove_book(self, filename, bookname):
        message = gtk.MessageDialog(parent=self, flags=0, type=gtk.MessageType.QUESTION, buttons=gtk.ButtonsType.YES_NO, message_format=None)
        message.set_markup("Are you sure you want to remove this book from library?\n\n" + '<b>' + bookname + '</b>')
        response = message.run()
        if response == gtk.ResponseType.YES:
          self.library.delete_book(filename)
          self.display_books()
          self.update_entry()
          self.show_all()
        message.destroy()

    def set_read_button(self, widget, filename, progress):
        if widget.get_active():
          x_progress = 100
        else:
          x_progress = progress
        widget.set_label('Read: ' + str(x_progress) + '%')

    def rate_book(self, widget, event, filename, rating):
        self.rating_box.rating = rating

        for i in self.rating_box.get_children():
          i.destroy()

        for asterisk in range(rating):
          star = gtk.Image()
          star.set_from_stock(gtk.STOCK_ABOUT, gtk.IconSize.MENU)
          star.set_tooltip_text('Rating')
          eventbox = gtk.EventBox()
          eventbox.add(star)
          eventbox.connect('button-press-event', self.rate_book, filename, asterisk + 1)
          self.rating_box.pack_start(eventbox, False, False, 0)

        for asterisk in range(5 - rating):
          blank = gtk.Image()
          blank.set_from_stock(gtk.STOCK_CLOSE, gtk.IconSize.MENU)
          blank.set_tooltip_text('Rating')
          eventbox = gtk.EventBox()
          eventbox.add(blank)
          eventbox.connect('button-press-event', self.rate_book, filename, asterisk + rating + 1)
          self.rating_box.pack_start(eventbox, False, False, 0)

        self.rating_box.show_all()

    def check_books(self, *args):
        for row in self.library.cursor.execute("SELECT file_path \
                                                FROM books"):
          if not os.path.exists(row[0]):
            self.library.delete_book(row[0])

        # remove duplicates (cbz with same base filename as acbf file)
        referenced_archives = []
        for referenced_archive in self.library.cursor.execute("SELECT file_path \
                                                               FROM books"):
          if referenced_archive[0][-4:].upper() == 'ACBF':
            referenced_archives.append(referenced_archive[0][0:-4] + 'cbz')

        for referenced_archive in referenced_archives:
          self.library.delete_book(referenced_archive)

        # cleanup library covers directory
        if randint(0,49) == 0: #this is slow, therefore we do it once in 50 times
          for root, dirs, files in os.walk(os.path.join(constants.CONFIG_DIR, 'Covers')):
            for f in files:
              do_remove = True
              for book in self.library.cursor.execute("SELECT coverpage \
                                                       FROM books"):
                if os.path.join(root, f) == book[0]:
                  do_remove = False
              if do_remove:
                os.unlink(os.path.join(root, f))
            for d in dirs:
              if not os.listdir(os.path.join(root, d)):
                shutil.rmtree(os.path.join(root, d))

        return

    def display_books(self, *args):
        for child_widget in self.book_list.get_children():
          child_widget.destroy()
        
        horizontal_list = gtk.HBox(False, 0)
        current_line_length = 0

        books_added = 0
        self.total_books = 0

        if self.library_layout == 2:
          self.scrolled.set_policy(gtk.PolicyType.AUTOMATIC, gtk.PolicyType.AUTOMATIC)
        else:
          self.scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)

        #default book language
        if self.preferences.get_value("default_language") != "0":
          default_language = constants.LANGUAGES[int(self.preferences.get_value("default_language"))]
        else:
          default_language = ''

        sort_items = ["ifnull(title, 'ZZZZ')", "ifnull(sequence_title, 'ZZZZ'), sequence_number", "CASE WHEN authors = '' THEN 'ZZZZ' ELSE upper(authors) END",
                      "CASE WHEN publisher = '' THEN 'ZZZZ' ELSE upper(publisher) END, ifnull(sequence_title, 'ZZZZ'), sequence_number",
                      "publish_date", "languages.show DESC, replace(languages.lang, '??', 'zz')", "rating DESC, ifnull(sequence_title, 'ZZZZ'), sequence_number"]
        order_by = sort_items[self.sort_by.get_active()]

        books = []
        for row in self.library.cursor.execute("SELECT DISTINCT file_path, coverpage, publish_date, publisher, authors, \
                                                       characters, pages, license, rating, has_frames, finished \
                                                FROM \
                                               (SELECT books.file_path, coverpage, substr(publish_date, 1, 4) publish_date, publisher, authors, \
                                                       characters, pages, license, rating, has_frames, finished \
                                                FROM books \
                                                LEFT JOIN titles ON books.file_path = titles.file_path \
                                                LEFT JOIN annotations ON books.file_path = annotations.file_path \
                                                LEFT JOIN languages ON books.file_path = languages.file_path \
                                                LEFT JOIN sequences ON books.file_path = sequences.file_path \
                                                LEFT JOIN genres ON books.file_path = genres.file_path \
                                                LEFT JOIN image_formats ON books.file_path = image_formats.file_path \
                                                WHERE ? in (genres.genre, 'all genres') \
                                                  AND ? in (languages.lang || CASE WHEN languages.show = 'FALSE' THEN '(no text layer)' ELSE '' END, 'all languages') \
                                                  AND (replace(upper(titles.title), ?, '') != upper(titles.title) or ? = '') \
                                                  AND (replace(upper(characters), ?, '') != upper(characters) or ? = '') \
                                                  AND (replace(upper(authors), ?, '') != upper(authors) or ? = '') \
                                                  AND ? in (sequences.sequence_title, 'all series') \
                                                  AND ? in (rating, -1) AND ? in (finished, 'Do Not Filter') \
                                                  AND ? in (has_frames, 'Do Not Filter') \
                                                  AND ? in (image_formats.format, 'all formats') \
                                                  AND ? in (publisher, 'all publishers') \
                                                  AND ? in (license, 'all licenses') \
                                                  AND ? in (substr(publish_date, 1, 4), 'all publish dates') \
                                                ORDER BY " + order_by + " \
                                                )", (self.genres[self.filter_genres], self.languages[self.filter_languages],
                                                    str(self.filter_title.upper()), str(self.filter_title.upper()),
                                                    self.filter_characters.upper(), self.filter_characters.upper(),
                                                    self.filter_authors.upper(), self.filter_authors.upper(),
                                                    self.series[self.filter_series], self.filter_rating - 1,
                                                    self.read[self.filter_read], self.frames_def[self.filter_frames],
                                                    self.im_formats[self.filter_im_formats], self.publishers[self.filter_publisher],
                                                    self.licenses[self.filter_license], self.publishdates[self.filter_publishdate]
                                                    )):
          book = {'file_path': row[0], 'coverpage': row[1], 'publish_date': row[2], 'publisher': row[3], 'authors': row[4],
                  'characters': row[5], 'pages': row[6], 'license': row[7], 'rating': row[8], 'has_frames': row[9], 'finished': row[10],
                  'publish_date_x': ' (' + row[2] + ')'}
          books.append(book)

        for book in books:
          title, annotation, sequences, genres, languages, im_formats = self.get_book_details(book['file_path'])

          rating = '  '
          for asterisk in range(book['rating']):
            rating = rating + '*'

          self.total_books = self.total_books + 1

          if books_added < self.books_per_page and self.total_books >= self.books_start_number:
            hbox = gtk.HBox(False, 0)
            eventbox = gtk.EventBox()
            eventbox.connect('button-press-event', self.open_book, book['file_path'])

            if self.library_layout in (0, 1):
              # coverpage
              coverpage = gtk.Image()
              cover_pix = GdkPixbuf.Pixbuf.new_from_file_at_size(book['coverpage'], 200, 200)
              coverpage_width = cover_pix.get_width()
              coverpage.set_from_pixbuf(cover_pix)
              coverpage.set_alignment(0.5, 0)
              eventbox.add(coverpage)

              vbox = gtk.VBox(False, 5)
              vbox.set_border_width(8)
              vbox.pack_start(eventbox, False, False, 0)

            if self.library_layout == 0:  #normal layout
              hbox.pack_start(vbox, False, False, 0)

              book_details = gtk.VBox(False, 0)
              book_details.set_border_width(5)

              # book meta-data
              label = gtk.Label()

              markup = '<big><b>' + title + book['publish_date_x'] + rating +  '</b></big>' + '\n<b>Author(s): </b> ' + book['authors']
              if sequences != '':
                markup = markup + '\n<b>Series: </b> ' + sequences
              markup = markup + '\n<b>Publisher: </b> ' + book['publisher']
              if book['license'] != '':
                markup = markup + '\n<b>License: </b> ' + book['license']
              markup = markup + '\n<b>Genre(s): </b> ' + genres
              if book['characters'] != '':
                markup = markup + '\n<b>Characters: </b> ' + book['characters']
              markup = markup + '\n<b>Annotation: </b> ' + annotation + '\n<b>Frames definitions: </b> '
              markup = markup + book['has_frames']
              markup = markup + '\n<b>Languages: </b> ' + languages
              if im_formats != '':
                markup = markup + '\n<b>Image Format(s): </b> ' + im_formats

              label.set_markup(markup)
              #label.connect("size-allocate", self.size_request)
              book_details.pack_start(label, False, True, 0)

              for label in book_details.get_children():
                label.set_alignment(0, 0)
                label.set_line_wrap(True)
                label.set_selectable(True)

              hbox.pack_end(book_details, True, True, 0)
              self.book_list.pack_start(hbox, False, False, 0)
              books_added = books_added + 1
            elif self.library_layout == 1: #compact layout
              if ((current_line_length + coverpage_width) > self.get_size()[0]):
                current_line_length = coverpage_width + 30
                self.book_list.pack_start(horizontal_list, False, False, 0)
                horizontal_list = gtk.HBox(False, 0)
              else:
                current_line_length = current_line_length + coverpage_width + 30

              label = gtk.Label()
              label.set_markup('<small><b>' + title + '</b></small>')

              label.set_line_wrap(True)
              label.set_justify(gtk.Justification.CENTER)
              label.set_size_request(coverpage_width, -1)
              label.set_alignment(0.5, 0.5)

              vbox.pack_start(label, False, False, 0)

              eventbox.set_tooltip_text(title + book['publish_date_x'] + rating + sequences + book['authors'])
              horizontal_list.pack_start(vbox, False, False, 0)
              books_added = books_added + 1
            elif self.library_layout == 2: #list layout
              eventbox.add(hbox)

              columns_list = [title, book['publish_date'], rating, book['publisher'], book['authors'], sequences, genres, languages]

              if books_added == 0:
                labels_hbox = gtk.HBox(False, 0)
                labels_list = ["Title", "Publish Date", "Rating", "Publisher", "Authors", "Series", "Genres", "Languages"]
                for column_label in labels_list:
                  label = gtk.Label()
                  label.set_markup(column_label)
                  label.set_alignment(0, 0.5)
                  labels_hbox.pack_start(label, False, False, 5)
                self.book_list.pack_start(labels_hbox, False, False, 0)
                
              for column_label in columns_list:
                label = gtk.Label()
                label.set_markup(column_label)
                label.set_alignment(0, 0.5)
                hbox.pack_start(label, False, False, 5)

              if books_added % 2 == 0:
                eventbox.set_state(gtk.StateType.ACTIVE)
              self.book_list.pack_start(eventbox, False, False, 0)
              books_added = books_added + 1

        if self.library_layout == 1:
          self.book_list.pack_start(horizontal_list, False, False, 0)
        elif self.library_layout == 2:
          # get max values
          book_column_lengths = [0, 0, 0, 0, 0, 0, 0, 0]
          for book in self.book_list.get_children():
            for i in range(0, len(book_column_lengths)):
              try:
                label = str(book.get_children()[0].get_children()[i].get_text())
              except:
                label = str(book.get_children()[i].get_text())
              if len(label) > book_column_lengths[i]:
                book_column_lengths[i] = len(label)

          # align columns
          for idx, book in enumerate(self.book_list.get_children()):
            for i in range(0, len(book_column_lengths)):
              try:
                label = str(book.get_children()[0].get_children()[i].get_text())
              except:
                label = str(book.get_children()[i].get_text())
              new_label = label.ljust(book_column_lengths[i])
              if idx == 0:
                new_label = "<span font_family='monospace' underline='low' font_weight='bold'>" + escape(new_label) + "</span>"
                book.get_children()[i].set_markup(new_label)
              else:
                book.get_children()[0].get_children()[i].set_markup("<tt>" + escape(new_label) + "</tt>")
            
        self.number_of_pages = int(round((self.total_books/float(self.books_per_page)) + 0.49999, 0))
        
        # adjust navigational buttons sensitivity
        if self.books_start_number == 1:
          self.goto_first_button.set_sensitive(False)
          self.goto_prev_button.set_sensitive(False)
        else:
          self.goto_first_button.set_sensitive(True)
          self.goto_prev_button.set_sensitive(True)

        if self.books_start_number < self.total_books - self.books_per_page + 1:
          self.goto_next_button.set_sensitive(True)
          self.goto_last_button.set_sensitive(True)
        else:
          self.goto_next_button.set_sensitive(False)
          self.goto_last_button.set_sensitive(False)

        self.scrolled.get_vadjustment().set_value(0)
        self.scrolled.get_hadjustment().set_value(0)
        return True

    def size_request(self, l, s ):
        l.set_size_request(s.width -1, -1)

    def add_book_folder(self, *args):
        filechooser = gtk.FileChooserDialog(title='Add Comic Book Folder ...', action=gtk.FileChooserAction.OPEN,
                                  buttons=(gtk.STOCK_CANCEL,gtk.ResponseType.CANCEL,gtk.STOCK_OPEN,gtk.ResponseType.OK))
        filechooser.set_action(gtk.FileChooserAction.SELECT_FOLDER)

        response = filechooser.run()
        if response != gtk.ResponseType.OK:
          filechooser.destroy()
          return
        
        directory = str(filechooser.get_filename())
        filechooser.destroy()

        progress_dialog = gtk.Dialog('Adding Comic Books ...', self, gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT, None)
        progress_dialog.set_resizable(False)
        progress_dialog.set_border_width(8)
        progress_dialog.set_size_request(400, 100)

        progress_bar = gtk.ProgressBar()
        progress_bar.set_size_request(-1, 13)
        progress_bar.show()

        progress_dialog.vbox.pack_start(progress_bar, False, False, 5)

        book_name = gtk.Label()
        book_name.set_markup('')
        progress_dialog.vbox.pack_start(book_name, True, True, 0)

        progress_dialog.show_all()

        while gtk.events_pending():
          gtk.main_iteration()

        books_added = float(0)
        total_books_to_add = 0

        for root, dirs, files in os.walk(directory):
          for f in files:
            if f[-4:].upper() == '.CBZ' or f[-5:].upper() == '.ACBF' or f[-4:].upper() == '.ACV':
              total_books_to_add = total_books_to_add + 1

        for root, dirs, files in os.walk(directory):
          for f in files:
            f = str(f)
            if f[-4:].upper() == '.CBZ' or f[-5:].upper() == '.ACBF' or f[-4:].upper() == '.ACV':
              book_name.set_markup(escape(f))
              try:
                self.insert_new_book(os.path.join(root, f), False)
              except Exception as inst:
                message = gtk.MessageDialog(parent=None, flags=0, type=gtk.MessageType.WARNING, buttons=gtk.ButtonsType.OK, message_format=None)
                message.set_markup("Failed to import comic book\n\n" + '<b>' + f + '</b>\n\n' + 'Exception: %s' % inst)
                response = message.run()
                message.destroy()
              books_added = books_added + 1
              progress_bar.set_fraction(books_added/total_books_to_add)
              while gtk.events_pending():
                gtk.main_iteration()

        progress_dialog.destroy()

        self.populate_filter_lists()
        self.change_sort_order()
        self.show_all()
        
        return

    def add_book(self, *args):
        filechooser = gtk.FileChooserDialog(title='Add Comic Book ...', action=gtk.FileChooserAction.OPEN,
                                  buttons=(gtk.STOCK_CANCEL,gtk.ResponseType.CANCEL,gtk.STOCK_OPEN,gtk.ResponseType.OK))
        # filters
        filter = gtk.FileFilter()
        filter.set_name("Comicbook files")
        filter.add_pattern("*.acbf")
        filter.add_pattern("*.acv")
        filter.add_pattern("*.cbz")
        filter.add_pattern("*.zip")
        filter.add_pattern("*.cbr")
        filechooser.add_filter(filter)

        filter = gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        filechooser.add_filter(filter)

        response = filechooser.run()

        if response != gtk.ResponseType.OK:
          filechooser.destroy()
          return
        
        filename = str(filechooser.get_filename())
        filechooser.destroy()

        try:
          if self.insert_new_book(filename, True):
            self.populate_filter_lists()
            self.change_sort_order()
            self.show_all()
        except Exception as inst:
          message = gtk.MessageDialog(parent=None, flags=0, type=gtk.MessageType.WARNING, buttons=gtk.ButtonsType.OK, message_format=None)
          message.set_markup("Failed to import comic book\n\n" + '<b>' + filename + '</b>\n\n' + 'Exception: %s' % inst)
          response = message.run()
          message.destroy()

        return

    def insert_new_book(self, filename, show_dialog):
        # check if already exists in library
        rating = 0
        filename = filename.replace('\\', os.sep).replace('/', os.sep)
        t = (filename,)
        self.library.cursor.execute('SELECT rating FROM books WHERE file_path=?', t)
        current_rating = self.library.cursor.fetchone()
        if current_rating != None:
          rating = current_rating[0]
          t = (filename,)
          self.library.cursor.execute('DELETE FROM books WHERE file_path=?', t)
          self.library.cursor.execute('DELETE FROM titles WHERE file_path=?', t)
          self.library.cursor.execute('DELETE FROM annotations WHERE file_path=?', t)
          self.library.cursor.execute('DELETE FROM sequences WHERE file_path=?', t)
          self.library.cursor.execute('DELETE FROM languages WHERE file_path=?', t)
          self.library.cursor.execute('DELETE FROM image_formats WHERE file_path=?', t)
          self.library.cursor.execute('DELETE FROM genres WHERE file_path=?', t)
        
        coverpage, book_title, publish_date, publisher, authors, genres, sequence, annotation, languages, characters, pages, license, has_frames, im_formats, sequences, langs, formats = self.load_file(filename, show_dialog)

        if book_title == {}:
          return False

        t = (filename, coverpage, publish_date, publisher, authors,
             characters, pages, license, rating, str(has_frames), 'False')
        self.library.cursor.execute('INSERT INTO books VALUES (?,?,?,?,?,?,?,?,?,?,?)', t)

        for title in list(book_title.items()):
          t = (filename, title[0], title[1])
          self.library.cursor.execute('INSERT INTO titles VALUES (?,?,?)', t)

        for anno in list(annotation.items()):
          t = (filename, anno[0], anno[1])
          self.library.cursor.execute('INSERT INTO annotations VALUES (?,?,?)', t)

        for seq in sequences:
          t = (filename, seq[0], seq[1])
          self.library.cursor.execute('INSERT INTO sequences VALUES (?,?,?)', t)

        for lang in langs:
          t = (filename, lang[0], lang[1])
          self.library.cursor.execute('INSERT INTO languages VALUES (?,?,?)', t)

        for im_format in formats:
          t = (filename, im_format)
          self.library.cursor.execute('INSERT INTO image_formats VALUES (?,?)', t)

        if len(genres) < 1:
          t = (filename, 'unknown', None)
          self.library.cursor.execute('INSERT INTO genres VALUES (?,?,?)', t)
        else:
          for genre in list(genres.items()):
            t = (filename, genre[0], genre[1])
            self.library.cursor.execute('INSERT INTO genres VALUES (?,?,?)', t)

        self.library.conn.commit()
        
        return True

    def load_file(self, in_filename, show_dialog):
        prepared_file = fileprepare.FilePrepare(self, in_filename, self._window.library_dir, show_dialog)
        filename = prepared_file.filename
        self.tempdir = self._window.library_dir
        acbf_document = acbfdocument.ACBFDocument(self, filename)

        if not acbf_document.valid:
          return None, None, None, None, None, None, None, None, None, None, None, None

        # coverpage
        coverpage = acbf_document.coverpage
        coverpage.thumbnail((int(coverpage.size[0]*150/float(coverpage.size[1])),150), Image.NEAREST)
        output_directory = os.path.join(os.path.join(constants.CONFIG_DIR, 'Covers'), acbf_document.book_title[list(acbf_document.book_title.items())[0][0]][0].upper())
        if not os.path.exists(output_directory):
          os.makedirs(output_directory, 0o700)

        cover_number = 0
        for root, dirs, files in os.walk(output_directory):
          for f in files:
            if f[-4:].upper() == '.PNG' and f[:-4].isdigit():
              if cover_number < int(f[:-4]):
                cover_number = int(f[:-4])
        cover_filename = os.path.join(output_directory, str(cover_number + 1) + '.png')
        
        output = io.BytesIO()
        coverpage.save(output, "PNG")
        coverpage_base64 = base64.b64encode(output.getvalue())
        output.close()
        coverpage.save(cover_filename, "PNG")

        # sequences
        sequences = ''
        for sequence in acbf_document.sequences:
          sequences = sequences + sequence[0] + ' (' + sequence[1] + '), '
        sequences = sequences[:-2]

        # publish-date 
        if acbf_document.publish_date_value != '':
          publish_date = acbf_document.publish_date_value
        else:
          publish_date = '9999-01-01'

        # languages
        languages = ''
        for language in acbf_document.languages:
          if language[1] == 'FALSE' and language[0] == '??':
            languages = languages + '??(no text layer), '
          elif language[1] == 'FALSE':
            languages = languages + language[0] + '(no text layer), '
          else:
            languages = languages + language[0] + ', '
        languages = languages[:-2]

        # image formats
        image_formats = []
        for page in acbf_document.pages:
          im_format = page.find("image").get("href")[-4:].upper().strip('.')
          if im_format not in image_formats:
            image_formats.append(im_format)
        im_formats_str = str(image_formats)[1:][:-1].replace("u'", "").replace("'", "")

        # clear library temp directory
        for root, dirs, files in os.walk(self._window.library_dir):
          for f in files:
            os.unlink(os.path.join(root, f))
          for d in dirs:
            shutil.rmtree(os.path.join(root, d))

        return cover_filename, acbf_document.book_title, publish_date, acbf_document.publisher, \
               acbf_document.authors, acbf_document.genres_dict, sequences, acbf_document.annotation, \
               languages, acbf_document.characters, acbf_document.pages_total, acbf_document.license, \
               acbf_document.has_frames, im_formats_str, acbf_document.sequences, acbf_document.languages, \
               image_formats

    
class Library():

  def __init__(self):
      self.library_file_path = os.path.join(constants.CONFIG_DIR, 'library.xml')
      self.library_db_path = os.path.join(constants.CONFIG_DIR, 'library.db');
      self.load_library()
      
  def load_library(self):
      #migrate from old xml library
      if os.path.isfile(self.library_file_path) and not os.path.isfile(self.library_db_path):
        self.conn = sqlite3.connect(self.library_db_path)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE books
             (file_path TEXT PRIMARY KEY, coverpage TEXT, publish_date TEXT, publisher TEXT, authors TEXT,
              characters TEXT, pages INTEGER, license TEXT, rating INTEGER, has_frames TEXT, finished TEXT)''')
        self.cursor.execute('''CREATE TABLE titles
             (file_path TEXT, lang TEXT, title TEXT, PRIMARY KEY (file_path, lang))''')
        self.cursor.execute('''CREATE TABLE annotations
             (file_path TEXT, lang TEXT, annotation TEXT, PRIMARY KEY (file_path, lang))''')
        self.cursor.execute('''CREATE TABLE sequences
             (file_path TEXT, sequence_title TEXT, sequence_number INTEGER, PRIMARY KEY (file_path, sequence_title))''')
        self.cursor.execute('''CREATE TABLE languages
             (file_path TEXT, lang TEXT, show TEXT)''')
        self.cursor.execute('''CREATE TABLE image_formats
             (file_path TEXT, format TEXT)''')
        self.cursor.execute('''CREATE TABLE genres
             (file_path TEXT, genre TEXT, perc INTEGER)''')
        self.cursor.execute('''CREATE TABLE library_info
             (item TEXT, value TEXT)''')
        t = [('genre_counts', 'x'), ('rating_counts', 'x'), ('language_counts', 'x'), ('publish_date_counts', 'x'), ('publisher_counts', 'x'),
             ('library_folder_size', '0'), ('genre_chart', 'x'), ('rating_chart', 'x'), ('language_chart', 'x'), ('publish_date_chart', 'x'),
             ('publisher_chart', 'x')]
        self.cursor.executemany('''INSERT INTO library_info VALUES (?, ?)''', t)
          
        self.conn.commit()

        self.tree = xml.parse(source = self.library_file_path).getroot()
        for book in self.tree.findall("book"):
          try:
            file_path = book.get("path")
            coverpage = get_element_text2(book, "coverpage")
            publish_date = get_element_text2(book, "publish_date")
            publisher = get_element_text2(book, "publisher")
            authors = get_element_text2(book, "authors")
            characters = get_element_text2(book, "characters")
            pages = int(get_element_text2(book, "pages"))
            license = get_element_text2(book, "license")
            rating = int(get_element_text2(book, "rating"))
            has_frames = get_element_text2(book, "has_frames")
            finished = get_element_text2(book, "read")

            t = (file_path, coverpage, publish_date, publisher, authors, characters, pages, license, rating, has_frames, finished)
            self.cursor.execute('''INSERT INTO books VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', t)

            t = []
            for title in book.findall("title"):
              t.append((file_path, title.get("lang"), title.text))
            self.cursor.executemany('''INSERT INTO titles VALUES (?, ?, ?)''', t)

            t = []
            for anno in book.findall("annotation"):
              t.append((file_path, anno.get("lang"), anno.text))
            self.cursor.executemany('''INSERT INTO annotations VALUES (?, ?, ?)''', t)

            t = []
            for sequence in get_element_text2(book, "sequence").split(', '):
              if sequence != '':
                t.append((file_path, unescape(sequence[:sequence.rfind('(') - 1]), sequence[sequence.rfind('(') + 1 : sequence.rfind(')')]))
            self.cursor.executemany('''INSERT INTO sequences VALUES (?, ?, ?)''', t)

            t = []
            for language in get_element_text2(book, "languages").split(', '):
              if language != '':
                t.append((file_path, language[0:2], str(len(language) == 2).upper()))
            self.cursor.executemany('''INSERT INTO languages VALUES (?, ?, ?)''', t)

            t = []
            for im_format in get_element_text2(book, "im_formats").split(', '):
              if im_format != '':
                t.append((file_path, im_format))
            self.cursor.executemany('''INSERT INTO image_formats VALUES (?, ?)''', t)

            t = []
            if get_element_text2(book, "genres") == '':
              t.append((file_path, 'unknown'))
            for genre in get_element_text2(book, "genres").split(', '):
              if genre != '':
                t.append((file_path, genre, None))
            self.cursor.executemany('''INSERT INTO genres VALUES (?, ?, ?)''', t)
          
            self.conn.commit()
          except Exception as inst:
            print("Failed to insert book: %s" % book.get("path"))
            print("Exception: %s" % inst)
            self.conn.rollback()
        
      #use library db
      elif os.path.isfile(self.library_db_path):
        self.conn = sqlite3.connect(self.library_db_path)
        self.cursor = self.conn.cursor()
        try:
          self.cursor.execute('''ALTER TABLE genres ADD perc INTEGER''')
          self.conn.commit()
        except:
          None
        """for row in self.cursor.execute('SELECT * FROM books '):
          print row
        for row in  self.cursor.execute('SELECT * FROM titles'):
          print row
        for row in  self.cursor.execute('SELECT * FROM annotations'):
          print row
        for row in  self.cursor.execute('SELECT * FROM sequences'):
          print row
        for row in  self.cursor.execute("SELECT * FROM languages"):
          print row
        for row in  self.cursor.execute('SELECT * FROM image_formats'):
          print row
        for row in  self.cursor.execute('SELECT * FROM genres'):
          print row
        for row in  self.cursor.execute('SELECT item, substr(value, 1, 20) FROM library_info'):
          print row"""
        
      #create new library db
      else:
        self.conn = sqlite3.connect(self.library_db_path)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE books
             (file_path TEXT PRIMARY KEY, coverpage TEXT, publish_date TEXT, publisher TEXT, authors TEXT,
              characters TEXT, pages INTEGER, license TEXT, rating INTEGER, has_frames TEXT, finished TEXT)''')
        self.cursor.execute('''CREATE TABLE titles
             (file_path TEXT, lang TEXT, title TEXT, PRIMARY KEY (file_path, lang))''')
        self.cursor.execute('''CREATE TABLE annotations
             (file_path TEXT, lang TEXT, annotation TEXT, PRIMARY KEY (file_path, lang))''')
        self.cursor.execute('''CREATE TABLE sequences
             (file_path TEXT, sequence_title TEXT, sequence_number INTEGER, PRIMARY KEY (file_path, sequence_title))''')
        self.cursor.execute('''CREATE TABLE languages
             (file_path TEXT, lang TEXT, show TEXT)''')
        self.cursor.execute('''CREATE TABLE image_formats
             (file_path TEXT, format TEXT)''')
        self.cursor.execute('''CREATE TABLE genres
             (file_path TEXT, genre TEXT, perc INTEGER)''')
        self.cursor.execute('''CREATE TABLE library_info
             (item TEXT, value TEXT)''')
        t = [('genre_counts', 'x'), ('rating_counts', 'x'), ('language_counts', 'x'), ('publish_date_counts', 'x'), ('publisher_counts', 'x'),
             ('library_folder_size', '0'), ('genre_chart', 'x'), ('rating_chart', 'x'), ('language_chart', 'x'), ('publish_date_chart', 'x'),
             ('publisher_chart', 'x')]
        self.cursor.executemany('''INSERT INTO library_info VALUES (?, ?)''', t)
          
        self.conn.commit()

  def delete_book(self, path):
      t = (path,)
      self.cursor.execute('DELETE FROM books WHERE file_path=?', t)
      self.cursor.execute('DELETE FROM titles WHERE file_path=?', t)
      self.cursor.execute('DELETE FROM annotations WHERE file_path=?', t)
      self.cursor.execute('DELETE FROM sequences WHERE file_path=?', t)
      self.cursor.execute('DELETE FROM languages WHERE file_path=?', t)
      self.cursor.execute('DELETE FROM image_formats WHERE file_path=?', t)
      self.cursor.execute('DELETE FROM genres WHERE file_path=?', t)
      self.conn.commit()
      return


def pil_to_pixbuf(PILImage, BGColor):
    """Return a pixbuf created from the PIL <image>."""

    bcolor = (int(gtk.gdk.color_parse(BGColor).red_float*255), int(gtk.gdk.color_parse(BGColor).green_float*255), int(gtk.gdk.color_parse(BGColor).blue_float*255))

    PILImage = PILImage.convert("RGBA")
    bg = Image.new("RGB", PILImage.size, bcolor)
    bg.paste(PILImage,PILImage)

    dummy_file = io.StringIO()
    bg.save(dummy_file, "ppm")
    contents = dummy_file.getvalue()
    dummy_file.close()

    loader = gtk.gdk.PixbufLoader("pnm")
    loader.write(contents, len(contents))
    pixbuf = loader.get_pixbuf()
    loader.close()
    return pixbuf

# function to retrieve text value from element without throwing exception
def get_element_text2(element_tree, element):
    try:
      text_value = element_tree.find(element).text
      if text_value is None:
        text_value = ''
    except:
      text_value = ''
    return text_value
