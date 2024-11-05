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

__version__ = '1.21'

import os
import kivy
kivy.require('2.1.0')

from kivy.app import App
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.scatter import Scatter
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.settings import SettingsWithTabbedPanel
from kivy.uix.settings import SettingItem
from kivy.uix.settings import Settings
from kivy.uix.settings import SettingOptions
from kivy.uix.settings import SettingPath
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.modalview import ModalView
from kivy.uix.popup import Popup
from kivy.animation import Animation
from kivy.base import EventLoop
from kivy.properties import NumericProperty, ListProperty, ObjectProperty, StringProperty
from kivy.graphics import Color, Rectangle, Mesh
from functools import partial
from kivy.graphics.opengl_utils import gl_register_get_size
from kivy.graphics.opengl import glGetIntegerv
from kivy.utils import platform
from kivy.clock import Clock

from io import StringIO
import random
import shutil
import threading
import time
import sys
from math import hypot
from xml.sax.saxutils import unescape

from acbf import acbfdocument
from acbf import constants
from acbf import fileprepare
from acbf import library
from acbf import history
from acbf import text_layer
from acbf import settingsjson

from PIL import Image as pil_image

if platform == 'android':
  from android.runnable import run_on_ui_thread
  from jnius import autoclass
  from jnius import cast
  from android import activity
  from android.permissions import request_permissions, Permission
  from androidstorage4kivy import SharedStorage
    
  PythonActivity = autoclass('org.kivy.android.PythonActivity')
  Intent = autoclass('android.content.Intent')
  Uri = autoclass('android.net.Uri')
  View = autoclass('android.view.View')
  DocumentsContract = autoclass('android.provider.DocumentsContract')
  DocumentFile = autoclass('androidx.documentfile.provider.DocumentFile')
  
  MediaStore_Images_Media_DATA = "_data"
  RESULT_LOAD_FILE = 1
else:
  print("Not running on Android ...")

