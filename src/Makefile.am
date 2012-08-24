SUBDIRS = gnome_abrt

bin_SCRIPTS=gnome-abrt

@INTLTOOL_DESKTOP_RULE@
desktopdir = $(datadir)/applications
desktop_in_files = gnome-abrt.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)

EXTRA_DIST = $(bin_SCRIPTS) $(desktop_in_files)
