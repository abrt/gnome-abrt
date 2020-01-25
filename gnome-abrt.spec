# TODO: https://fedoraproject.org/wiki/Packaging:AutoProvidesAndRequiresFiltering
#       rpmlint warns about private-shared-object-provides
#       can't use filter because the package doesn't met any of the required criteria
#         ! Noarch package       ... caused by libreport wrappers shared library
#         ! no binaries in $PATH ... caused by gnome-abrt python script in /usr/bin

Name:       gnome-abrt
Version:    1.2.9
Release:    1%{?dist}
Summary:    A utility for viewing problems that have occurred with the system

License:    GPLv2+
URL:        https://github.com/abrt/gnome-abrt
Source0:    https://github.com/abrt/%{name}/archive/%{version}/%{name}-%{version}.tar.gz

BuildRequires: gettext
BuildRequires: libtool
BuildRequires: python3-devel
BuildRequires: desktop-file-utils
BuildRequires: asciidoc
BuildRequires: xmlto
BuildRequires: pygobject3-devel
BuildRequires: libreport-gtk-devel > 2.4.0
BuildRequires: python3-libreport
BuildRequires: abrt-gui-devel > 2.4.0
BuildRequires: gtk3-devel
%if 0%{?fedora}
BuildRequires: python3-pylint
BuildRequires: python3-six
BuildRequires: python3-inotify
BuildRequires: python3-gobject
BuildRequires: python3-dbus
BuildRequires: python3-humanize
%else
%define checkoption --with-nopylint
%endif

Requires:   python3-libreport
Requires:   python3-inotify
Requires:   python3-gobject
Requires:   python3-dbus
Requires:   python3-humanize

%description
A GNOME application allows users to browse through detected problems and
provides them with convenient way for managing these problems.


%prep
%setup -q


%build
autoconf
%configure %checkoption
%make_build


%install
%make_install
%find_lang %{name}

# remove all .la and .a files
find %{buildroot} -name '*.la' -or -name '*.a' | xargs rm -f

desktop-file-install \
    --dir %{buildroot}%{_datadir}/applications \
    --delete-original \
    %{buildroot}%{_datadir}/applications/org.freedesktop.GnomeAbrt.desktop


%check
# do not fail on pylint warnings
make check || :


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
* Fri Apr 26 2019 Ernestas Kulik <ekulik@redhat.com> - 1.2.8-1
- Update to 1.2.8

* Mon Feb 04 2019 Ernestas Kulik <ekulik@redhat.com> - 1.2.7-1
- Update to 1.2.7

* Fri Apr 27 2018 Rafal Luzynski <digitalfreak@lingonborough.com> - 1.2.6-4
- Change appdata location according to the current guidelines
- Remove "Group:" tag according to the current guidelines

* Sat Jan 06 2018 Igor Gnatenko <ignatenkobrain@fedoraproject.org> - 1.2.6-2
- Remove obsolete scriptlets

* Thu Nov 16 2017 Julius Milan <jmilan@redhat.com> 1.2.6-1
- Translation updates
- build: do not upload tarball to fedorahosted.org
- Satisfy pylint v1.7.1 warnings
- pylintrc: disable pylint no-else-return warnings
- configure.ac: adapt to pylint binary name change on F26
- Add fur, kk, nn languages into LINGUAS
- Translation updates, add new languages fur,kk,nn
- spec: do not use fedorahosted.org as source
- maint: check pulled .po files for errors

* Mon Oct 31 2016 Jakub Filak <jfilak@redhat.com> 1.2.5-1
- Translation updates
- Fix some small issues to please pylint
- Use compatible CSS selectors for both gtk 3.18 and 3.20
- Translation updates
- Update Project URL on the About page
- Update the project URLs in the spec file
- Translation updates
- Fixed crash when calculating offsets to align the buttons

* Tue Jun 07 2016 Jakub Filak <jfilak@redhat.com> 1.2.4-1
- Translation updates
- Add new translation languages - sq
- More translators comments
- One more fix for the format of a package version
- Align the header buttons position to the sidebar size
- Correct format of the package version

* Wed Mar 23 2016 Jakub Filak <jfilak@redhat.com> 1.2.3-1
- Translation updates
- Let main title of the crash wrap
- Label all kernel oops problems with "System"
- Disambiguate the word "System"
- Use context gettext
- Reword "Detected" to "First Detected"
- Use "Problem Reporting" as the program name in the About box
- Remove "Report problem with ABRT"
- Fix dim-label being applied to proper app icons
- Make "Select" button unsensitive when list is empty
- Make titlebar blue in selection mode
- Use dim-label style, not hard-coded colours for labels
- Remove "ABRT Configuration" dialogue
- Add search button
- Add more keywords to .desktop

