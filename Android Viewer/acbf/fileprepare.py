"""fileprepare.py - unzip and prepare file.

Copyright (C) 2011-2014 Robert Pastierovic
https://launchpad.net/~just-me
"""

# -*- coding: utf-8 -*-
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
import stat
import shutil
import zipfile
import lxml.etree as xml
from PIL import Image
import subprocess
import threading
import time
import patoolib
from kivy.app import App

try:
  from . import constants
  from . import preferences
  from . import acbfdocument
except Exception:
  import constants
  import preferences
  import acbfdocument

class FilePrepare():
    
    def __init__(self, window, filename, tempdir, prepare_type, *args):
      print("fileprepare")
      self._window = window
      self.filename = str(filename)
      self.tempdir = tempdir

      file_type = None
      if zipfile.is_zipfile(self.filename):
        file_type = 'ZIP'
      elif self.filename[-4:].upper() == 'ACBF':
        file_type = 'ACBF'
      elif self.filename[-4:].upper() == '.CBR':
        file_type = 'RAR'

      # clear temp directory
      for root, dirs, files in os.walk(self.tempdir):
        for f in files:
          os.unlink(os.path.join(root, f))
        for d in dirs:
          shutil.rmtree(os.path.join(root, d))

      if file_type == 'ACBF':
        return_filename = os.path.join(self.tempdir, os.path.basename(self.filename))
        try:
          shutil.copy(self.filename, return_filename)
        except:
          pass
        self._window.prepared_file = return_filename
      else:
        if file_type == 'ZIP':
          # extract files from CBZ into DATA_DIR
          z = zipfile.ZipFile(self.filename)
          if prepare_type == 'book':

            # thread count handling
            threads_status = App.get_running_app().config.get('general', 'threads').split(',')[0]
            threads = int(App.get_running_app().config.get('general', 'threads').split(',')[1])
            threads_count = int(App.get_running_app().config.get('general', 'threads').split(',')[2])
            threads_delay = float(App.get_running_app().config.get('general', 'threads').split(',')[3])
            #print("Threads before:", threads_status, threads, threads_count, threads_delay, len(z.namelist()))

            if (threads_status == "True" and threads_count > 5 and threads_delay > 0.1 and threads > 50):
              threads = 30
              threads_delay = threads_delay - 0.1
              threads_count = 0
            elif (threads_status == "True" and threads_count > 5):
              threads = threads + 1
              threads_count = 0
            elif (threads_status != "True" and threads >= 20):
              threads = threads - 10
              threads_count = 0
            elif threads_status != "True":
              threads_delay = threads_delay + 0.1
              threads = 30
              threads_count = 0
            elif len(z.namelist()) > threads:
              threads_count = threads_count + 1

            thread_setting = 'False,' + str(threads) + ',' + str(threads_count) + ',' + str(round(threads_delay, 1))
            #print("Threads after:", thread_setting)
            App.get_running_app().config.set('general', 'threads', thread_setting)
            App.get_running_app().config.write()

            self._window.loading_book_dialog.ids.loading_progress_bar.max = len(z.namelist())

            #extract directories first to avoid extract mkdir error in threads
            folders_inside = []
            for idx, f in enumerate(z.infolist()):
              if '/' in f.filename:
                if f.filename[:f.filename.rfind("/")] not in folders_inside:
                  folders_inside.append(f.filename[:f.filename.rfind("/")])
                  z.extract(f, self.tempdir)
            active_threads = threading.active_count()
            for idx, f in enumerate(z.namelist()):
              while threading.active_count() > threads: # keep it low
                time.sleep(threads_delay)
              t = threading.Thread(target=self.extract_file, args = (z, f, prepare_type))
              t.daemon = True
              t.start()

            while threading.active_count() > active_threads:
              time.sleep(0.5)
          else:
            zip_files = []
            metadata_file = ''
            coverpage_file = ''
            for file_in_zip in z.infolist():
              if file_in_zip.filename[-4:].upper() == 'ACBF':
                # extract ACBF
                self.extract_file(z, file_in_zip.filename, prepare_type)
                # extract coverpage
                metadata_file = str(os.path.join(self.tempdir, file_in_zip.filename))
                acbf_doc =  acbfdocument.ACBFDocument(self, metadata_file)

                try:
                  self.extract_file(z, acbf_doc.coverpage.replace(self.tempdir + '/', ''), prepare_type)
                except:
                  print("extract failed - probably internal image")

              elif file_in_zip.filename[-4:].upper() == '.XML':
                # extract XML
                self.extract_file(z, file_in_zip.filename, prepare_type)
              elif self.filename[-4:].upper() == '.ACV':
                self.extract_file(z, file_in_zip.filename, prepare_type)
            for file_in_zip in z.infolist():
              if file_in_zip.filename[-4:].upper() in ('.JPG', '.PNG', '.GIF', 'WEBP', '.BMP', 'JPEG'):
                zip_files.append(str(file_in_zip.filename))

            # extract coverpage
            if len(zip_files) > 0:
              safe_zip_files = []
              for f in zip_files:
                safe_zip_files.append(f)
              
              for f in zip_files:
                if f == sorted(safe_zip_files)[0]:
                  self.extract_file(z, f, prepare_type)

        else:
          unrar_location = None
          if file_type == 'RAR':
            print("getting unrar location ...")
            for root, dirs, files in os.walk(str(App.get_running_app().directory)):
              for f in files:
                if f == 'unrar':
                  unrar_location = os.path.abspath(os.path.join(root, f))
                  print("Unrar location:", unrar_location)
                  os.chmod(unrar_location, stat.S_IXUSR)
          try:
            print("running patool ...")
            # check if it fails on ascii/utf-8 conversion hack (unrar can't extract these and will crash whole app)
            #command = ["/data/data/org.acbf.acbfa/files/unrar/unrar", "v", self.filename]
            xx = self.filename
            #unrar_list = str(subprocess.Popen(command, stdout=subprocess.PIPE).stdout.read().decode('utf-8'))

            if unrar_location != None:
              patoolib.extract_archive(archive=xx, outdir=self.tempdir, program=unrar_location, verbosity=1)
            else:
              patoolib.extract_archive(archive=xx, outdir=self.tempdir)
          except Exception as inst:
            print("Patool exception:", inst)
            self.filename = None
            raise

        # rename to safe filenames
        #for root, dirs, files in os.walk(self.tempdir):
        #  for d in dirs:
        #    os.rename(os.path.join(root, d), os.path.join(root, d).encode('ascii', 'replace').replace('?', '_'))
        #for root, dirs, files in os.walk(self.tempdir):
        #  for f in files:
        #    os.rename(os.path.join(root, f), os.path.join(root, f).encode('ascii', 'replace').replace('?', '_'))

        # check if there's ACBF file inside
        acbf_found = False
        for datafile in os.listdir(self.tempdir):
          if datafile[-4:].upper() == 'ACBF':
            acbf_found = True
            return_filename = os.path.join(self.tempdir, datafile)

        if not acbf_found:
          # create dummy acbf file
          tree = xml.Element("ACBF", xmlns="http://www.fictionbook-lib.org/xml/acbf/1.0")
          metadata = xml.SubElement(tree, "meta-data")
          bookinfo = xml.SubElement(metadata, "book-info")
          coverpage = xml.SubElement(bookinfo, "coverpage")
          cover_image = ''
          all_files = []
          files_to_elements = {}
          publishinfo = xml.SubElement(metadata, "publish-info")
          docinfo = xml.SubElement(metadata, "document-info")
          body = xml.SubElement(tree, "body")

          if os.path.isfile(os.path.join(self.tempdir, "comic.xml")):
            is_acv_file = True
          else:
            is_acv_file = False

          if file_type == 'ZIP' and prepare_type != 'book':
            for zfile in zip_files:
              all_files.append(zfile.encode('ascii', 'replace').replace('?', '_'))
          else:
            for root, dirs, files in os.walk(self.tempdir):
              for f in files:
                all_files.append(os.path.join(root, f)[len(self.tempdir) + 1:])
          for datafile in sorted(all_files):
            if datafile[-4:].upper() in ('.JPG', '.PNG', '.GIF', 'WEBP', '.BMP', 'JPEG'):
              if cover_image == '':
                # insert coverpage
                cover_image = xml.SubElement(coverpage, "image", href=datafile)
                files_to_elements[os.path.basename(datafile)[:-4]] = cover_image
              else:
                # insert normal page
                if is_acv_file and "/" not in datafile:
                  page = xml.SubElement(body, "page")
                  image = xml.SubElement(page, "image", href=datafile)
                  files_to_elements[os.path.basename(datafile)[:-4]] = image
                elif not is_acv_file:
                  page = xml.SubElement(body, "page")
                  image = xml.SubElement(page, "image", href=datafile)

          # check for ACV's comic.xml
          if is_acv_file:
            acv_tree = xml.parse(source = os.path.join(self.tempdir, "comic.xml"))

            if acv_tree.getroot().get("bgcolor") != None:
              body.set("bgcolor", acv_tree.getroot().get("bgcolor"))

            if acv_tree.getroot().get("title") != None:
              book_title = xml.SubElement(bookinfo, "book-title")
              book_title.text = acv_tree.getroot().get("title")

            images = acv_tree.find("images")
            pattern_length = len(images.get("indexPattern"))
            pattern_format = images.get("namePattern").replace("@index", "%%0%dd" % pattern_length)
            for screen in acv_tree.findall("screen"):
              element = files_to_elements[pattern_format % int(screen.get("index"))]
              xsize, ysize = Image.open(os.path.join(self.tempdir, element.get('href'))).size
              for frame in screen:
                x1, y1, w, h = map(float, frame.get("relativeArea").split(" "))
                ix1 = int(xsize * x1)
                ix2 = int(xsize * (x1 + w))
                iy1 = int(ysize * y1)
                iy2 = int(ysize * (y1 + h))
                envelope = "%d,%d %d,%d %d,%d %d,%d" % (ix1, iy1, ix2, iy1, ix2, iy2, ix1, iy2)
                frame_elt = xml.SubElement(element.getparent(), "frame", points=envelope)
                if frame.get("bgcolor") != None:
                  frame_elt.set("bgcolor", frame.get("bgcolor"))

          # check if there's ComicInfo.xml file inside
          elif os.path.isfile(os.path.join(self.tempdir, "ComicInfo.xml")):
            # load comic book information from ComicInfo.xml
            comicinfo_tree = xml.parse(source = os.path.join(self.tempdir, "ComicInfo.xml"))

            for author in ["Writer", "Penciller", "Inker", "Colorist", "CoverArtist", "Adapter", "Letterer"]:
              if comicinfo_tree.find(author) != None:
                author_element = xml.SubElement(bookinfo, "author", activity=author)
                first_name = xml.SubElement(author_element, "first-name")
                first_name.text = comicinfo_tree.find(author).text.split(' ')[0]
                if len(comicinfo_tree.find(author).text.split(' ')) > 2:
                  middle_name = xml.SubElement(author_element, "middle-name")
                  middle_name.text = ''
                  for i in range(len(comicinfo_tree.find(author).text.split(' '))):
                    if i > 0 and i < (len(comicinfo_tree.find(author).text.split(' ')) - 1):
                      middle_name.text = middle_name.text + ' ' + comicinfo_tree.find(author).text.split(' ')[i]
                last_name = xml.SubElement(author_element, "last-name")
                last_name.text = comicinfo_tree.find(author).text.split(' ')[-1]

            if comicinfo_tree.find("Title") != None:
              book_title = xml.SubElement(bookinfo, "book-title")
              book_title.text = comicinfo_tree.find("Title").text

            if comicinfo_tree.find("Genre") != None:
              for one_genre in comicinfo_tree.find("Genre").text.split(', '):
                genre = xml.SubElement(bookinfo, "genre")
                genre.text = comicinfo_tree.find("Genre").text

            if comicinfo_tree.find("Characters") != None:
              characters = xml.SubElement(bookinfo, "characters")
              for character in comicinfo_tree.find("Characters").text.split(', '):
                name = xml.SubElement(characters, "name")
                name.text = character

            if comicinfo_tree.find("Series") != None:
              sequence = xml.SubElement(bookinfo, "sequence", title=comicinfo_tree.find("Series").text)
              if comicinfo_tree.find("Number") != None:
                sequence.text = comicinfo_tree.find("Number").text
              else:
                sequence.text = '0'

            if comicinfo_tree.find("Summary") != None:
              annotation = xml.SubElement(bookinfo, "annotation")
              for text_line in comicinfo_tree.find("Summary").text.split("\n"):
                if text_line != '':
                  paragraph = xml.SubElement(annotation, "p")
                  paragraph.text = text_line

            if comicinfo_tree.find("LanguageISO") != None:
              languages = xml.SubElement(bookinfo, "languages")
              language = xml.SubElement(languages, "text-layer", lang=comicinfo_tree.find("LanguageISO").text, show="False")

            if comicinfo_tree.find("Year") != None and comicinfo_tree.find("Month") != None and comicinfo_tree.find("Day") != None:
              publish_date = comicinfo_tree.find("Year").text + "-" + comicinfo_tree.find("Month").text + "-" + comicinfo_tree.find("Day").text
              publish_date = xml.SubElement(publishinfo, "publish-date", value=publish_date)
              publish_date.text = comicinfo_tree.find("Year").text

            if comicinfo_tree.find("Publisher") != None:
             publisher = xml.SubElement(publishinfo, "publisher")
             publisher.text = comicinfo_tree.find("Publisher").text

          # save generated acbf file
          return_filename = os.path.join(self.tempdir, os.path.splitext(os.path.basename(self.filename))[0] + '.acbf')
          f = open(return_filename, 'w')
          f.write(xml.tostring(tree, encoding='unicode', pretty_print=True))
          f.close()

        self._window.prepared_file = return_filename

    def extract_file(self, z, f, prepare_type):
        z.extract(f, self.tempdir)
        if prepare_type == 'book':
          self._window.loading_book_dialog.ids.loading_progress_bar.value = self._window.loading_book_dialog.ids.loading_progress_bar.value + 1
          #print(self._window.loading_book_dialog.ids.loading_progress_bar.value, '/', self._window.loading_book_dialog.ids.loading_progress_bar.max)
        #print(f, threading.active_count())

    def show_message_dialog(self, text):
        pass

