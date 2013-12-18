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
	l10n.py

controller.py: controller.py.in Makefile
	sed -e s,\@libexecdir\@,$(libexecdir),g $< > $@

__init__.py: __init__.py.in Makefile
	sed -e s,\@PACKAGE\@,$(PACKAGE),g \
	-e s,\@VERSION\@,$(VERSION),g \
	-e s,\@GNOME_ABRT_UI_DIR\@,$(uidir),g \
	-e s,\@localedir\@,$(localedir),g $< > $@

dist_ui_DATA = oops.glade
uidir = $(pkgdatadir)/ui

gnome_abrtdir = $(pythondir)/gnome_abrt

EXTRA_DIST = __init__.py.in oops.glade controller.py.in

DISTCLEANFILES = __init__.py controller.py

all-local: __init__.py controller.py

check-local: $(gnome_abrtexec_PYTHON)
if USE_PYLINT
	$(PYLINT) --rcfile=$(top_builddir)/pylintrc $(abs_builddir)
endif