* Thu Feb 18 2016 Jakub Filak <jfilak@redhat.com> 1.2.2-1
- Translation updates
- Translation updates
- Remove cs_CZ translation
- Do not translate the temporary developer's strings
- Fix the plural/singular translations for fancydate
- Details pane: new design
- add new translation to LINGUAS
- Update translations
- Make the code compatible with Pylint-1.5.2
- Do not pass None to function expecting str object
- Add kudos to the AppData file
- Hook README.md in the spec file
- Tell Automake to not require README
- Update README and CONTRIBUTING
- Problem type included in the problem list
- Scroll whole details panel instead of its single widgets
- Fix broken build caused by pylint warning

* Thu Nov 19 2015 Jakub Filak <jfilak@redhat.com> 1.2.1-1
- Translation updates
- Update zanata client configuration
- Fix Python-3.5 module initialization
- HTMLParseError replaced with generic Exception
- Get rid of the Gtk3 module loading warning
- Remove any remaining references to the old btn_details (header bar)
- trivial: set spacing=6 in box_header for non-GNOME desktops
- fancydate: Handle the singular cases separately
- Don't scroll the sidebar horizontally
- Show HiDPI icons on HiDPI screens
- autogen: use dnf instead of yum to install dependencies
- Translation update
- Translation fix in view.py
- Correct testing of return values from ABRT D-Bus API wrrapper
- Fix an exception when searching for a bug ID
- Fix loading applicaton icons
- Use UTF-8 encoding when working with user files
- Remove the Details button from the top bar in non-GNOME desktops

* Tue Jun 09 2015 Jakub Filak <jfilak@redhat.com> 1.2.0-1
- build: Make the changelog builder more robust
- Fix an error introduced with the details on System page
- Enabled the Details also for the System problems
- Link the module wrappers with libX11
- Add libX11 to BRs
- Use DBus to get problem data for detail dialog
- Test availability of XServer in C wrappers
- Remove a debug print introduced with port to Python3
- Quit Application on Ctrl+Q
- Use valid dir URI in 'Open problem's data directory'
- Translation updates
- Remove deprecated pylint's disabling of warning

* Thu Apr 09 2015 Jakub Filak <jfilak@redhat.com> 1.1.1-1
- Translation updates
- Do not encode the filtered dbus.String to 'UTF-8'
- Do not die if the problem data misses 'cmdline'
- Disable pylint warning for ngettext
- Use correct plurals for n weeks/months/years ago
- Turn of missing member pylint warning for report module
- Use a gettext function returning strings instead of bytes
- Fix a crash when selected problem doesn't have environ
- Fix build dependencies caused by Python3
- Bump the required versions in the spec file
- Fix too long line
- Try to use environment to find the the application
- Add wrapper for problem_create_app_from_env()
- Remove unused code from get_application()
- build: Filter out unimportant commit messages in the changelog builder

* Tue Mar 17 2015 Jakub Filak <jfilak@redhat.com> 1.1.0-1
- Translation updates
- Get rid of pylint warnings
- Updates to the spec file due to Python3
- Port to Python3
- Fix setting application icons
- Fix crasher in the wrappers
- Add ar to LINGUAS
- Use libreport's helper to find the app and icons
- Wrap libreport's problem_create_app_from_cmdline()
- Stop using deprecated widget properties
- po: Remove en-ar from LINGUAS
- Fix typo in comment
- Remove xdg-open usage
- Merge pull request #111 from aboobed/master
- Update ar.po
- Rename ar to ar.po
- Create ar
- Update LINGUAS
- autogen: move configure to the default case
- Add gettext mappings to the zanata config
- Translation updates
- Move from transifex to zanata
- Merge pull request #104 from abrt/gh97_always_show_icon
- Use scalable system-run-symbolic icon
- Move the heading text down
- sidebar - remove double border
- header bar alignment fixes
- Always show an icon for problems
- Merge pull request #95 from abrt/search_by_bug_id
- Search by Bug Tracker ID
- Disable pylint warning for wrong continued indentation
- Translation updates

