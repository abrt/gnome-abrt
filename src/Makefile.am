bin_SCRIPTS=gnome-abrt

gnome_abrt_PYTHON = \
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
	gnome_abrt_glade.py

gnome_abrt_glade.py : oops.glade
	{ \
	  echo '# coding=utf-8'; \
	  echo 'GNOME_ABRT_GLADE_CONTENTS ="\'; \
	  cat oops.glade | sed -e 's/\"/\\\"/g' -e 's/$$/\\/'; \
	  echo '"'; \
	} >gnome_abrt_glade.py

gnome_abrtdir = $(pythondir)/gnome-abrt

EXTRA_DIST = oops.glade $(gnome_abrt_PYTHON) $(bin_SCRIPTS)
