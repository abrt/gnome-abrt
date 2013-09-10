SUBDIRS = gnome_abrt

bin_SCRIPTS=gnome-abrt

@INTLTOOL_XML_RULE@

appdatadir = $(datadir)/appdata
app_data_in_files = gnome-abrt.appdata.xml.in
appdata_DATA = $(app_data_in_files:.xml.in=.xml)

@INTLTOOL_DESKTOP_RULE@

desktopdir = $(datadir)/applications
desktop_in_files = gnome-abrt.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)

EXTRA_DIST = $(bin_SCRIPTS) $(desktop_in_files) $(app_data_in_files)

check-local: $(bin_SCRIPTS)
if USE_PYLINT
	$(PYLINT) --rcfile=$(top_builddir)/pylintrc $^
endif