* Fri Oct 03 2014 Jakub Filak <jfilak@redhat.com> 1.0.0-1
- Disable pylint rule for too many lines in module
- Fix problems with selection when all problems are filtered out
- Enable multiple selection
- Update INSTALL
- Use symbolic icons
- Merge pull request #93 from abrt/gh64_detail_dialog
- Hide the 'Details' button for system problems
- Show technical details for user problems locally
- Make the main window's look more GNOMish
- Make the sidebar wider
- Give the designed look to the sidebar
- Consistently return 'count' as a string
- Try to avoid usage of NoDisplay=True .desktop files
- Merge pull request #89 from hadess/build-fixes
- Merge pull request #88 from hadess/search-bar
- build: Make autogen.sh run configure by default
- Replace GtkSearchEntry with GtkSearchBar
- Update the spec file
- Use human readable dates in main view
- Disable pylint warning for too general Exception
- Improve sidebar dates
- Hide "no" repoted label by default
- Revert "Remove leftover key-press-event on the search entry"
- Fix too long lines
- Use GtkLabel instead of GtkLinkButton
- Use dim-label class instead of RGB
- Merge pull request #81 from elad661/use-search-changed
- Remove leftover key-press-event on the search entry
- Merge pull request #82 from elad661/fix-grammar
- Fix grammar in kernel oopses/crashes summary
- Don't start search on 'Delete' key
- Make "No problems detected" label centered vertically
- Merge pull request #79 from elad661/dont_elipsize_summary
- Merge pull request #80 from elad661/thinner_border
- Make the border between the panes thinner
- Don't elipsize summary, it's more readable if it's wrapped.
- Align "Reports" with the actual label
- Make sidebar date dimmed
- Use "suggested-action" style for "Report" button
- Only show search when activated
- Use GtkSearchEntry for the search text box
- Merge pull request #75 from elad661/patch-1
- Match window title to the desktop launcher name
- Display accurate package name and version
- Fix pylint warnings for long lines
- Don't show technical details in 'Reason' and 'Summary'
- Don't show "hook" type in sidebar
- Keep selection on Right click
- Merge pull request #54 from elad661/patch-1
- Rename desktop launcher to "Problem Reporting"
- Teach the GUI to understand the Exec key format
- Put "About" and "Quit" into a section
- Do not close the report dialog with the main window
- Wrap words in "Report problem with ABRT" dialogue
- Properly handle UTF-8 problem filter input

* Wed Jun 11 2014 Jakub Filak <jfilak@redhat.com> 0.3.7-1
- Fix XDG_RUNTIME_DIR not set messages by creating one
- Handle UTF-8 problem filter input
- Disable "no-member" check in pylintrc
- Fix issues uncovered by a newer version of pylint
- Do not crash in case of a DBus timeout
- Fix too long line
- Ignore problems without 'type' element

* Wed Mar 05 2014 Jakub Filak <jfilak@redhat.com> 0.3.6-1
- Translation updates
- Use human readable type string everywhere
- Display C/C++ instead of CCpp
- Truncate possibly long component name to 40 chars
- Disable horizontal scrollbar on problem list
- Right-alignment of date entries
- Initialize gnome_abrt module before importing its submodules

* Mon Jan 13 2014 Jakub Filak <jfilak@redhat.com> 0.3.5-1
- Do not crash when a FileIcon cant be loaded
- Enable multiple problems selection
- Fix a type in appdata
- Update translations

* Thu Dec 19 2013 Jakub Filak <jfilak@redhat.com> 0.3.4-1
- Do not use deprecated GObject API
- Make gnome-abrt compatible with Python GObject < 3.7.2
- Do not fail if there is no Problem D-Bus service
- Make all labels selectable
- spec: Install UI files
- Fix locales handling
- Run xdg-open for problem directory nonblocking
- Expand list of problems
- Update translations

* Sat Oct 26 2013 Jakub Filak <jfilak@redhat.com> 0.3.3-1
- Make problem list resizable
- Make info about Reported state of problem more clear
- Less confusing message about missing Bugzilla ticket

* Fri Oct 04 2013 Jakub Filak <jfilak@redhat.com> 0.3.2-1
- Fix a bug in SIGCHLD handler causing 100% CPU usage
- Show "yes" in Reported field only if no URL is available
- Load only the most recent reported to value
- Check if Application has valid name in filter fn
- Do not change old selection upon reloading
- Fix issues found by new pylint
- Do not crash on None in signal handler

* Thu Sep 12 2013 Jakub Filak <jfilak@redhat.com> 0.3.1-1
- Improve user experience
- Make About dialog transient for the main window
- Hook up AppData file in spec file
- Add AppData file
- Ship the 256x256 icon in the right place
- Recover from fork errors
- Add abrt_gui to build requires
- Add ABRT configure application menu
- Use absolute path in python shebang
- Fix broken make check
- Temporarily disable URL title retrieval
- Recover from invalid time stamp values
- Use wrapped text for the bug report link

