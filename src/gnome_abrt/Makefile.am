SUBDIRS = wrappers url

gnome_abrtexecdir = $(pyexecdir)/gnome_abrt

gnome_abrtexec_PYTHON = \
	__init__.py \
	application.py \
	config.py \
	controller.py \
	dbus_problems.py \
	dialogs.py \
	directory_problems.py \
	errors.py \
	problems.py \
	signals.py \
	tools.py \
	views.py \
	l10n.py \
	gnome_abrt_glade.py

controller.py: controller.py.in Makefile
	sed -e s,\@libexecdir\@,$(libexecdir),g $< > $@

__init__.py: __init__.py.in Makefile
	sed -e s,\@PACKAGE\@,$(PACKAGE),g \
	-e s,\@VERSION\@,$(VERSION),g \
	-e s,\@localedir\@,$(localedir),g $< > $@

gnome_abrt_glade.py: oops.glade Makefile
	{ \
	  echo '# coding=utf-8'; \
	  echo 'GNOME_ABRT_GLADE_CONTENTS ="\'; \
	  cat oops.glade | sed -e 's/\"/\\\"/g' -e 's/$$/\\/'; \
	  echo '"'; \
	} >gnome_abrt_glade.py

gnome_abrtdir = $(pythondir)/gnome_abrt

EXTRA_DIST = __init__.py.in oops.glade controller.py.in

DISTCLEANFILES = __init__.py controller.py gnome_abrt_glade.py

all-local: __init__.py controller.py gnome_abrt_glade.py

check-local: $(gnome_abrtexec_PYTHON)
if USE_PYLINT
	$(PYLINT) --rcfile=$(top_builddir)/pylintrc $(abs_builddir)
endif
