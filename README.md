Advanced Comic Book Format (ACBF) specification is a distribution and interchange format for digital comic books. ACBF specification defines a means of representing structured and semanticaly enhanced content used in comic books. In contrast to widely used Comic Book Archive (CBR, CBZ …), format defines comic structure and content can be represented in separate graphic and text translation layer(s) as well as comic book metadata is present.

Some of the properties of ACBF are:
* Definition of comic book metadata (title, authors, genres ...)
* Definition of comic book structure (pages, frames) as well as order in which they follow
* Indexing of comic book pages (creation of Table of Contents upon page title)
* Definition of text layer separate from background graphics as well as reading order of text areas in it
* Definition of semantics on the text layer (e.g. emphasis, code, speech, commentary …)
* Support for more text layers in one document (translations to different languages)

ACBF aims to be used as a digital comic book format that is able to properly represent any comic books content and at the same time be suitable for automatic processing, indexing, comic book collection management and conversion into other formats.

ACBF is an extension of XML. Some inspiration regarding meta-data and semantics of the text layer comes from Fictionbook (file format that is used for electronic books distribution) and ACV 2 (comic book format used by Droid Comic Viewer).

ACBF does not use any kind of DRM (Digital Rights Management) and all specifications are open.

Besides XML Schema definition and comic book files examples, this project maintains several other tools:

* ACBF Viewer - is a viewer application capable of reading ACBF and CBZ file formats. It is written in python. Currently there are versions for Linux and Windows.
* ACBF Editor - is an editor capable of creating CBZ archives with ACBF files inside. It is written in python. Currently there are versions for Linux and Windows.
* ACBF Viewer for Android - is a port of ACBF Viewer to Android platform. It is written in python and using Kivy framework to handle user interface.

Wiki pages are available at: https://acbf.fandom.com/wiki/Advanced_Comic_Book_Format_Wiki

