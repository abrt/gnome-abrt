SUBDIRS = wrappers

gnome_abrtexecdir = $(pyexecdir)/gnome_abrt

gnome_abrtexec_PYTHON = \
	__init__.py \
	application.py \
	config.py \
	controller.py \
	dbus_problems.py \
	directory_problems.py \
	errors.py \
	problems.py \
	tools.py \
	views.py \
	l10n.py \
	gnome_abrt_glade.py

controller.py: controller.py.in
	sed -e s,\@libexecdir\@,$(libexecdir),g $< > $@

gnome_abrt_glade.py: oops.glade
	{ \
	  echo '# coding=utf-8'; \
	  echo 'GNOME_ABRT_GLADE_CONTENTS ="\'; \
	  cat oops.glade | sed -e 's/\"/\\\"/g' -e 's/$$/\\/'; \
	  echo '"'; \
	} >gnome_abrt_glade.py

gnome_abrtdir = $(pythondir)/gnome_abrt

EXTRA_DIST = oops.glade controller.py.in

DISTCLEANFILES = controller.py

all-local: controller.py gnome_abrt_glade.py
