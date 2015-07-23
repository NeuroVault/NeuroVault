
# Pycortex static data is deployed by collectstatic at build time.
STATICFILES_DIRS = (
    ('pycortex-resources', '/usr/local/lib/python2.7/site-packages/cortex/webgl/resources'),
    ('pycortex-ctmcache', '/usr/local/share/pycortex/db/fsaverage/cache'),
)
