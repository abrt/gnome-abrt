project('gnome-abrt', 'c', meson_version : '>= 0.51.0', license : 'GPL3+', version : '1.4.0')

bindir = get_option('bindir')
datadir = get_option('datadir')
icondir = join_paths(datadir, 'icons')
libexecdir = get_option('libexecdir')
localedir = get_option('localedir')
mandir = get_option('mandir')
pkgdatadir = join_paths(datadir, meson.project_name())
prefix = get_option('prefix')

gnome = import('gnome')
i18n = import('i18n')
python = import('python')

python_modules = []
if get_option('lint')
  python_modules += 'pylint'
endif

python_installation = python.find_installation('python3',
  modules: python_modules
)

abrt_dep = dependency('abrt')
gio_dep = dependency('gio-2.0')
gtk_dep = dependency('gtk+-3.0')
libreport_gtk_dep = dependency('libreport-gtk')
pygobject_dep = dependency('pygobject-3.0', version: '>= 3.29.1')
python_dep = dependency('python3')

asciidoc = find_program('asciidoc',
  required: get_option('docs'),
)
if get_option('lint')
  pylint = find_program('pylint-3')
else
  pylint = disabler()
endif
tito = find_program('tito',
  required: false,
  disabler: true,
)
xmlto = find_program('xmlto',
  required: get_option('docs')
)

subdir('data')
subdir('doc')
subdir('icons')
subdir('po')
subdir('src')

# This will, naturally, fail if the build directory is outside the git repo,
# since Tito does not provide a way to specify the working directory or the spec
# file using the CLI.
run_target('rpm',
  command: [
    tito,
    'build',
    '--offline',
    '--output=@0@/rpm'.format(meson.current_build_dir()),
    '--rpm',
    '--test'
  ],
)
run_target('srpm',
  command: [
    tito,
    'build',
    '--offline',
    '--output=@0@/rpm'.format(meson.current_build_dir()),
    '--srpm',
    '--test'
  ],
)

run_target('run',
  command: [
    gnome_abrt_main,
  ],
  depends: [
    gnome_abrt_resources,
    gnome_abrt_wrappers_module,
  ],
)