* Fri Jul 26 2013 Jakub Filak <jfilak@redhat.com> 0.3.0-1
- Do not include url files twice
- Get rid of Stock Items usage
- Do not remove invalid problems while sorting the list
- Check if X display can be opened
- Fix a condition in the source changed notification handler
- Update Translations
- Skip inotify events for sub folders in dump location watcher
- Use GLib.io_add_watch() instead of IOChanell.add_watch()
- Fix a typo in macro name
- remove shebang from non-executable scripts
- Remember missing elements and load them only once
- Download more problem elements in a single D-Bus call
- Improve data caching
- Display two sets of problems (My/System)
- Fix typo in dbus error message
- Replace 'exception.message' with just 'exception'
- Don't crash if a new directory problem is invalid
- Make all generated files dependent on configuration

* Fri May 03 2013 Jakub Filak <jfilak@redhat.com> 0.2.12-1
- Use 'N/A' instead of ??
- Use package name is neither component nor executable items are available
- Don't try to select a problem if the list is empty
- Catch InvalidProblem exception in sort function
- Handle DBus initialization errors gracefully
- Show HTML titles of URLs from reported_to element
- updated translation
- Continue in handling of SIGCHLD after the first one is handled
- Merge pull request #22 from Catanzaro/master
- Fix two comma splices
- Fix wrong dialog flag names

* Mon Apr 22 2013 Jakub Filak <jfilak@redhat.com> 0.2.11-1
- Enable pylint check only on Fedora
- Fix bogus dates in chagelog
- Introduce expert mode and show 'Analyze' button in that mode
- Use last occurrence item for problems sorting
- Fix broken keyboard shortcuts
- Fix missing space typo
- Compare all DesktopEntry.*() return values to None
- Display 'component' name instead of 'executable' if desktop file is missing
- Do not show scrollbar for long links
- Allow to disable pylint check in configure.ac
- Merge pull request #19 from clockfort/manpage-fix
- move manpage to volume 1
- Move gnome_abrt module check to module's Makefile
- Disable 'Interface not implemented' pylint warning
- Configure pylint to produce parseable output

* Thu Mar 28 2013 Jakub Filak <jfilak@redhat.com> 0.2.10-1
- Fix a wrong import of GLib.GError
- Fix typos in configure.ac
- Add the report dialog to the menu
- Add 'Report problem with ABRT' dialog
- Add VERSION and PACKAGE attributes to gnome_abrt module
- Rename attribute in errors.InvalidProblem
- Use IOChannel approach in order to make signal handling synchronous
- Add all python Requires to BuildRequires because of pylint
- Replace GNU style make pattern rules by implicit rules
- Remove left-over RELEASE varible from configure.ac
- Recover from DBus errors while sending command line
- Catch more exceptions and handle them correctly
- Add pylint check and fix problems uncoverend by pylint
- Filter out empyt strings from splitted cmdline
- Fix sytanx error
- Change the label "No oopses" to "No problems detected"
- Get rid of scrollbar around the text on the bottom of window in default size
- Fix appearance of scrolled widgets to no longer have white background
- Remove leftover shebang from non-executable script

* Mon Mar 18 2013 Jakub Filak <jfilak@redhat.com> 0.2.9-1
- Truncate long texts with ellipsis instead of auto-adjusting of window width
- Add a popopup menu for list of problems
- Use executable's basename as an application name instead of the full path
- Remove invalid problems from GUI tree view list
- Remove invalid problems from the dbus cache
- Robustize the processing of newly occurred problems
- autogen.sh: stop using bashisms
- Remove a left-over usage of the window member in OopsApplication
- Handle reaching inotify max watches better
- Update translation
- Don't allow reporting if the problem is not reportable
- Suggest reporting a bug if it wasn't reported yet
- Simplify the glade file and add a widget for messages
- Refactorize the function rendering a problem data
- A workaround for the bug in remote GtkApplications
- Allow only a single instance of gnome-abrt
- Fix bugs in main window in handler of configuration updates

* Mon Feb 25 2013 Jakub Filak <jfilak@redhat.com> 0.2.8-1
- Add make release targets
- Always generate controller.py & gnome-abrt-glade.py
- Update the list of required files
- Make gen-version less stupid
- Use $ARGS variable for arguments in 'make run'
- Try harder when looking for icon and don't cache weak results
- Make controller more robust against invalid arguments
- Check return value of the get selection function
- Require correct version of libreport
- Return an empty list instead of None from OopsWindow.get_selected()
- Return an empty list instead of None from get_problems() in case of DBus error
- Get rid of unnecessary variable from the directory source
- Add a cmd line argument for selected problem id

