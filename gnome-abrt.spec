# TODO: https://fedoraproject.org/wiki/Packaging:AutoProvidesAndRequiresFiltering
#       rpmlint warns about private-shared-object-provides
#       can't use filter because the package doesn't met any of the required criteria
#         ! Noarch package       ... caused by libreport wrappers shared library
#         ! no binaries in $PATH ... caused by gnome-abrt python script in /usr/bin

# Uncomment when building from a git snapshot.
#%%global snapshot 1
%global commit 3e3512d2d6c81a4ca9b3b4d3f3936c876a6482f7
%global shortcommit %(c=%{commit}; echo ${c:0:7})

Name:       gnome-abrt
Version:    1.4.1
Release:    1%{?snapshot:.git%{shortcommit}}%{?dist}
Summary:    A utility for viewing problems that have occurred with the system

License:    GPLv2+
URL:        https://github.com/abrt/%{name}
%if 0%{?snapshot}
Source0:    %{url}/archive/%{commit}.tar.gz#/%{name}-%{commit}.tar.gz
%else
Source0:    %{url}/archive/%{version}/%{name}-%{version}.tar.gz
%endif

BuildRequires: git-core
BuildRequires: meson >= 0.59.0
BuildRequires: gettext
BuildRequires: libtool
BuildRequires: python3-devel
BuildRequires: desktop-file-utils
BuildRequires: asciidoc
BuildRequires: xmlto
BuildRequires: pygobject3-devel
BuildRequires: libreport-gtk-devel > 2.14.0
BuildRequires: python3-libreport
BuildRequires: abrt-gui-devel > 2.14.0
BuildRequires: gtk3-devel
%if 0%{?fedora}
BuildRequires: python3-pylint
BuildRequires: python3-six
BuildRequires: python3-gobject
BuildRequires: python3-dbus
BuildRequires: python3-humanize
%endif

Requires:   glib2%{?_isa} >= 2.63.2
Requires:   gobject-introspection%{?_isa} >= 1.63.1
Requires:   python3-libreport
Requires:   python3-gobject
Requires:   python3-dbus
Requires:   python3-humanize
Requires:   python3-beautifulsoup4

%description
A GNOME application allows users to browse through detected problems and
provides them with convenient way for managing these problems.


%prep
%autosetup -S git %{?snapshot:-n %{name}%-%{commit}}


%build
%meson \
%if ! 0%{?fedora}
    -Dlint=false \
%endif
    %{nil}
%meson_build


%install
%meson_install

%find_lang %{name}

%check
# do not fail on pylint warnings
%meson_test || :


%files -f %{name}.lang
%doc COPYING README.md
%{python3_sitearch}/gnome_abrt
%{_datadir}/%{name}
%{_bindir}/%{name}
%{_datadir}/applications/*
%{_datadir}/metainfo/*
%{_mandir}/man1/%{name}.1*
%{_datadir}/icons/hicolor/*/apps/*

%changelog
