gnome_abrt_wrappers_sources = [
  '__init__.py',
]

foreach file: gnome_abrt_wrappers_sources
  configure_file(
    copy: true,
    input: file,
    output: file,
  )
endforeach

python_installation.install_sources(gnome_abrt_wrappers_sources,
  subdir: 'gnome_abrt/wrappers',
)

gnome_abrt_wrappers_module_sources = [
  'common.h',
  'configure.c',
  'module.c',
  'problem_app.c',
  'problem_details.c',
]

gnome_abrt_wrappers_module = python_installation.extension_module('_wrappers', gnome_abrt_wrappers_module_sources,
  subdir: 'gnome_abrt/wrappers',
  dependencies: [
    abrt_dep,
    gio_dep,
    gtk_dep,
    libreport_gtk_dep,
    pygobject_dep,
    python_dep
  ],
  install: true,
)