class ScatterBackGroundImage(FloatLayout):
    zoom_level = NumericProperty(1) #(1 = full page, 2 = fit width, 3 = frame level)
    scroll_step = NumericProperty()
    zoom_width_top = NumericProperty()
    scatter_position = ListProperty([0,0])
    scatter_scale = NumericProperty(1)
    bg_color = ListProperty([0,0,0,1])
    image_color = ListProperty([1,1,1,1])
    pages_total = NumericProperty(1)

    def __init__(self, tempdir, config_dir, **kwargs):
        super(ScatterBackGroundImage, self).__init__(**kwargs)
        Window.bind(on_keyboard=self.hook_keyboard)
        self.default_temp_dir = tempdir
        self.base_dir = tempdir
        self.load_settings()

        print("TEMP DIR: " + self.tempdir)

        #clean up temp dir
        if os.path.isdir(self.tempdir):
          for root, dirs, files in os.walk(self.tempdir):
            for f in files:
              os.unlink(os.path.join(root, f))
            for d in dirs:
              shutil.rmtree(os.path.join(root, d))

        self.config_dir = config_dir
        self.prepared_file = None
        self.is_converting = False
        self.is_animating = False
        self.image_resize_ratio = 1
        self.page_transition = None
        self.cached_image = CachedImage(self)
        self.is_prev_page = False
        self.no_page_anim = False

        MAX_TEXTURE_SIZE = 0x0D33
        gl_register_get_size(MAX_TEXTURE_SIZE, 1)
        self.MAX_TEXTURE_SIZE = glGetIntegerv(MAX_TEXTURE_SIZE)[0]

        self.history = history.History(self.config_dir)
        self.loading_book_dialog = LoadingBookDialog()

        self.library_dir = os.path.join(config_dir, 'Library')
        if not os.path.exists(self.library_dir):
          os.makedirs(self.library_dir, 0o700)
        print('LIBRARY DIR: ', self.library_dir)
        #os.unlink('/data/user/0/org.acbf.acbfa/files/Library/library.xml')
        #shutil.rmtree('/data/user/0/org.acbf.acbfa/files/Covers')
        #print(os.listdir('/data/user/0/org.acbf.acbfa/files'))
        #print(os.listdir('/data/user/0/org.acbf.acbfa/files/Library'))
        #myfile = open('/data/user/0/org.acbf.acbfa/files/Library/library.xml')
        #print(myfile.read())
        #myfile.close()
        
        self.library = library.Library(self.library_dir)
        self.library.check_books()
        self.total_books = len(self.library.tree.findall("book"))

        self.last_touch = (0, 0)
        self.touch_move_error = max(Window.width, Window.height) / 100
        self.zoom_list = [1,2,3,2]
        self.zoom_index = 0
        self.page_number = 1
        self.frame_number = 1
        self.language_layer = 0
        self.page_color = (0, 0, 0, 0)
        self.frame_center = 0, 0

        self.really_exit = False

        self.library_dialog = ComicBookLibrary()
        self.library_dialog.icon_set = self.conf_iconset
        self.library_dialog.bind(on_dismiss=self.library_dialog.close_dialog)
        self.library_dialog.library_shown = False
        default_cover_width = max(Window.height, Window.width) / self.library_cols
        self.library_dialog.cols = int(Window.width / default_cover_width)
        current_cover_width = int(Window.width / self.library_dialog.cols)
        self.cover_height = int(current_cover_width * 1.4)

        self.anim = Animation()

        if self.total_books == 0:
          self.populate_library()

        if self.total_books > 0:
          self.filename = "x"
          self.base_dir = os.path.dirname(self.filename)
          self.acbf_document = acbfdocument.ACBFDocument(self, self.filename)
          self.ids.bg_image.source = './images/blank.png'
          self.toolbar_shown = False
          self.show_library()
          EventLoop.idle()
          self.populate_library()
        else:
          self.ids.bg_image.source = './images/default.png'
          self.filename = "./default.cbz"
          self.loading_book_dialog = LoadingBookDialog()
          self.loading_book_dialog.book_path = self.filename
          self.loading_book_dialog.ids.loading_progress_bar.value = 0
          self.loading_book_dialog.open()
          EventLoop.idle()
          self.load_book(self.filename, False)
          self.open_book()

    #@run_on_ui_thread
    def set_systemui_visibility(self, options):
    #    PythonActivity.mActivity.getWindow().getDecorView().setSystemUiVisibility(options)
        pass

    #@run_on_ui_thread
    def set_keep_screen_on(self, options):
    #    if options == '1':
    #      PythonActivity.mActivity.getWindow().addFlags(128)
    #    else:
    #      PythonActivity.mActivity.getWindow().clearFlags(128)
        pass

    def scale_to_height(self, *args):
        self.scatter_scale = Window.height / float(self.ids.bg_image.height)
        self.scatter_position = Window.width / 2 - self.ids.bg_image.width * self.scatter_scale / 2, 0

    def scale_to_width(self, *args):
        self.scatter_scale = Window.width / float(self.ids.bg_image.width)
        self.scatter_position = 0, 0 - self.ids.bg_image.height * self.scatter_scale + Window.height

    def calculate_zoom_width_top(self, *args):
        self.zoom_width_top = 0 - self.ids.bg_image.height * self.scatter_scale + Window.height

    def reposition(self, mode, *args):
        print("reposition")
        if self.library_dialog.library_shown:
          default_cover_width = max(Window.height, Window.width) / self.library_cols
          self.library_dialog.cols = int(Window.width / default_cover_width)
          current_cover_width = int(Window.width / self.library_dialog.cols)
          self.cover_height = int(current_cover_width * 1.4)
          self.refresh_library()
          EventLoop.idle()
          return

        self.calculate_zoom_width_top()

        if self.zoom_level == 1:
          if Window.width / float(Window.height) > self.ids.scatter.width / float(self.ids.scatter.height):
            self.scale_to_height()
          else:
            self.scale_to_width()
            self.scatter_position = (self.scatter_position[0], (Window.height - self.ids.scatter.height * self.scatter_scale) / 2)
        elif self.zoom_level == 2:
          if Window.width / float(Window.height) < self.ids.scatter.width / float(self.ids.scatter.height):
            self.zoom_index = 0
            self.zoom_level = 1
          self.scale_to_width()
          self.scroll_step = self.ids.bg_image.height / round(self.ids.bg_image.height / float(Window.height / 2) + 0.5, 0)

        if self.zoom_level == 3:
          self.zoom_to_frame(self.frames[self.frame_number - 1], mode)
        elif mode == 'move':
          self.ids.scatter.scale = self.scatter_scale
          self.ids.scatter.pos = self.scatter_position
        elif mode == 'animate':
          self.animate_to_pos(self.scatter_position[0], self.scatter_position[1], self.scatter_scale, self.conf_anim_dur)

        if self.zoom_level in (1,2):
            self.bg_color = [0,0,0,1]
        elif self.zoom_level == 3:
          self.frame_color = self.hex_to_rgb(self.frames[self.frame_number - 1][1])
          if self.frame_color != None:
            self.bg_color = self.frame_color
          else:
            self.bg_color = self.page_color

        #print(Window.size)

    def first_page(self, *args):
        self.no_page_anim = True
        if self.page_number != 1:
          self.frame_number = 1
          self.frame_color = self.hex_to_rgb(self.frames[self.frame_number - 1][1])
          self.jump_to_page(1)
          self.reposition('move')
          self.page_in()
        self.ids.scatter2.scale = 0.1
        self.no_page_anim = False

    def next_page(self, *args):
        if self.page_number < self.pages_total + 1:
          self.frame_number = 1
          self.frame_color = self.hex_to_rgb(self.frames[self.frame_number - 1][1])
          self.jump_to_page(self.page_number + 1)
          self.reposition('move')
          self.page_in()
        else:
          #fade out
          self.anim = Animation(opacity = 1,
                                duration=self.conf_anim_dur * 2,
                                t='out_cubic')

          self.anim.start(self.ids.last_page_notif)

          while self.anim.have_properties_to_animate(self.ids.last_page_notif):
            EventLoop.idle()

          #fade_in
          self.anim = Animation(opacity = 0,
                                duration=self.conf_anim_dur * 2,
                                t='in_cubic')
          self.anim.start(self.ids.last_page_notif)
        while self.anim.have_properties_to_animate(self.ids.bg_image):
          EventLoop.idle()
        self.ids.scatter2.scale = 0.1

    def prev_page(self, *args):
        print("prev page")
        self.is_prev_page = True
        if self.page_number > 1:
          self.jump_to_page(self.page_number - 1)
          if self.zoom_level == 3:
            self.frame_number = len(self.frames)
          else:
            self.frame_number = 1
          self.frame_color = self.hex_to_rgb(self.frames[self.frame_number - 1][1])
          self.reposition('move')
          if self.zoom_level == 2:
            self.scatter_position = (0, 0)
            self.ids.scatter.scale = self.scatter_scale
            self.ids.scatter.pos = self.scatter_position
          self.page_in()
        self.ids.scatter2.scale = 0.1

    def last_page(self, *args):
        self.no_page_anim = True
        if self.page_number < self.pages_total + 1:
          self.frame_number = 1
          self.frame_color = self.hex_to_rgb(self.frames[self.frame_number - 1][1])
          self.jump_to_page(self.pages_total + 1)
          self.reposition('move')
          self.page_in()
        self.ids.scatter2.scale = 0.1
        self.no_page_anim = False

    def go_to_page(self, widget):
        print("go_to_page")
        EventLoop.idle()
        self.no_page_anim = True
        self.contents_view.dismiss()
        EventLoop.idle()
        self.frame_number = 1
        self.frame_color = self.hex_to_rgb(self.frames[self.frame_number - 1][1])
        self.jump_to_page(int(widget.text.split('.')[-1].strip()))
        self.reposition('move')
        self.hide_toolbar()
        self.page_in()
        self.ids.scatter2.scale = 0.1
        self.no_page_anim = False

    def zoom_page(self, *args):
      self.zoom_index = self.zoom_index + 1
      if (Window.width / float(Window.height) < self.ids.scatter.width / float(self.ids.scatter.height)) and self.zoom_list[self.zoom_index] == 2:
        # skip fit with zoom level
        self.zoom_index = self.zoom_index + 1
      if self.zoom_index > len(self.zoom_list) - 1:
        self.zoom_index = 0
      if len(self.acbf_document.load_page_frames(self.page_number)) == 0 and self.zoom_list[self.zoom_index] == 3:
        # skip frame zoom level
        self.zoom_index = 0

      self.zoom_level = self.zoom_list[self.zoom_index]
      self.reposition('animate')

    def set_layer(self, widget):
        print("set_layer")
        self.no_page_anim = True
        EventLoop.idle()
        self.layer_view.dismiss()
        for idx, layer in enumerate(self.acbf_document.languages):
          if layer[1] == 'FALSE' and widget.text.endswith('#'):
            self.language_layer = idx
          elif layer[0] == widget.text:
            self.language_layer = idx
            
        self.ids.text_layer_label.text = widget.text
        self.load_page()
        self.page_in()
        self.no_page_anim = False

    def change_layer(self, *args):
        EventLoop.idle()
        if len(self.acbf_document.languages) < 2:
          return
        self.layer_view = LayersDialog()
        self.layer_view.open()
        self.layer_view.ids.layer_items.bind(minimum_height=self.layer_view.ids.layer_items.setter('height'))

        for layer in self.acbf_document.languages:
          if layer[1] == 'FALSE':
            btn = Button(text=layer[0] + '#', size_hint_y=None, height=40, on_press=self.set_layer)
          else:
            btn = Button(text=layer[0], size_hint_y=None, height=40, on_press=self.set_layer)
          self.layer_view.ids.layer_items.add_widget(btn)

    def show_contents(self, *args):
        if len(self.acbf_document.contents_table) > 0:
          self.contents_view = ContentsDialog()
          self.contents_view.open()
          self.contents_view.ids.contents_items.bind(minimum_height=self.contents_view.ids.contents_items.setter('height'))

          if len(self.acbf_document.contents_table) > self.language_layer:
            contents_lang = self.language_layer
          else:
            contents_lang = 0

          for item in self.acbf_document.contents_table[contents_lang]:
            btn = Button(text=item[0] + ' ... ' + item[1], size_hint_y=None, height=40, on_press=self.go_to_page)
            self.contents_view.ids.contents_items.add_widget(btn)

    def convert_webp(self, *args):
        print("convert_webp")
        im = pil_image.open(self.load_image).convert("RGB")
        self.load_image = os.path.join(self.tempdir, 'temp_webp.jpg')
        im.save(self.load_image,"jpeg")

    def resize_source_image(self, *args):
        print("resize_source_image")
        self.image_resize_ratio = float(self.MAX_TEXTURE_SIZE) / float(max(self.ids.bg_image.size[0], self.ids.bg_image.size[1]))
        im = pil_image.open(self.load_image)
        im.thumbnail([self.MAX_TEXTURE_SIZE, self.MAX_TEXTURE_SIZE], self.conf_resize_filter)
        self.load_image = os.path.join(self.tempdir, 'temp_resized.jpg')
        try:
          im.save(self.load_image, "JPEG")
        except:
          self.load_image = './images/default.png'
        self.ids.bg_image.source = self.load_image


    def draw_text_layer(self, *args):
        print("draw_text_layer")
        output_image = os.path.join(self.tempdir, 'temp_layer.jpg')
        self.text_layer = text_layer.TextLayer(self.load_image, self.page_number, self.acbf_document, self.language_layer, output_image,
                                               self.normal_font, self.strong_font, self.emphasis_font, self.code_font, self.commentary_font,
                                               self.sign_font, self.formal_font, self.heading_font, self.letter_font, self.audio_font,
                                               self.thought_font)
        self.load_image = output_image

    def page_out(self):
        print("page out")
        self.ids.scatter.do_scale = False
        self.ids.scatter.do_translation = False
        self.ids.scatter2.do_scale = False
        self.ids.scatter2.do_translation = False

        if self.is_prev_page:
          self.page_transition = self.acbf_document.get_page_transition(self.page_number + 1).upper()
        else:
          self.page_transition = self.acbf_document.get_page_transition(self.page_number).upper()

        while self.cached_image.is_loading:
          self.ids.loading_image.opacity = 0.2
          EventLoop.idle()

        if (self.page_transition == 'UNDEFINED' and self.conf_transition == 'Fade Out') or self.page_transition == 'FADE' or self.no_page_anim:
          #fade out
          self.anim = Animation(opacity = 0,
                                duration=self.conf_anim_dur + 0.2,
                                t='linear')

          self.anim.start(self.ids.bg_image)

          while self.anim.have_properties_to_animate(self.ids.bg_image):
            EventLoop.idle()
        elif (self.page_transition == 'UNDEFINED' and self.conf_transition == 'Blend') or self.page_transition == 'BLEND':
          #blend
          if self.ids.blend_image.source == self.ids.bg_image.source:
            self.ids.blend_image.reload()
          else:
            try:
              self.ids.blend_image.source = self.ids.bg_image.source
            except:
              self.ids.blend_image.source = './images/default.png'
          self.ids.scatter2.scale = self.ids.scatter.scale
          self.ids.scatter2.pos = self.ids.scatter.pos
          self.ids.blend_image.opacity = 1
          self.ids.bg_image.opacity = 0
        elif (self.page_transition == 'UNDEFINED' and self.conf_transition == 'Scroll Right') or self.page_transition == 'SCROLL_RIGHT':
          #scroll right
          if self.ids.blend_image.source == self.ids.bg_image.source:
            self.ids.blend_image.reload()
          else:
            try:
              self.ids.blend_image.source = self.ids.bg_image.source
            except:
              self.ids.blend_image.source = './images/default.png'
          self.ids.scatter2.scale = self.ids.scatter.scale
          self.ids.scatter2.pos = self.ids.scatter.pos
          self.ids.blend_image.opacity = 1
          self.ids.bg_image.opacity = 0
        else:
          self.ids.bg_image.opacity = 0

    def page_in(self):
        print("page in")
        self.ids.loading_image.opacity = 0

        if (self.page_transition == 'UNDEFINED' and self.conf_transition == 'Fade Out') or self.page_transition == 'FADE' or self.no_page_anim:
          #fade_in
          self.anim = Animation(opacity = 1,
                                duration=self.conf_anim_dur + 0.2,
                                t='linear')
          self.anim.start(self.ids.bg_image)
          while self.anim.have_properties_to_animate(self.ids.bg_image):
            EventLoop.idle()
        elif (self.page_transition == 'UNDEFINED' and self.conf_transition == 'Blend') or self.page_transition == 'BLEND':
          #blend
          self.anim = Animation(opacity = 1,
                                duration=self.conf_anim_dur * 2,
                                t='linear')

          self.anim2 = Animation(opacity = 0,
                                duration=self.conf_anim_dur * 3,
                                t='linear')

          self.anim.start(self.ids.bg_image)
          self.anim2.start(self.ids.blend_image)

          while self.anim.have_properties_to_animate(self.ids.bg_image):
            EventLoop.idle()
          while self.anim2.have_properties_to_animate(self.ids.blend_image):
            EventLoop.idle()
        elif (self.page_transition == 'UNDEFINED' and self.conf_transition == 'Scroll Right') or self.page_transition == 'SCROLL_RIGHT':
          #scroll right
          self.ids.bg_image.opacity = 1

          if self.is_prev_page:
            self.ids.scatter.pos = (self.ids.scatter.pos[0] - Window.size[0], self.ids.scatter.pos[1])
            self.anim = Animation(x=self.ids.scatter.pos[0] + Window.size[0],
                                  duration=self.conf_anim_dur + 0.2,
                                  t='linear')
            self.anim2 = Animation(x = self.ids.scatter2.pos[0] + Window.size[0],
                                  duration=self.conf_anim_dur + 0.2,
                                  t='linear')
          else:
            self.ids.scatter.pos = (self.ids.scatter.pos[0] + Window.size[0], self.ids.scatter.pos[1])
            self.anim = Animation(x=self.ids.scatter.pos[0] - Window.size[0],
                                  duration=self.conf_anim_dur + 0.2,
                                  t='linear')
            self.anim2 = Animation(x = self.ids.scatter2.pos[0] - Window.size[0],
                                  duration=self.conf_anim_dur + 0.2,
                                  t='linear')

          self.anim2.start(self.ids.scatter2)
          self.anim.start(self.ids.scatter)

          while self.anim.have_properties_to_animate(self.ids.scatter):
            EventLoop.idle()
          while self.anim2.have_properties_to_animate(self.ids.scatter2):
            EventLoop.idle()

        else:
          self.ids.bg_image.opacity = 1

        # cache next image
        next_page = self.page_number + 1
        t = threading.Thread(target=self.cached_image.load_next_page)
        t.daemon = True
        t.start()

        self.is_converting = False
        self.ids.blend_image.opacity = 0
        self.is_prev_page = False

        #unlock page
        if self.conf_lock_page == '1' and self.zoom_level == 1:
          self.ids.scatter.do_scale = False
          self.ids.scatter.do_translation = False
          self.ids.scatter2.do_scale = False
          self.ids.scatter2.do_translation = False
        else:
          self.ids.scatter.do_scale = True
          self.ids.scatter.do_translation = True
          self.ids.scatter2.do_scale = True
          self.ids.scatter2.do_translation = True

    def load_page(self, *args):
        self.page_out()
        print("load_page")

        self.image_resize_ratio = 1
        self.frames = self.acbf_document.load_page_frames(self.page_number)
        self.load_image = str(self.acbf_document.load_page_image(self.page_number)[0])
        self.is_converting = True

        if self.load_image != self.cached_image.original_name or self.page_number > self.pages_total:
          self.cached_image.load_current_page()
        self.load_image = self.cached_image.file_name

        #reload if needed
        if self.ids.bg_image.source == self.load_image:
          self.ids.bg_image.reload()
        else:
          self.ids.bg_image.source = './images/default.png'
          self.ids.bg_image.source = self.load_image#.encode('ascii', 'replace').replace('?', '_')

        #resize large image
        if (self.ids.bg_image.source == './images/default.png' or
            self.ids.bg_image.size[0] > self.MAX_TEXTURE_SIZE or
            self.ids.bg_image.size[1] > self.MAX_TEXTURE_SIZE):
          EventLoop.idle()
          self.resize_source_image()

        if len(self.frames) == 0:
          self.frames = [([(0,0), (0, self.ids.bg_image.height), (self.ids.bg_image.width, 0), (self.ids.bg_image.width, self.ids.bg_image.height)], '#000000')]
        self.page_color = self.hex_to_rgb(self.acbf_document.load_page_image(self.page_number)[1])

        self.reposition('move')

    def slide_to_page(self, value):
        self.no_page_anim = True
        if self.page_number != int(value):
          self.jump_to_page(value)
          self.page_in()
        self.no_page_anim = False

    def jump_to_page(self, value):
        self.page_number = int(value)
        self.frame_number = 1
        self.ids.slider.value = value
        self.load_page()
        
    def on_touch_down(self, touch):
        if self.conf_lock_page == '1' and self.zoom_level == 1:
          self.ids.scatter.do_scale = False
          self.ids.scatter.do_translation = False
        else:
          self.ids.scatter.do_scale = True
          self.ids.scatter.do_translation = True
        self.last_touch = touch.pos
        self.last_touch_time = time.time()
        return super(ScatterBackGroundImage, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        self.really_exit = False

        #print(self.ids.toolbar.pos, self.ids.toolbar.size, touch.pos)
        if self.anim.have_properties_to_animate(self.ids.bg_image) or self.is_converting or self.ids.loading_image.opacity != 0:
          return

        # in library
        if self.library_dialog.library_shown or self.is_animating:
          return super(ScatterBackGroundImage, self).on_touch_up(touch)

        # not a move
        if (abs(self.last_touch[0] - touch.pos[0]) < self.touch_move_error and
            abs(self.last_touch[1] - touch.pos[1]) < self.touch_move_error and
            time.time() - self.last_touch_time < 1):
          # show/hide toolbar
          if (touch.pos[0] > self.width / 3 and touch.pos[0] < self.width - self.width / 3 and
             touch.pos[1] > self.height / 5 and touch.pos[1] < self.height - self.height / 5):
            if not self.toolbar_shown:
              self.show_toolbar()
            else:
              self.hide_toolbar()
            return

          if self.toolbar_shown and not self.ids.toolbar.collide_point(*touch.pos):
            self.hide_toolbar()
            return

          # navigate
          if not self.toolbar_shown:
            # next
            if (touch.pos[0] > self.width - self.width / 3):
              if self.zoom_level == 1:
                self.next_page()
              elif self.zoom_level == 2:
                if self.ids.scatter.pos[1] + self.touch_move_error >= 0:
                  self.next_page()
                else:
                  scroll_to = self.ids.scatter.pos[1] + self.scroll_step
                  if scroll_to > 0:
                    scroll_to = 0
                  self.animate_to_pos(self.ids.scatter.pos[0], scroll_to, self.ids.scatter.scale, self.conf_anim_dur)
              elif self.zoom_level == 3:
                self.frame_number = self.frame_number + 1
                if self.frame_number > len(self.frames):
                  self.frame_number = self.frame_number - 1
                  self.next_page()
                  return
                else:
                  self.zoom_to_frame(self.frames[self.frame_number - 1], 'animate')
                self.frame_color = self.hex_to_rgb(self.frames[self.frame_number - 1][1])
              return
            # prev
            elif (touch.pos[0] < self.width / 3):
              if self.zoom_level == 1:
                self.prev_page()
              elif self.zoom_level == 2:
                if  self.ids.scatter.pos[1] - self.touch_move_error <= self.zoom_width_top:
                  self.prev_page()
                  return
                else:
                  scroll_to = self.ids.scatter.pos[1] - self.scroll_step
                  if scroll_to < self.zoom_width_top:
                    scroll_to = self.zoom_width_top
                  self.animate_to_pos(self.ids.scatter.pos[0], scroll_to, self.ids.scatter.scale, self.conf_anim_dur)
              elif self.zoom_level == 3:
                self.frame_number = self.frame_number - 1
                if self.frame_number < 1:
                  self.frame_number = 1
                  self.prev_page()
                  return
                else:
                  self.zoom_to_frame(self.frames[self.frame_number - 1], 'animate')
                self.frame_color = self.hex_to_rgb(self.frames[self.frame_number - 1][1])
              return
          return

        # return to bounds
        if self.zoom_level == 3:
          if (((self.last_touch[0] - touch.pos[0]) > min(Window.width, Window.height) / 5 or
               (touch.pos[1] - self.last_touch[1]) > min(Window.width, Window.height) / 5) and
               not (self.last_touch[1] - touch.pos[1]) > min(Window.width, Window.height) / 5 and
               not self.toolbar_shown and round(self.ids.scatter.scale, 2) == round(self.scatter_scale, 2)):
            self.frame_number = self.frame_number + 1
            if self.frame_number > len(self.frames):
              self.frame_number = self.frame_number - 1
              self.next_page()
              return
          elif (((touch.pos[0] - self.last_touch[0]) > min(Window.width, Window.height) / 5 or
                (self.last_touch[1] - touch.pos[1]) > min(Window.width, Window.height) / 5) and
                not self.toolbar_shown and round(self.ids.scatter.scale, 2) == round(self.scatter_scale, 2)):
            self.frame_number = self.frame_number - 1
            if self.frame_number < 1:
              self.frame_number = 1
              self.prev_page()
              return
          self.zoom_to_frame(self.frames[self.frame_number - 1], 'animate')
        elif self.zoom_level == 2:
          animate = False
          if self.ids.scatter.pos[0] < 0 or self.ids.scatter.pos[0] > 0:
            animate_to_y = self.ids.scatter.pos[1]
            animate = True
          if self.ids.scatter.pos[1] > 0:
            animate_to_y = 0
            animate = True
          if self.ids.scatter.pos[1] < self.zoom_width_top:
            animate_to_y = self.zoom_width_top
            animate = True
          if round(self.ids.scatter.scale, 10) != round(self.scatter_scale, 10):
            animate = True
            animate_to_y = self.scatter_position[1]
          if animate:
            self.animate_to_pos(0, animate_to_y, self.scatter_scale, self.conf_anim_dur)
          return super(ScatterBackGroundImage, self).on_touch_up(touch)

        # default return
        return super(ScatterBackGroundImage, self).on_touch_up(touch)

    def animate_to_pos(self, pos_x, pos_y, scale_to, anim_duration):
        print("animate_to_pos")
        if anim_duration > (self.conf_anim_dur * 2.5):
          anim_duration = self.conf_anim_dur * 2.5
        self.is_animating = True
        self.scatter_position = (pos_x, pos_y)
        Animation.cancel_all(self)
        anim = Animation(scale=scale_to,
                         duration=anim_duration,
                         t='linear')

        anim &= Animation(x=pos_x, y=pos_y,
                          duration=anim_duration,
                          t='linear')

        anim += Animation(x=pos_x, y=pos_y, scale=scale_to,
                          duration=anim_duration / 4,
                          t='linear')
        anim.bind(on_complete=self.animation_complete)
        anim.start(self.ids.scatter)

    def animation_complete(self, animation, widget):
        self.ids.scatter.pos = self.scatter_position
        self.is_animating = False


    def zoom_to_frame(self, frame, mode):
        # get frame bounds
        x_min = 100000000
        x_max = -1
        y_min = 100000000
        y_max = -1
        for frame_tuple in frame[0]:
          if x_min > frame_tuple[0] * self.image_resize_ratio:
            x_min = frame_tuple[0] * self.image_resize_ratio
          if y_min > frame_tuple[1] * self.image_resize_ratio:
            y_min = frame_tuple[1] * self.image_resize_ratio
          if x_max < frame_tuple[0] * self.image_resize_ratio:
            x_max = frame_tuple[0] * self.image_resize_ratio
          if y_max < frame_tuple[1] * self.image_resize_ratio:
            y_max = frame_tuple[1] * self.image_resize_ratio

        # calculate pos and scale
        framesize = (x_max - x_min, y_max - y_min)
        scale_x = Window.width / float(framesize[0])
        scale_y = Window.height / float(framesize[1])
        scaleframe = min(scale_x, scale_y)
        framesize_scaled = (framesize[0] * scaleframe, framesize[1] * scaleframe)

        framepos_x = ((Window.width - framesize_scaled[0]) / 2) - (x_min * scaleframe)
        framepos_y = ((framesize_scaled[1] - Window.height) / 2) + Window.height + (y_min * scaleframe) - self.ids.bg_image.height * scaleframe

        self.scatter_scale = scaleframe
        self.scatter_position = framepos_x, framepos_y
        self.frame_center_old = self.frame_center
        self.frame_center = x_min + (x_max - x_min) / 2, y_min + (y_max - y_min) / 2

        #self.ids.bg_image.canvas.after.clear()
        #self.ids.bg_image.canvas.after.add(Color(1, 0, 0, 0.5))
        #self.ids.bg_image.canvas.after.add(Rectangle(size=framesize, pos=(x_min, self.ids.bg_image.height - y_min - framesize[1])))

        if mode == 'animate':
          distance_to_animate = hypot(self.frame_center[0] - self.frame_center_old[0], self.frame_center[1] - self.frame_center_old[1])
          anim_duration = self.conf_anim_dur + distance_to_animate / self.ids.scatter.size[0] * self.conf_anim_dur * 2
          self.animate_to_pos(self.scatter_position[0], self.scatter_position[1], scaleframe, anim_duration * 0.8)
        elif mode == 'move':
          self.ids.scatter.scale = self.scatter_scale
          self.ids.scatter.pos = self.scatter_position

    def hex_to_rgb(self, value):
        if value == None:
          return None
        value = value.lstrip('#')
        lv = len(value)
        color = tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
        color_rgba = []
        color_rgba.append(color[0]/float(255))
        color_rgba.append(color[1]/float(255))
        color_rgba.append(color[2]/float(255))
        color_rgba.append(1)

        return color_rgba

    def refresh_library(self):
        print("refresh_library")
        if not self.library_dialog.library_shown:
          return
        self.library_dialog.ids.lib_layout.clear_widgets()
        self.library_dialog.icon_set = self.conf_iconset

        self.library.sort_library('sequence')

        for book in self.library.tree.findall("book"):
          filename = book.find("coverpage").text
          cover_image = Image(source = filename)
          cover_width = int(cover_image.norm_image_size[0]*self.cover_height/float(cover_image.size[1]))
          comic = Cover()
          comic.height = self.cover_height
          for widget in comic.children:
            if widget.name == 'book_cover':
              coverpage = widget
            elif widget.name == 'book_name':
              label = widget
            elif widget.name == 'progress_bar':
              progress_bar = widget
            elif widget.name == 'has_frames':
              has_frames = widget
            elif widget.name == 'has_frames_bg':
              has_frames_bg = widget
          coverpage.background_normal = filename
          coverpage.background_down = filename
          coverpage.width = cover_width
          coverpage.text = book.get("path")
          coverpage.size_hint_x = 1
          coverpage.bind(on_release = self.open_book_dialog)

          label.text = self.get_element_text3(book, "title", "en")
          for title in book.findall("title"):
            if self.default_text_layer != "??#":
              if title.get("lang") == self.default_text_layer:
                  label.text = title.text

          if self.get_element_text2(book, "has_frames") == 'True':
            has_frames.text = ' *'
            has_frames_bg.text = ' *'

          (page_number, frame_number, zoom_level, language_layer) = self.history.get_book_details(book.get("path"))
          if book.find("pages") != None and page_number > 1:
            progress_bar.size_hint = (float(page_number)/(int(book.find("pages").text) + 1), None)
          else:
            progress_bar.height = 0

          self.library_dialog.ids.lib_layout.add_widget(comic)
          EventLoop.idle()

    def show_library(self, *args):
        print("show_library")
        if not self.acbf_document.valid:
          self.bg_color = [0,0,0,0]
          self.ids.bg_image.opacity = 0

        self.library_dialog.library_shown = True
        self.library_dialog.icon_set = self.conf_iconset
        self.library_dialog.open()
        self.library_dialog.lib_layout.bind(minimum_height=self.library_dialog.lib_layout.setter('height'))
        self.library_dialog.lib_layout.bind(minimum_width=self.library_dialog.lib_layout.setter('width'))

        self.history.set_book_details(self.filename, self.page_number, self.frame_number, self.zoom_index, self.language_layer)
        self.history.save_history()
        self.library.check_books()

        if self.total_books == 0:
          self.library_dialog.dismiss()
          return

        self.reposition('move')
        self.set_systemui_visibility(0)
        
    def populate_library(self, *args):
        print("populate_library")

        #wait_time = int(len(self.library.tree.findall("book")) / 7) + 1

        #wait for UI displaying to finish
        #t = threading.Thread(target=time.sleep, args = ([wait_time]))
        #t.daemon = True
        #t.start()
        #while t.is_alive():
        #  EventLoop.idle()

        book_is_added = False

        folder = str(App.get_running_app().config.get('general', 'lib_path'))
        if folder in ('/', '/sdcard/'):
          # don't go through whole directory structure
          return

        if not os.path.exists(self.library_dir):
          os.makedirs(self.library_dir, 0o700)

        for root, dirs, files in os.walk(folder):
          for f in files:
            if f == u'default.cbz':
              break
            if f[-4:].upper() == '.CBZ' or f[-5:].upper() == '.ACBF' or f[-4:].upper() == '.ACV' or f[-4:].upper() == '.CBR':
              for book in self.library.tree.findall("book"):
                if book.get("path") == os.path.join(root, f):
                  break
              else:
                try:
                  book_is_added = True
                  self.loading_book_dialog = LoadingBookDialog()
                  self.loading_book_dialog.title = 'Importing Comic Book ...'
                  self.loading_book_dialog.book_path = os.path.join(root, f)
                  self.loading_book_dialog.ids.loading_progress_bar.value = 0
                  self.loading_book_dialog.open()
                  EventLoop.idle()
                  self.library.insert_new_book(os.path.join(root, f), self.tempdir, None)
                  self.library.save_library()
                  self.loading_book_dialog.dismiss()
                except Exception as inst:
                  print("Failed to import comic book:", os.path.join(root, f).encode('ascii','ignore'))
                  print("Exception: %s" % inst)
                  self.loading_book_dialog.dismiss()

        # remove duplicates (cbz with same base filename as acbf file)
        referenced_archives = []
        for referenced_archive in self.library.tree.findall("book"):
          if referenced_archive.get("path")[-4:].upper() == 'ACBF':
            referenced_archives.append(referenced_archive.get("path")[0:-4] + 'cbz')

        for referenced_archive in referenced_archives:
          self.library.delete_book(referenced_archive)

        self.total_books = len(self.library.tree.findall("book"))

        if self.library_dialog.library_shown and book_is_added:
          self.refresh_library()

    def get_element_text2(self, element_tree, element):
        try:
          text_value = unescape(element_tree.find(element).text)
          if text_value is None:
            text_value = ''
        except:
          text_value = ''
        return text_value

    def get_element_text3(self, element_tree, element, lang):
       try:
         text_value = unescape(element_tree.find(element).text)
         for i in element_tree.findall(element):
           if i.get("lang") == lang or (i.get("lang") == None and lang == "en"):
             text_value = unescape(i.text)
         if text_value is None:
           text_value = ''
       except:
         text_value = ''
       return text_value

    def open_book_dialog(self, widget):
        print("open_book_dialog")
        view = ComicBookDialog()
        view.book_path = widget.text
        view.icon_set = self.conf_iconset
        view.open()
        view.bind(on_dismiss=self.close_dialog)
        for book in self.library.tree.findall("book"):
          if book.get("path") == widget.text:
            view.ids.cover_image.source = book.find("coverpage").text
            
            publish_date = " (" + self.get_element_text2(book, "publish_date")[0:4] + ")"

            bookname = self.get_element_text3(book, "title", "en")
            for title in book.findall("title"):
              if self.default_text_layer != "??#":
                if title.get("lang") == self.default_text_layer:
                    bookname = title.text

            annotation = self.get_element_text3(book, "annotation", "en")
            for anno in book.findall("annotation"):
              if self.default_text_layer != "??#":
                if anno.get("lang") == self.default_text_layer:
                    annotation = anno.text

            markup = '[size=20sp][b]' + bookname + publish_date + '[/b][/size]\n' + '\n[b]Author(s): [/b] ' + self.get_element_text2(book, "authors")
            if self.get_element_text2(book, "sequence") != '':
              markup = markup + '\n[b]Series: [/b] ' + self.get_element_text2(book, "sequence")
            markup = markup + '\n[b]Publisher: [/b] ' + self.get_element_text2(book, "publisher") 
            if self.get_element_text2(book, "license") != '':
              markup = markup + '\n[b]License: [/b] ' + self.get_element_text2(book, "license")
            markup = markup + '\n[b]Genre(s): [/b] ' + self.get_element_text2(book, "genres")
            if self.get_element_text2(book, "characters") != '':
              markup = markup + '\n[b]Characters: [/b] ' + self.get_element_text2(book, "characters")
            markup = markup + '\n[b]Annotation: [/b] ' + annotation
            markup = markup + '\n[b]Pages: [/b] ' + self.get_element_text2(book, "pages") + ' + cover'
            markup = markup + '\n[b]Frames definitions: [/b] '
            if self.get_element_text2(book, "has_frames") == '':
              markup = markup + 'False'
            else:
              markup = markup + self.get_element_text2(book, "has_frames")
            markup = markup + '\n[b]Languages: [/b] ' + self.get_element_text2(book, "languages")
            markup = markup + '\n\n[b]Path: [/b] ' + str(book.get("path"))
            view.ids.comic_metadata.text = markup

    def close_dialog(self, dialog):
        print("close_dialog")
        if dialog.button_pressed == 'open':
          dialog.pos = 0, Window.height
          self.loading_book_dialog = LoadingBookDialog()
          self.loading_book_dialog.title = 'Loading Comic Book ...'
          self.loading_book_dialog.book_path = dialog.book_path
          self.loading_book_dialog.ids.loading_progress_bar.value = 0
          self.loading_book_dialog.open()
          self.loading_book_dialog.bind(on_dismiss=self.open_book)
          EventLoop.idle()
          self.load_book(dialog.book_path, True)
        elif dialog.button_pressed == 'remove':
          view = RemoveBookDialog()
          view.book_path = dialog.book_path
          view.open()
          view.bind(on_dismiss=self.close_remove_dialog)

        return False

    def close_remove_dialog(self, dialog):
        if dialog.button_pressed == 'remove':
          try:
            if platform == 'android':
              currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
              uri = Uri.parse(dialog.book_path)
              documentfile = DocumentFile.fromSingleUri(currentActivity, uri)
              documentfile.delete()
            else:
              os.remove(dialog.book_path)
            self.library.check_books()
            self.refresh_library()
          except Exception as inst:
            view = ErrorDialog()
            view.ids.label_text.text = "Can't delete the comic book: %s" % inst
            view.open()

    def load_book(self, path, scheduled):
        print("load_book")

        self.hide_toolbar()
        self.history.set_book_details(self.filename, self.page_number, self.frame_number, self.zoom_index, self.language_layer)
        self.history.save_history()

        self.filename = path
        
        if scheduled:
          if platform == 'android':
            cache_dir = SharedStorage().get_cache_dir()
            if cache_dir and os.path.exists(cache_dir): shutil.rmtree(cache_dir)  # cleaning cache
            print("Copying file from share: ", self.filename)
            sharefile = SharedStorage().copy_from_shared(Uri.parse(self.filename))
            t = threading.Thread(target=fileprepare.FilePrepare, args = (self, sharefile, self.tempdir, 'book'))
          else:
            t = threading.Thread(target=fileprepare.FilePrepare, args = (self, self.filename, self.tempdir, 'book'))
          t.daemon = True
          t.start()

          while t.is_alive():
            time.sleep(0.1)
            EventLoop.idle()
          EventLoop.idle()
          
          # cleaning cache
          if platform == 'android':
            if cache_dir and os.path.exists(cache_dir):
              shutil.rmtree(cache_dir)
          self.loading_book_dialog.dismiss()
        else:
          fileprepare.FilePrepare(self, self.filename, self.tempdir, 'book')
          self.loading_book_dialog.dismiss()

    def open_book(self, *args):
        print("open_book")
        self.no_page_anim = True
        self.base_dir = os.path.dirname(self.filename)
        self.acbf_document = acbfdocument.ACBFDocument(self, self.prepared_file)

        if self.acbf_document.font_styles['normal'] != '':
          self.normal_font = self.acbf_document.font_styles['normal']
        if self.acbf_document.font_styles['emphasis'] != '':
          self.emphasis_font = self.acbf_document.font_styles['emphasis']
        if self.acbf_document.font_styles['strong'] != '':
          self.strong_font = self.acbf_document.font_styles['strong']
        if self.acbf_document.font_styles['code'] != '':
          self.code_font = self.acbf_document.font_styles['code']
        if self.acbf_document.font_styles['commentary'] != '':
          self.commentary_font = self.acbf_document.font_styles['commentary']
        if self.acbf_document.font_styles['sign'] != '':
          self.sign_font = self.acbf_document.font_styles['sign']
        if self.acbf_document.font_styles['formal'] != '':
          self.formal_font = self.acbf_document.font_styles['formal']
        if self.acbf_document.font_styles['heading'] != '':
          self.heading_font = self.acbf_document.font_styles['heading']
        if self.acbf_document.font_styles['letter'] != '':
          self.letter_font = self.acbf_document.font_styles['letter']
        if self.acbf_document.font_styles['audio'] != '':
          self.audio_font = self.acbf_document.font_styles['audio']
        if self.acbf_document.font_styles['thought'] != '':
          self.thought_font = self.acbf_document.font_styles['thought']

        self.pages_total = self.acbf_document.pages_total

        self.library_dialog.dismiss()
        EventLoop.idle()

        self.zoom_index = 0
        self.page_number = 1
        self.frame_number = 1

        (self.page_number, self.frame_number, self.zoom_index, self.language_layer) = self.history.get_book_details(self.filename)
        if self.conf_zoom_to_frame == '1' and self.acbf_document.has_frames:
          self.zoom_index = 2
        self.zoom_level = self.zoom_list[self.zoom_index]

        # set language layer to default if available
        if self.default_text_layer != '??#':
          for idx, layer in enumerate(self.acbf_document.languages):
            if layer[1] == 'TRUE' and layer[0] == self.default_text_layer:
              self.language_layer = idx

        self.ids.slider.value = self.page_number
        self.load_page()

        threads = int(App.get_running_app().config.get('general', 'threads').split(',')[1])
        threads_count = int(App.get_running_app().config.get('general', 'threads').split(',')[2])
        threads_delay = float(0.2)#float(App.get_running_app().config.get('general', 'threads').split(',')[3])
        thread_setting = 'True,' + str(threads) + ',' + str(threads_count) + ',' + str(round(threads_delay, 1))
        App.get_running_app().config.set('general', 'threads', thread_setting)
        App.get_running_app().config.write()

        self.body_color = self.hex_to_rgb(self.acbf_document.bg_color)
        self.page_color = self.hex_to_rgb(self.acbf_document.load_page_image(self.page_number)[1])
        self.frame_color = [0,0,0,1]
        self.reposition('move')
        self.page_in()

        # set text layer display on toolbar
        if self.acbf_document.languages[self.language_layer][1] == 'FALSE':
          self.ids.text_layer_label.text = self.acbf_document.languages[self.language_layer][0] + '#'
        else:
          self.ids.text_layer_label.text = self.acbf_document.languages[self.language_layer][0]
        self.hide_toolbar()
        self.no_page_anim = False

    def show_toolbar(self, *args):
        print("show_toolbar")
        self.icon_set = self.conf_iconset
        self.ids.toolbar.pos = (0, Window.height - Window.width / 8)
        self.ids.slider.pos = (0, 0)
        self.toolbar_shown = True
        self.set_systemui_visibility(0)

    def hide_toolbar(self):
        self.ids.toolbar.pos = (0, self.height + 10)
        self.ids.slider.pos = (0, self.height + 10)
        self.toolbar_shown = False
        #if not self.library_dialog.library_shown:
        #  self.set_systemui_visibility(View.SYSTEM_UI_FLAG_LOW_PROFILE)

    def hook_keyboard(self, window, key, *largs):
        if key == 27: # BACK BUTTON
          if not self.really_exit:
            self.really_exit = True
            #fade out
            anim = Animation(opacity = 1,
                                  duration=self.conf_anim_dur * 2,
                                  t='out_cubic')

            anim.start(self.ids.exit_notif)

            while anim.have_properties_to_animate(self.ids.exit_notif):
              EventLoop.idle()

            #fade_in
            anim = Animation(opacity = 0,
                                  duration=self.conf_anim_dur * 2,
                                  t='in_cubic')
            anim.start(self.ids.exit_notif)
            return True
        elif key in (282, 319): # SETTINGS
          pass

    def load_settings(self):
        print('Load Settings')
        self.conf_zoom_to_frame = App.get_running_app().config.get('general', 'zoom_to_frame')
        self.conf_keep_screen_on = App.get_running_app().config.get('general', 'keep_screen_on')
        self.conf_lock_page = App.get_running_app().config.get('general', 'lock_page')
        self.library_cols = int(App.get_running_app().config.get('general', 'max_covers'))
        self.conf_iconset = App.get_running_app().config.get('general', 'iconset')
        self.set_keep_screen_on(self.conf_keep_screen_on)
        self.conf_transition = App.get_running_app().config.get('image', 'transition')
        if App.get_running_app().config.get('image', 'resize_filter') == 'Nearest (fastest)':
          self.conf_resize_filter = pil_image.NEAREST
        elif App.get_running_app().config.get('image', 'resize_filter') == 'Bilinear':
          self.conf_resize_filter = pil_image.BILINEAR
        elif App.get_running_app().config.get('image', 'resize_filter') == 'Bicubic':
          self.conf_resize_filter = pil_image.BICUBIC
        elif App.get_running_app().config.get('image', 'resize_filter') == 'Antialias (best quality)':
          self.conf_resize_filter = pil_image.ANTIALIAS
        self.conf_anim_dur = float(App.get_running_app().config.get('image', 'anim_dur'))
        for font in constants.FONTS_LIST:
          if font[0] == App.get_running_app().config.get('image', 'normal_font'):
            self.normal_font = font[1]
          if font[0] == App.get_running_app().config.get('image', 'strong_font'):
            self.strong_font = font[1]
          if font[0] == App.get_running_app().config.get('image', 'emphasis_font'):
            self.emphasis_font = font[1]
          if font[0] == App.get_running_app().config.get('image', 'code_font'):
            self.code_font = font[1]
          if font[0] == App.get_running_app().config.get('image', 'commentary_font'):
            self.commentary_font = font[1]
        self.sign_font = self.normal_font
        self.formal_font = self.normal_font
        self.heading_font = self.normal_font
        self.letter_font = self.normal_font
        self.audio_font = self.normal_font
        self.thought_font = self.normal_font

        self.default_text_layer = App.get_running_app().config.get('image', 'default_text_layer')
        if App.get_running_app().config.get('general', 'use_temp_dir') == '1':
          self.tempdir = App.get_running_app().config.get('general', 'temp_dir_path')
        else:
          self.tempdir = self.default_temp_dir

class ComicBookLibrary(ModalView):
    lib_layout = ObjectProperty(None)
    cols = NumericProperty(3)

    def close_dialog(self, *args):
      print("ComicBookLibrary.close_dialog")
      _window_ = App.get_running_app().my_app
      if _window_.acbf_document.valid:
        self.library_shown = False
        return False

      if _window_.really_exit:
        App.get_running_app().stop()
      else:
        _window_.really_exit = True
        #fade out
        anim = Animation(opacity = 1,
                              duration=_window_.conf_anim_dur * 2,
                              t='out_cubic')

        anim.start(self.ids.exit_notif)

        while anim.have_properties_to_animate(self.ids.exit_notif):
          EventLoop.idle()

        #fade_in
        anim = Animation(opacity = 0,
                              duration=_window_.conf_anim_dur * 2,
                              t='in_cubic')
        anim.start(self.ids.exit_notif)

      return True

class CachedImage(): #cached_image
    def __init__(self, window):
        self._window = window
        self.is_loading =  False
        self.file_name = './images/blank.png'
        self.original_name = './images/blank.png'
        self.cached_file = os.path.join(self._window.tempdir, 'temp_cached.jpg')

    def load_next_page(self):
        if self._window.page_number < self._window.pages_total + 1:
          self.load_image(self._window.page_number + 1)

    def load_current_page(self):
        self.load_image(self._window.page_number)

    def load_image(self, page_number):
        while self.is_loading:
          time.sleep(0.1)

        self.is_loading =  True
        try:
          self.original_name = str(self._window.acbf_document.load_page_image(page_number)[0])
        except:
          self.original_name = './images/default.png'

        if self.cached_file == os.path.join(self._window.tempdir, 'temp_cached.jpg'):
          self.cached_file = os.path.join(self._window.tempdir, 'temp_cached1.jpg')
        else:
          self.cached_file = os.path.join(self._window.tempdir, 'temp_cached.jpg')

        self.file_name = self.original_name

        # WebP conversion
        if self.original_name[-4:].upper() == 'WEBP':
          print("Cache: webp conversion")
          im = pil_image.open(self.original_name).convert("RGB")
          self.file_name = self.cached_file
          im.save(self.file_name,"jpeg")

        # GIF conversion
        elif self.original_name[-4:].upper() == '.GIF':
          print("Cache: gif conversion")
          image = pil_image.open(self.original_name)
          self.file_name = self.cached_file
          image.convert('RGB').save(self.file_name.format("RGB"), "JPEG")
        else:
          self.file_name = self.original_name

        # draw text layer
        if self._window.acbf_document.languages[self._window.language_layer][1] == 'TRUE':
          print("Cache: draw layer")
          output_image = self.cached_file
          self.text_layer = text_layer.TextLayer(self.file_name, page_number, self._window.acbf_document,
                                                 self._window.language_layer, output_image, self._window.normal_font,
                                                 self._window.strong_font, self._window.emphasis_font, self._window.code_font,
                                                 self._window.commentary_font, self._window.sign_font, self._window.formal_font,
                                                 self._window.heading_font, self._window.letter_font, self._window.audio_font,
                                                 self._window.thought_font, self._window)
          self.file_name = output_image

        self.is_loading =  False

# Scollable Options override
class SettingSpacer(Widget):
    # Internal class, not documented.
    pass

class SettingScrollOptions(SettingOptions):

    def _create_popup(self, instance):
        # create the popup
        content         = GridLayout(cols=1, spacing='5dp')
        scrollview      = ScrollView( do_scroll_x=False)
        scrollcontent   = GridLayout(cols=1,  spacing='5dp', size_hint=(None, None))
        scrollcontent.bind(minimum_height=scrollcontent.setter('height'))
        self.popup   = popup = Popup(content=content, title=self.title, size_hint=(0.5, 0.9),  auto_dismiss=False)

        #we need to open the popup first to get the metrics 
        popup.open()
        #Add some space on top
        content.add_widget(Widget(size_hint_y=None, height=dp(2)))
        # add all the options
        uid = str(self.uid)
        for option in self.options:
            state = 'down' if option == self.value else 'normal'
            btn = ToggleButton(text=option, state=state, group=uid, size=(popup.width, dp(55)), size_hint=(None, None))
            btn.bind(on_release=self._set_option)
            scrollcontent.add_widget(btn)

        # finally, add a cancel button to return on the previous panel
        scrollview.add_widget(scrollcontent)
        content.add_widget(scrollview)
        content.add_widget(SettingSpacer())
        #btn = Button(text='Cancel', size=((oORCA.iAppWidth/2)-sp(25), dp(50)),size_hint=(None, None))
        btn = Button(text='Cancel', size=(popup.width, dp(50)),size_hint=(0.9, None))
        btn.bind(on_release=popup.dismiss)
        content.add_widget(btn)

class SettingIconPath(SettingPath):

    def set_home_path(self, *args):
        if os.path.isdir('/sdcard/'):
          self.textinput.path = '/sdcard/'
        else:
          self.textinput.path = '/'

    def _create_popup(self, instance):
        # create popup layout
        content = BoxLayout(orientation='vertical', spacing=5)
        popup_width = min(0.95 * Window.width, dp(500))
        self.popup = popup = Popup(
            title=self.title, content=content, size_hint=(None, 0.9),
            width=popup_width)

        if os.path.isdir('/storage/'):
          root_dir = '/storage/'
        elif os.path.isdir('/sdcard/'):
          root_dir = '/sdcard/'
        else:
          root_dir = '/'

        # create the filechooser
        self.textinput = textinput = FileChooserIconView(
            path=self.value, size_hint=(1, 1), dirselect=True, rootpath=root_dir)
        textinput.bind(on_path=self._validate)
        self.textinput = textinput

        # construct the content
        content.add_widget(textinput)
        content.add_widget(SettingSpacer())

        # 2 buttons are created for accept or cancel the current value
        btnlayout = BoxLayout(size_hint_y=None, height='50dp', spacing='5dp')
        btn = Button(text='Home')
        btn.bind(on_release=self.set_home_path)
        btnlayout.add_widget(btn)
        btn = Button(text='Ok')
        btn.bind(on_release=self._validate)
        btnlayout.add_widget(btn)
        btn = Button(text='Cancel')
        btn.bind(on_release=self._dismiss)
        btnlayout.add_widget(btn)
        content.add_widget(btnlayout)

        # all done, open the popup !
        popup.open()

class Cover(AnchorLayout):
    pass

class ComicBookDialog(ModalView):
    pass

class ContentsDialog(Popup):
    pass

class LayersDialog(Popup):
    pass

class RemoveBookDialog(Popup):
    pass

class ErrorDialog(Popup):
    pass

class LoadingBookDialog(Popup):
    pass

class ACBFaApp(App):

    def build(self):
        # get Android permissions
        if platform == 'android':
          request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE])
          
        # directories
        self.tempdir_root = constants.DATA_DIR
        self.tempdir =  str(os.path.join(self.tempdir_root, ''.join('tmp')))
        if not os.path.exists(self.tempdir):
          os.makedirs(self.tempdir, 0o700)
        if not os.path.exists(self.user_data_dir):
          os.makedirs(self.user_data_dir, 0o700)

        print("DATA: " + constants.DATA_DIR)
        print("CONFIG: " + self.user_data_dir)

        self.icon = 'images/acbfa.png'
        self.title = 'ACBF Viewer for Android'

        self.tmp_cleanup()
        self.cleaned_up = False
        # settings
        self.settings_cls = SettingsWithTabbedPanel
        self.use_kivy_settings = False

        # run
        self.my_app = ScatterBackGroundImage(self.tempdir, self.user_data_dir)
        return self.my_app

    def on_pause(self):
      self.my_app.history.set_book_details(self.my_app.filename, self.my_app.page_number, self.my_app.frame_number, self.my_app.zoom_index, self.my_app.language_layer)
      self.my_app.history.save_history()
      return True

    def on_stop(self):
        if self.cleaned_up:
          return
        else:
          self.cleaned_up = True

        self.tmp_cleanup()
        self.my_app.history.set_book_details(self.my_app.filename, self.my_app.page_number, self.my_app.frame_number, self.my_app.zoom_index, self.my_app.language_layer)
        self.my_app.history.save_history()

    def tmp_cleanup(self):
        print("Cleanup")
        # clear temp directory
        for root, dirs, files in os.walk(self.tempdir):
          for f in files:
            os.unlink(os.path.join(root, f))
          for d in dirs:
            shutil.rmtree(os.path.join(root, d))
        #shutil.rmtree(self.tempdir)
        
        try:
          for root, dirs, files in os.walk(self.my_app.tempdir):
            for f in files:
              os.unlink(os.path.join(root, f))
            for d in dirs:
              shutil.rmtree(os.path.join(root, d))
        except:
          None

    def build_config(self, config):
        print('Build Config')
        if os.path.isdir('/sdcard/'):
          library_path = '/sdcard/'
        else:
          library_path = '/'
        
        self.tempdir_root = constants.DATA_DIR
        self.tempdir =  str(os.path.join(self.tempdir_root, ''.join('tmp')))
        config.setdefaults('general', {
                           'lib_path': library_path,
                           'lib_path_change': 0,
                           'use_temp_dir': 0,
                           'temp_dir_path': self.tempdir,
                           'zoom_to_frame': 1,
                           'keep_screen_on': 0,
                           'lock_page': 1,
                           'iconset': 'Default',
                           'max_covers': 6,
                           'version': '',
                           'copyright': '',
                           'threads': 'True,30,0,0.2'})

        self.normal_font = self.strong_font = self.emphasis_font = self.code_font = self.commentary_font = self.sign_font = self.formal_font = self.heading_font = self.letter_font = self.audio_font = self.thought_font = ''

        for font in constants.FONTS_LIST:
          if font[0] == 'DroidSans.ttf':
            self.normal_font = 'DroidSans.ttf'
          elif font[0] == 'DroidSans-Bold.ttf':
            self.strong_font = 'DroidSans-Bold.ttf'
          elif font[0] == 'DroidSerif-BoldItalic.ttf':
            self.emphasis_font = 'DroidSerif-BoldItalic.ttf'
          elif font[0] == 'DroidSansMono.ttf':
            self.code_font = 'DroidSansMono.ttf'
          elif font[0] == 'DroidSans.ttf':
            self.commentary_font = 'DroidSans.ttf'

          if self.emphasis_font == 'DroidSans.ttf' and 'BoldItalic.' in font[0]:
            self.emphasis_font = font[0]
        
        if self.normal_font == '':
          self.normal_font = self.strong_font = self.emphasis_font = self.code_font = self.commentary_font = self.sign_font = self.formal_font = self.heading_font = self.letter_font = self.audio_font = self.thought_font = 'DejaVuSans.ttf'
        
        config.setdefaults('image', {
                           'transition': 'Fade Out',
                           'anim_dur': 0.4,
                           'resize_filter': 'Bilinear',
                           'normal_font': self.normal_font,
                           'strong_font': self.strong_font,
                           'emphasis_font': self.emphasis_font,
                           'code_font': self.code_font,
                           'commentary_font': self.commentary_font,
                           'default_text_layer': '??#'})

    def build_settings(self, settings):
        settings.register_type('scrolloptions', SettingScrollOptions)
        settings.register_type('icon_path', SettingIconPath)
        settings.add_json_panel('General', self.config, data=settingsjson.lib_json)
        settings.add_json_panel('Image', self.config, data=settingsjson.image_json)
        self.settings = settings
        
    def user_select_folder(self, config):
        currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
        cache_dir = SharedStorage().get_cache_dir()
        
        def on_activity_result(request_code, result_code, intent):
          if request_code != RESULT_LOAD_FILE:
            print('user_select_image: ignoring activity result that was not RESULT_LOAD_FILE')
            return
          elif result_code == 0:
            return

          currentActivity.getContentResolver().takePersistableUriPermission(intent.getData(), Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
          selectedFolder = intent.getData();  # Uri
          print("selectedFolder:", selectedFolder.toString())
          uri = cast('android.net.Uri', selectedFolder)
          childrenUri = DocumentsContract.buildChildDocumentsUriUsingTree(uri, DocumentsContract.getTreeDocumentId(uri))
          documentfile = DocumentFile.fromTreeUri(currentActivity, childrenUri)
          print("DocumentFiles:", documentfile.listFiles())
          
          for f in documentfile.listFiles():
            file_uri = f.getUri()
            print(file_uri.toString())
            opened_file = SharedStorage().copy_from_shared(file_uri)
            print(opened_file)
            print(os.listdir(cache_dir))
            self.my_app.library.insert_new_book(opened_file, self.my_app.tempdir, file_uri.toString())
            self.my_app.library.save_library()
            
            if cache_dir and os.path.exists(cache_dir): shutil.rmtree(cache_dir)  # cleaning cache
          
          self.my_app.total_books = len(self.my_app.library.tree.findall("book"))
          
          for child in self.settings.interface.children:
            if str(type(child)) == "<class 'kivy.uix.tabbedpanel.TabbedPanel'>":
              for child2 in child.children:
                if str(type(child2)) == "<class 'kivy.uix.tabbedpanel.TabbedPanelContent'>":
                  for child3 in child2.children:
                    for child4 in child3.children:
                      for child5 in child4.children:
                        if str(type(child5)) == "<class 'kivy.uix.settings.SettingString'>":
                          if child5.key == 'lib_path':
                            child5.disabled = False
                            child5.value = selectedFolder.toString()
                            config.set('general', 'lib_path', selectedFolder.toString())
                            child5.disabled = True
                        if str(type(child5)) == "<class 'kivy.uix.settings.SettingBoolean'>":
                          if child5.key == 'lib_path_change':
                            config.set('general', 'lib_path_change', 0)
          config.write()
          return

        activity.bind(on_activity_result=on_activity_result)
        intent = Intent()
        intent.setAction(Intent.ACTION_OPEN_DOCUMENT_TREE)
        intent.addFlags(Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
        intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION)
        #intent.addFlags(Intent.FLAG_GRANT_PREFIX_URI_PERMISSION)
        currentActivity.startActivityForResult(intent, RESULT_LOAD_FILE)

    def on_config_change(self, config, section, key, value):
        self.my_app.load_settings()
        if key == 'lib_path_change':
          self.user_select_folder(config)
        if key == 'lib_path':
          self.my_app.populate_library()
        if key == 'temp_dir_path':
          try:
            if not os.path.exists(os.path.join(value, 'tmp')):
              os.makedirs(os.path.join(value, 'tmp'), 0o700)
            config.set('general', 'temp_dir_path', os.path.join(value, 'tmp'))
            config.write()
            for child in self.settings.interface.children:
              if str(type(child)) == "<class 'kivy.uix.tabbedpanel.TabbedPanel'>":
                for child2 in child.children:
                  if str(type(child2)) == "<class 'kivy.uix.tabbedpanel.TabbedPanelContent'>":
                    for child3 in child2.children:
                      for child4 in child3.children:
                        for child5 in child4.children:
                          if str(type(child5)) == "<class '__main__.SettingIconPath'>":
                            if child5.key == 'temp_dir_path':
                              child5.value = os.path.join(value, 'tmp')
          except Exception as inst:
            print("Exception: %s" % inst)
            config.set('general', 'temp_dir_path', self.tempdir)
            config.set('general', 'use_temp_dir', 0)
            config.write()
            for child in self.settings.interface.children:
              if str(type(child)) == "<class 'kivy.uix.tabbedpanel.TabbedPanel'>":
                for child2 in child.children:
                  if str(type(child2)) == "<class 'kivy.uix.tabbedpanel.TabbedPanelContent'>":
                    for child3 in child2.children:
                      for child4 in child3.children:
                        for child5 in child4.children:
                          if str(type(child5)) == "<class 'kivy.uix.settings.SettingBoolean'>":
                            if child5.key == 'use_temp_dir':
                              child5.value = 0
                          if str(type(child5)) == "<class '__main__.SettingIconPath'>":
                            if child5.key == 'temp_dir_path':
                              child5.disabled = True
                              child5.value = self.tempdir
        if key == 'use_temp_dir':
          for child in self.settings.interface.children:
            if str(type(child)) == "<class 'kivy.uix.tabbedpanel.TabbedPanel'>":
              for child2 in child.children:
                if str(type(child2)) == "<class 'kivy.uix.tabbedpanel.TabbedPanelContent'>":
                  for child3 in child2.children:
                    for child4 in child3.children:
                      for child5 in child4.children:
                        if str(type(child5)) == "<class '__main__.SettingIconPath'>":
                          if child5.key == 'temp_dir_path':
                            if value == '0':
                              child5.disabled = True
                            else:
                              child5.disabled = False

        if key == 'iconset':
          if self.my_app.toolbar_shown:
            self.my_app.hide_toolbar()
            self.my_app.show_toolbar()
          self.my_app.library_dialog.icon_set = self.my_app.conf_iconset

        if key == 'lock_page':
          self.my_app.conf_lock_page = value
          if value == '0':
            self.my_app.ids.scatter.do_scale = True
            self.my_app.ids.scatter.do_translation = True
          else:
            self.my_app.ids.scatter.do_scale = False
            self.my_app.ids.scatter.do_translation = False

        if not self.my_app.library_dialog.library_shown:
          if key in ['normal_font', 'strong_font', 'emphasis_font', 'code_font', 'commentary_font']:
            if not self.my_app.ids.text_layer_label.text.endswith('#'):
              self.my_app.load_page()
              self.my_app.page_in()
          if key in ['max_image', 'resize_filter']:
            self.my_app.load_page()
            self.my_app.page_in()

if __name__ == '__main__':
    ACBFaApp().run()

