"""library_info.py - Library Info Dialog.

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
import io
import os
from matplotlib import pyplot
import base64

try:
  from . import history
  from . import constants
except Exception:
  import history
  import constants

class LibraryInfoDialog(gtk.Dialog):
    
    """Library Info dialog."""
    
    def __init__(self, window):
        self._window = window
        gtk.Dialog.__init__(self, 'Library Info', window, gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT, (gtk.STOCK_CLOSE, gtk.ResponseType.CLOSE))
        self.set_resizable(False)
        self.set_border_width(8)

        # populate variables
        self._window.library.cursor.execute('SELECT count(*) FROM books')
        total_books = self._window.library.cursor.fetchone()[0]

        self.genre_counts = [('unknown', 0), ('science_fiction', 0), ('fantasy', 0), ('adventure', 0), ('horror', 0), ('mystery', 0), ('crime', 0), ('military', 0),
                        ('real_life', 0), ('superhero', 0), ('humor', 0), ('western', 0), ('manga', 0), ('politics', 0), ('caricature', 0),
                        ('sports', 0), ('history', 0), ('biography', 0), ('education', 0), ('computer', 0), ('religion', 0), ('romance', 0),
                        ('children', 0), ('non-fiction', 0), ('adult', 0), ('alternative', 0), ('other', 0)]
        self.rating_counts = [('0', 0), ('1', 0), ('2', 0), ('3', 0), ('4', 0), ('5', 0)]
        self.language_counts = []
        for language in self._window.languages[1:]:
          self.language_counts.append((language, 0))
        self.publish_date_counts = [('Unknown', 0)]
        for publishdate in self._window.publishdates[1:]:
          if publishdate != '9999':
            self.publish_date_counts.append((publishdate, 0))
        self.publisher_counts = []
        self.publisher_max = 0
        for publisher in self._window.publishers[1:]:
          self.publisher_counts.append((publisher, 0))
          if len(publisher) > self.publisher_max:
            self.publisher_max = len(publisher)

        # get counts from db
        for row in self._window.library.cursor.execute('SELECT genre, sum(perc) \
                                                        FROM (SELECT genre, ifnull(cast(perc as real) / 100, \
                                                                                   1 / cast((SELECT count(*) \
                                                                                             FROM genres c \
			                                                                     WHERE c.file_path = m.file_path) as Real)) perc \
                                                              FROM genres m) \
                                                        GROUP BY genre \
                                                        ORDER BY sum(perc) DESC'):
          for idx, genre_item in enumerate(self.genre_counts):
            if genre_item[0] == row[0]:
              self.genre_counts[idx] = (genre_item[0], int(round(row[1], 0)))
        self.genre_counts = sorted(self.genre_counts,key=lambda x: x[1], reverse=True)

        for row in self._window.library.cursor.execute('SELECT rating, count(*) FROM books GROUP BY rating'):
          for idx, rating_item in enumerate(self.rating_counts):
            if rating_item[0] == str(row[0]):
              self.rating_counts[idx] = (rating_item[0], row[1])
        self.rating_counts = sorted(self.rating_counts,key=lambda x: x[1], reverse=True)

        for row in self._window.library.cursor.execute("SELECT lang || CASE WHEN show='FALSE' THEN '(no text layer)' ELSE '' END, count(*) \
                                                        FROM languages \
                                                        GROUP BY lang || CASE WHEN show='FALSE' THEN '(no text layer)' ELSE '' END"):
          for idx, language_item in enumerate(self.language_counts):
            if language_item[0] == row[0]:
              self.language_counts[idx] = (language_item[0], row[1])
        self.language_counts = sorted(self.language_counts,key=lambda x: x[1], reverse=True)

        for row in self._window.library.cursor.execute('SELECT substr(publish_date, 1, 4), count(*) FROM books GROUP BY substr(publish_date, 1, 4)'):
          for idx, publish_date_item in enumerate(self.publish_date_counts):
            if row[0] == '9999':
              self.publish_date_counts[0] = (self.publish_date_counts[0][0], row[1])
            elif publish_date_item[0] == row[0]:
              self.publish_date_counts[idx] = (publish_date_item[0], row[1])
        self.publish_date_counts = sorted(self.publish_date_counts,key=lambda x: x[0], reverse=False)

        for row in self._window.library.cursor.execute("SELECT publisher, count(*) FROM books GROUP BY publisher"):
          for idx, publisher_item in enumerate(self.publisher_counts):
            if publisher_item[0] == row[0]:
              self.publisher_counts[idx] = (publisher_item[0], row[1])
        self.publisher_counts = sorted(self.publisher_counts,key=lambda x: x[1], reverse=True)

        # get counts from library info
        for row in self._window.library.cursor.execute("SELECT item, value FROM library_info"):
          if row[0] == 'genre_counts':
            l_genre_counts = row[1]
          if row[0] == 'rating_counts':
            l_rating_counts = row[1]
          if row[0] == 'language_counts':
            l_language_counts = row[1]
          if row[0] == 'publish_date_counts':
            l_publish_date_counts = row[1]
          if row[0] == 'publisher_counts':
            l_publisher_counts = row[1]


        ## Library refresh if necessary
        if (str(self.genre_counts) != l_genre_counts or str(self.rating_counts) != l_rating_counts or
            str(self.language_counts) != l_language_counts or str(self.publish_date_counts) != l_publish_date_counts or
            str(self.publisher_counts) != l_publisher_counts
           ):

          message = gtk.Dialog('Refreshing library statistics ...', parent=self, flags = gtk.DialogFlags.MODAL | gtk.DialogFlags.DESTROY_WITH_PARENT)
          message.set_resizable(False)
          message.set_border_width(8)
          message.set_size_request(300, 100)
          message.show_all()
          while gtk.events_pending():
            gtk.main_iteration()
          self.refresh_library_info()
          message.destroy()

        ## Window
        notebook = gtk.Notebook()
        self.vbox.pack_start(notebook, False, False, 0)
        notebook.set_border_width(3)


        ## General Stats
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        scrolled.set_size_request(580, 400)
        tab = gtk.VBox(False, 0)
        tab.set_border_width(5)
        scrolled.add_with_viewport(tab)

        self.history = history.History()

        self._window.library.cursor.execute("SELECT count(*) FROM books WHERE finished = 'True'")
        read_books = self._window.library.cursor.fetchone()[0]

        self._window.library.cursor.execute("SELECT value FROM library_info WHERE item = 'library_folder_size'")
        library_folder_size = self._window.library.cursor.fetchone()[0]
        library_file_size = round(float(os.path.getsize(self._window.library.library_db_path))/1024/1024, 2)

        label = gtk.Label()
        label_markup = '<big><b>General Library Information</b></big>\n\n'
        label_markup = label_markup + '<b>Number of books: </b>' + str(total_books) + ' (' + '%.2f' % round(float(read_books)/total_books*100, 2) + '% finished reading)\n'
        label_markup = label_markup + '<b>Library Disk Size</b>: ' + str(round(library_file_size + float(library_folder_size), 2)) + ' MB (metadata ' + str(library_file_size) + ' MB, covers ' + str(library_folder_size) + ' MB)\n\n'
        label_markup = label_markup + '<b>' + str(len(self._window.publishers) - 1) + '</b> different publishers\n'
        label_markup = label_markup + '<b>' + str(len(self._window.publishdates) - 1) + '</b> different years of publication\n'
        label_markup = label_markup + '<b>' + str(len(self._window.genres) - 2) + '</b> different genres\n'
        label_markup = label_markup + '<b>' + str(len(self._window.series) - 1) + '</b> comic book series\n'
        label_markup = label_markup + '<b>' + str(len(self._window.languages) - 2) + '</b> different language layers\n'
        label_markup = label_markup + '<b>' + str(len(self._window.licenses) - 1) + '</b> licenses\n'
        label.set_markup(label_markup)
        label.set_alignment(0, 0)
        tab.pack_start(label, False, False, 0)

        notebook.insert_page(scrolled, gtk.Label('General'), -1)

        ## Genres
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)
        scrolled.add_with_viewport(hbox)

        # genres chart
        chart_image_png = self.get_png_chart("genre_chart")
        chart_image = gtk.Image()
        chart_image.set_from_pixbuf(chart_image_png)
        canvas_alignment = gtk.Alignment(xalign=0, yalign=0, xscale=0.0, yscale=0.0)
        canvas_alignment.add(chart_image)
        hbox.pack_start(canvas_alignment, True, True, 10)

        label_markup = ''
        for genre_item in self.genre_counts:
          label_markup = label_markup + '<small><tt><i>' + genre_item[0] + '</i> ' + (' ' + str(genre_item[1])).rjust(22 - len(genre_item[0]), '.') + '</tt></small>\n'

        label = gtk.Label()
        label.set_markup(label_markup)
        label.set_alignment(0, 0)
        label.set_line_wrap(False)
        hbox.pack_start(label, True, True, 10)

        notebook.insert_page(scrolled, gtk.Label('Genres'), -1)

        ## Ratings
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)
        scrolled.add_with_viewport(hbox)

        # ratings chart
        chart_image_png = self.get_png_chart("rating_chart")
        chart_image = gtk.Image()
        chart_image.set_from_pixbuf(chart_image_png)
        canvas_alignment = gtk.Alignment(xalign=0, yalign=0, xscale=0.0, yscale=0.0)
        canvas_alignment.add(chart_image)
        hbox.pack_start(canvas_alignment, True, True, 10)

        label_markup = '\n'
        for rating_item in self.rating_counts:
          rating = ''
          for i in range(int(rating_item[0])):
            rating = rating + '*'
          if rating == '':
            rating = 'Without rating'

          label_markup = label_markup + '<small><tt><i>' + rating + '</i> ' + str(rating_item[1]).rjust(18 - len(rating), '.') + '</tt></small>\n'

        label = gtk.Label()
        label.set_markup(label_markup)
        label.set_alignment(0, 0)
        label.set_line_wrap(False)
        hbox.pack_start(label, True, True, 10)

        notebook.insert_page(scrolled, gtk.Label('Book Ratings'), -1)

        ## Publish Dates
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)
        scrolled.add_with_viewport(hbox)

        # publish dates chart
        chart_image_png = self.get_png_chart("publish_date_chart")
        chart_image = gtk.Image()
        chart_image.set_from_pixbuf(chart_image_png)
        canvas_alignment = gtk.Alignment(xalign=0, yalign=0, xscale=0.0, yscale=0.0)
        canvas_alignment.add(chart_image)
        hbox.pack_start(canvas_alignment, True, True, 10)

        self.publish_date_counts = sorted(self.publish_date_counts,key=lambda x: x[1], reverse=True)
        label_markup = ''
        for publish_date_item in self.publish_date_counts:
          label_markup = label_markup + '<small><tt><i>' + publish_date_item[0] + '</i> ' + str(publish_date_item[1]).rjust(9 - len(publish_date_item[0]), '.') + '</tt></small>\n'

        label = gtk.Label()
        label.set_markup(label_markup)
        label.set_alignment(0, 0)
        label.set_line_wrap(False)
        hbox.pack_start(label, True, True, 20)

        notebook.insert_page(scrolled, gtk.Label('Publish Dates'), -1)

        ## Publishers
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)
        scrolled.add_with_viewport(hbox)

        # publishers chart
        chart_image_png = self.get_png_chart("publisher_chart")
        chart_image = gtk.Image()
        chart_image.set_from_pixbuf(chart_image_png)
        canvas_alignment = gtk.Alignment(xalign=0, yalign=0, xscale=0.0, yscale=0.0)
        canvas_alignment.add(chart_image)
        hbox.pack_start(canvas_alignment, True, True, 10)

        self.publisher_counts = sorted(self.publisher_counts,key=lambda x: x[1], reverse=True)
        label_markup = ''
        for publisher_item in self.publisher_counts:
          label_markup = label_markup + '<small><tt><i>' + publisher_item[0] + '</i> ' + str(publisher_item[1]).rjust(self.publisher_max + 4 - len(publisher_item[0]), '.') + '</tt></small>\n'

        label = gtk.Label()
        label.set_markup(label_markup)
        label.set_alignment(0, 0)
        label.set_line_wrap(False)
        hbox.pack_start(label, True, True, 10)

        notebook.insert_page(scrolled, gtk.Label('Publishers'), -1)

        ## Languages
        scrolled = gtk.ScrolledWindow()
        scrolled.set_policy(gtk.PolicyType.NEVER, gtk.PolicyType.AUTOMATIC)
        hbox = gtk.HBox(False, 0)
        hbox.set_border_width(5)
        scrolled.add_with_viewport(hbox)

        # languages chart
        chart_image_png = self.get_png_chart("language_chart")
        chart_image = gtk.Image()
        chart_image.set_from_pixbuf(chart_image_png)
        canvas_alignment = gtk.Alignment(xalign=0, yalign=0, xscale=0.0, yscale=0.0)
        canvas_alignment.add(chart_image)
        hbox.pack_start(canvas_alignment, True, True, 10)

        label_markup = '\n'
        for language_item in self.language_counts:
          label_markup = label_markup + '<small><tt><i>' + language_item[0] + '</i> ' + str(language_item[1]).rjust(23 - len(language_item[0]), '.') + '</tt></small>\n'

        label = gtk.Label()
        label.set_markup(label_markup)
        label.set_alignment(0, 0)
        label.set_line_wrap(False)
        hbox.pack_start(label, True, True, 10)

        notebook.insert_page(scrolled, gtk.Label('Languages'), -1)

        # show it
        self.show_all()

        self.run()
        self.destroy()

    def get_png_chart(self, chart_name):
        self._window.library.cursor.execute("SELECT value FROM library_info WHERE item = ?", (chart_name, ))
        chart_image_png = base64.b64decode(self._window.library.cursor.fetchone()[0])
        #base64.encodebytes(dummy_file.getvalue()).decode()
        loader = GdkPixbuf.PixbufLoader()
        loader.write(chart_image_png)
        pixbuf = loader.get_pixbuf()
        loader.close()

        return pixbuf.scale_simple(int(pixbuf.get_width()*0.9), int(pixbuf.get_height()*0.9), GdkPixbuf.InterpType.BILINEAR).add_alpha(True, 255, 255, 255)

    def refresh_library_info(self):
        # general stats
        library_folder_size = get_folder_size(os.path.join(constants.CONFIG_DIR, 'Covers'))
        self._window.library.cursor.execute("UPDATE library_info SET value=? WHERE item='library_folder_size'", (library_folder_size, ))
        self._window.library.conn.commit()

        # genres chart
        labels = []
        fracs = []
        explode = [0.10, 0.08, 0.06]
        for idx, genre_item in enumerate(self.genre_counts):
          if idx < 6:
            labels.append(genre_item[0])
          else:
            labels.append('')
          fracs.append(genre_item[1])
          explode.append(0)
        explode.pop()
        explode.pop()
        explode.pop()

        self._window.library.cursor.execute("UPDATE library_info SET value=? WHERE item='genre_counts'", (str(self.genre_counts), ))
        self._window.library.cursor.execute("UPDATE library_info SET value=? WHERE item='genre_chart'", (self.draw_pie_chart(labels, fracs, explode, 'Genres Distribution'), ))
        self._window.library.conn.commit()

        # ratings chart
        labels = []
        fracs = []
        explode = [0.10, 0.08, 0.06]
        for idx, rating_item in enumerate(self.rating_counts):
          rating = ''
          for i in range(int(rating_item[0])):
            rating = rating + '*'
          if rating == '':
            rating = 'Without rating'
          labels.append(rating)
          fracs.append(rating_item[1])
          explode.append(0)
        explode.pop()
        explode.pop()
        explode.pop()

        self._window.library.cursor.execute("UPDATE library_info SET value=? WHERE item='rating_counts'", (str(self.rating_counts), ))
        self._window.library.cursor.execute("UPDATE library_info SET value=? WHERE item='rating_chart'", (self.draw_pie_chart(labels, fracs, explode, 'Book Ratings Distribution'), ))
        self._window.library.conn.commit()

        # languages chart
        labels = []
        fracs = []
        explode = [0.10, 0.08, 0.06]
        for idx, language_item in enumerate(self.language_counts):
          if idx < 5:
            labels.append(language_item[0])
          else:
            labels.append('')
          fracs.append(language_item[1])
          explode.append(0)
        explode.pop()
        explode.pop()
        explode.pop()

        self._window.library.cursor.execute("UPDATE library_info SET value=? WHERE item='language_counts'", (str(self.language_counts), ))
        self._window.library.cursor.execute("UPDATE library_info SET value=? WHERE item='language_chart'", (self.draw_pie_chart(labels, fracs, explode, 'Languages Distribution'), ))
        self._window.library.conn.commit()

        # publish dates chart
        names = []
        values = []
        for idx, publish_date_item in enumerate(self.publish_date_counts):
          names.append(publish_date_item[0])
          values.append(publish_date_item[1])

        self._window.library.cursor.execute("UPDATE library_info SET value=? WHERE item='publish_date_counts'", (str(self.publish_date_counts), ))
        self._window.library.cursor.execute("UPDATE library_info SET value=? WHERE item='publish_date_chart'", (self.draw_bar_chart(names, values, 'Publish Dates Distribution'), ))
        self._window.library.conn.commit()

        # publishers chart
        names = []
        values = []
        for idx, publisher_item in enumerate(self.publisher_counts):
          names.append(publisher_item[0])
          values.append(publisher_item[1])

        self._window.library.cursor.execute("UPDATE library_info SET value=? WHERE item='publisher_counts'", (str(self.publisher_counts), ))
        self._window.library.cursor.execute("UPDATE library_info SET value=? WHERE item='publisher_chart'", (self.draw_bar_chart(names, values, 'Publishers Distribution'), ))
        self._window.library.conn.commit()

    def draw_pie_chart(self, labels, fracs, explode, title):
        pyplot.clf()
        f = pyplot.figure(1, figsize=(6,6))
        ax = f.add_subplot(111)

        patches, texts, autotexts = ax.pie(fracs, labels=labels, explode=explode, autopct='%1.1f%%', shadow=True, labeldistance=1.1)
        ax.set_title(title, fontsize=20);

        for patch in patches:
          patch.set_edgecolor('None')

        for idx, text in enumerate(autotexts):
          if idx > 5:
            text.set_text('')
          else:
            text.set_fontsize(15)

        for text in texts:
          text.set_fontsize(15)

        dummy_file = io.BytesIO()
        pyplot.savefig(dummy_file, format="png", bbox_inches='tight', transaparent=True)
        contents = base64.encodebytes(dummy_file.getvalue()).decode()
        dummy_file.close()

        return contents


    def draw_bar_chart(self, names, values, title):
        pyplot.clf()
        f = pyplot.figure(1, figsize=(6,6))
        ax = f.add_subplot(111)

        skip_ticks = int(len(names)/20) + 1

        ax.bar(list(range(len(names))), values)
        ax.set_xticks(list(range(0, len(names), skip_ticks)))
        ax.set_xticklabels(names[0::skip_ticks])
        ax.set_title(title, fontsize=20);

        f.autofmt_xdate(rotation=50)

        dummy_file = io.BytesIO()
        pyplot.savefig(dummy_file, format="png", bbox_inches='tight', transaparent=True)
        contents = base64.encodebytes(dummy_file.getvalue()).decode()
        dummy_file.close()

        return contents

def get_folder_size(folder_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return round(float(total_size/1024/1024), 2)

def get_element_text2(element_tree, element):
    try:
      text_value = element_tree.find(element).text
      if text_value is None:
        text_value = ''
    except:
      text_value = ''
    return text_value