* Fri Feb 08 2013 Jakub Filak <jfilak@redhat.com> - 0.2.7-1
- Fix failure in processing of dump directories from user's home
- Resolves: #908712

* Tue Jan 08 2013 Jakub Filak <jfilak@redhat.com> - 0.2.6-1
- Require libreport version 2.0.20 and greater
- Use DD api correctly
- Reflect changes in libreport

* Wed Nov 28 2012 Jakub Filak <jfilak@redhat.com> - 0.2.5-1
- Add licenses to all files
- Refresh view's source if InvalidProblem exception is caught during GUI update
- Properly handle removal of the first and the last problem from the list
- Use right tree model in searching for problems
- Use theme backround color as background for the link buttons
- Make the links to servers less moving
- Keep user's selection even if a source has changed
- Destroy abrt-handle-event zombies

* Fri Oct 05 2012 Jakub Filak <jfilak@redhat.com> - 0.2.4-1
- Fix label fields size
- Assure ownership of reported problem
- Remove unnecessary GtkEventBox
- Fix appearance of link button widget to no longer have a white background
- Update translations

* Fri Oct 05 2012 Jakub Filak <jfilak@redhat.com> - 0.2.3-1
- Generate version
- Add GNOME3 application menu
- Use correct D-Bus path to listen on for Crash signal
- Make path to abrt-handle-event configurable
- Fix a bug in running of subprocesses
- Refactorize directory problems implementation
- Don't print weired debug message
- Don't show the 'reconnecting to dbus' warning
- Don't show new root's crashes by default
- Fix indentation

* Fri Sep 21 2012 Jakub Filak <jfilak@redhat.com> - 0.2.2-1
- Lazy initialization of directory source
- Don't utilize CPU for 99%
- Code refactorization
- Add translation from the ABRT project
- Properly log exceptions
- Delete directory problems marked as invalid after refresh in inotify handler
- Declare directory problems deleted if its directory doesn't exist
- Fix indentation bug in icon look up algorithm
- Add --verbose command line argument
- Add directory name to error messages

* Mon Sep 17 2012 Jakub Filak <jfilak@redhat.com> - 0.2.1-4
- Fix a problem with desktop items without icons
- A bit better handling of uncaght exceptions

* Mon Sep 17 2012 Jakub Filak <jfilak@redhat.com> - 0.2.1-3
- Add cs and et translations

* Fri Sep 14 2012 Jakub Filak <jfilak@redhat.com> - 0.2.1-2
- Fixed problem with selection of problem after start up
- Corrected application icon look up algorithm
- Fixed problem with missing problems directory

* Fri Sep 14 2012 Jakub Filak <jfilak@redhat.com> - 0.2.1-1
- Detail button replaced by list of reported_to links
- Improved look (margins, icons, wider window by default)
- Implemented multiple delete
- Changed window tiple
- Double click and keyboard shortcuts

* Thu Sep 06 2012 Jakub Filak <jfilak@redhat.com> - 0.2-9
- Remove noarch because of binary wrappers
- Added support for adjusting libreport preferences

* Tue Aug 28 2012 Jakub Filak <jfilak@redhat.com> - 0.2-8
- Take ownership of all installed directories
- Correct paths to translated files

* Mon Aug 27 2012 Jakub Filak <jfilak@redhat.com> - 0.2-7
- Dropped versions from requires
- Simplified spec
- Removed pylint check from configure.ac
- Whitespace cleanup (rmarko@redhat.com)

* Fri Aug 24 2012 Jakub Filak <jfilak@redhat.com> - 0.2-6
- Use own icons set

* Fri Aug 24 2012 Jakub Filak <jfilak@redhat.com> - 0.2-5
- Reorganize source files
- Get rid of all rpmlint complaints

* Thu Aug 23 2012 Jakub Filak <jfilak@redhat.com> - 0.2-4
- Update GUI on various signals (new problem, problem changed, etc.)
- Sort problems by time in descending order
- Correct internationalization in date string generator

* Wed Aug 15 2012 Jakub Filak <jfilak@redhat.com> - 0.2-3
- Reconnect to DBus bus
- Default values for missing items
- Correct field for 'is_reported' flag

* Wed Aug 15 2012 Jakub Filak <jfilak@redhat.com> - 0.2-2
- Add missing files

* Wed Aug 15 2012 Jakub Filak <jfilak@redhat.com> - 0.2-1
- Problems filtering
- Errors handling
- Localization support

* Mon Aug 13 2012 Jakub Filak <jfilak@redhat.com> - 0.1-1
- Initial version
