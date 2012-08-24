AC_INIT([gnome-abrt], [0.2],
        [crash-catcher@fedorahosted.org])

AC_CONFIG_MACRO_DIR([m4])
AM_INIT_AUTOMAKE([-Wall])
AM_MAINTAINER_MODE

AC_DISABLE_STATIC
AC_PROG_CC
AC_GNU_SOURCE
AC_PROG_LIBTOOL

AM_PATH_PYTHON([2.7])
#AX_PYTHON_MODULE([rpm], [1])
#AX_PYTHON_MODULE([rpmUtils.miscutils], [1])

AC_PATH_PROGS(BASH, sh bash)

# Manual pages.
AC_PATH_PROG([ASCIIDOC], [asciidoc], [no])
[if test "$ASCIIDOC" = "no"]
[then]
    [echo "The asciidoc program was not found in the search path. Please ensure"]
    [echo "that it is installed and its directory is included in the search path."]
    [echo "Then run configure again before attempting to build faf."]
    [exit 1]
[fi]

# Manual pages.
AC_PATH_PROG([XMLTO], [xmlto], [no])
[if test "$XMLTO" = "no"]
[then]
    [echo "The xmlto program was not found in the search path. Please ensure"]
    [echo "that it is installed and its directory is included in the search path."]
    [echo "Then run configure again before attempting to build faf."]
    [exit 1]
[fi]

# make check
AC_PATH_PROG([PYLINT], [pylint], [no])
[if test "$PYLINT" = "no"]
[then]
    [echo "The pylint program was not found in the search path. Please ensure"]
    [echo "that it is installed and its directory is included in the search path."]
    [echo "Then run configure again before attempting to build faf."]
    [exit 1]
[fi]

dnl ****** INTERNATIONALIZATION **********************

GETTEXT_PACKAGE=gnome-abrt
AC_SUBST(GETTEXT_PACKAGE)
AC_DEFINE_UNQUOTED(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", [Package name for gettext])

AM_GNU_GETTEXT([external])
AM_GNU_GETTEXT_VERSION([0.17])

IT_PROG_INTLTOOL([0.35.0])

dnl ****** END ****************************************

dnl PKG_CHECK_MODULES([PYXDG], [pyxdg >= 0.19])
dnl PKG_CHECK_MODULES([PYGOBJECT3], [pygobject3 >= 3.2.2])
dnl PKG_CHECK_MODULES([LIBREPORT_PYTHON], [libreport-python])

AC_CONFIG_FILES([
    gnome-abrt.spec
    Makefile
    doc/Makefile
    src/Makefile
    src/gnome_abrt/Makefile
    po/Makefile.in
])

AC_OUTPUT
