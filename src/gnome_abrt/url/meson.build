gnome_abrt_url_sources = [
  '__init__.py',
  'urltitle.py',
  'gliburltitle.py',
]

foreach file: gnome_abrt_url_sources
  configure_file(
    copy: true,
    input: file,
    output: file,
  )
endforeach

python_installation.install_sources(gnome_abrt_url_sources,
  subdir: 'gnome_abrt/url',
)
