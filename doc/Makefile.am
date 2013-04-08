-include ../config.mak

MAN1_TXT = gnome-abrt.txt

# Manual pages are generated from .txt via Docbook
man1_MANS = ${MAN1_TXT:%.txt=%.1}

SUFFIXES = .txt .xml .1

.xml.1:
	$(XMLTO_SILENT) xmlto man $< 2>&1 | sed '/Note/d'

.txt.xml:
	$(ASCIIDOC_SILENT) asciidoc --backend=docbook --doctype=manpage \
									  --conf-file ../asciidoc.conf \
									  -aabrt_version=$(PACKAGE_VERSION) -o $@ $<

EXTRA_DIST = $(MAN1_TXT)

CLEANFILES = $(man1_MANS)
