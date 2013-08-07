wrappersexecdir = $(pyexecdir)/gnome_abrt/wrappers

wrappersexec_PYTHON =  __init__.py

wrappersexec_LTLIBRARIES = _wrappers.la

_wrappers_la_SOURCES = \
    module.c \
    configure.c \
    common.h

_wrappers_la_CPPFLAGS = \
    $(CFLAGS) \
    $(GLIB_CFLAGS) \
    $(PYTHON_CFLAGS) \
    $(PYGOBJECT3_CFLAGS) \
    $(GTK_CFLAGS) \
    $(LIBREPORT_GTK_CFLAGS) \
    $(ABRT_GUI_CFLAGS)

_wrappers_la_LDFLAGS = \
    $(LIBREPORT_GTK_LIBS) \
    $(ABRT_GUI_LIBS) \
    $(GTK_LIBS) \
    $(PYGOBJECT3_LIBS) \
    -module \
    -avoid-version \
    -export-symbols-regex init_wrappers

_wrappers.so: $(wrappersexec_LTLIBRARIES)
	cp .libs/$@ ./

all-local: _wrappers.so

clean-local:
	rm -rf _wrappers.so
