configuration = configuration_data()

configuration.set('libexecdir', join_paths(prefix, libexecdir))
configuration.set('localedir', join_paths(prefix, localedir))
configuration.set('PACKAGE', meson.project_name())
configuration.set('PKGDATADIR', join_paths(prefix, pkgdatadir))
configuration.set('VERSION', meson.project_version())

gnome_abrt_generated_sources = [
  configure_file(
    configuration: configuration,
    input: '__init__.py.in',
    output: '__init__.py',
  ),
  configure_file(
    configuration: configuration,
    input: 'controller.py.in',
    output: 'controller.py',
  ),
]

gnome_abrt_sources = [
  'config.py',
  'dbus_problems.py',
  'errors.py',
  'problems.py',
  'signals.py',
  'views.py',
  'l10n.py',
]

foreach file: gnome_abrt_sources
  configure_file(
    copy: true,
    input: file,
    output: file,
  )
endforeach

python_installation.install_sources(gnome_abrt_generated_sources + gnome_abrt_sources,
  pure: false,
  subdir: 'gnome_abrt',
)

subdir('wrappers')
