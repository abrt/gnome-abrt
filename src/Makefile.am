SUBDIRS = gnome_abrt

bin_SCRIPTS=gnome-abrt

appdatadir = $(datadir)/metainfo
app_data_in_files = gnome-abrt.appdata.xml.in
appdata_DATA = $(app_data_in_files:.xml.in=.xml)

$(app_data_in_files:.xml.in=.xml): $(app_data_in_files)
	$(AM_V_GEN) $(MSGFMT) --xml --template $< -d $(top_srcdir)/po -o $@

desktopdir = $(datadir)/applications
desktop_in_files = gnome-abrt.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)

$(desktop_in_files:.desktop.in=.desktop): $(desktop_in_files)
	$(AM_V_GEN) $(MSGFMT) --desktop --template $< -d $(top_srcdir)/po -o $@

CLEANFILES = \
	$(app_data_in_files:.xml.in=.xml) \
	$(desktop_in_files:.desktop.in=.desktop)

EXTRA_DIST = $(bin_SCRIPTS) $(desktop_in_files) $(app_data_in_files)

check-local: $(bin_SCRIPTS)
if USE_PYLINT
	PYLINT=$(PYLINT) PYLINTRC=$(top_builddir)/pylintrc $(top_builddir)/runpylint.sh $^
endif
