-include ../config.mak

MAN6_TXT = gnome-abrt.txt

# Manual pages are generated from .txt via Docbook
man6_MANS = ${MAN6_TXT:%.txt=%.6}

SUFFIXES = .txt .xml .6

.xml.6:
	$(XMLTO_SILENT) xmlto man $< 2>&1 | sed '/Note/d'

.txt.xml:
	$(ASCIIDOC_SILENT) asciidoc --backend=docbook --doctype=manpage \
									  --conf-file ../asciidoc.conf \
									  -aabrt_version=$(PACKAGE_VERSION) -o $@ $<

EXTRA_DIST = $(MAN6_TXT)

CLEANFILES = $(man6_MANS)
