FROM neurovault/ahba

RUN apt-get update && apt-get install -y \
    libopenblas-dev \
    gfortran \
    libhdf5-dev \
    libhdf5-8 \
    libgeos-dev

RUN pip install --upgrade pip

RUN pip install numpy==1.11.0
RUN pip install cython \
                scipy \
                scikit-learn==0.17.1 \
                pandas==0.20.3 \
                h5py==2.6.0 \
                matplotlib==1.5.1 \
                scikit-image==0.12.3 \ celery[redis]==3.1.24 \
                certifi==2015.04.28 \
                cognitiveatlas \
                'Django==1.8.8' \
                djangorestframework==3.4.7 \
                django-celery \
                django-chosen \
                django-cleanup==0.4.2 \
                git+git://github.com/maraujop/django-crispy-forms.git@bc3a520dffafac3613631fb95ec1a8bab53c1160#egg=django-crispy-forms \
                django-datatables-view \
                'django-dbbackup<2.3' \
                django-dirtyfields \
                django-file-resubmit==0.4.3 \
                django-filter==1.1.0 \
                django-fixture-media \
                django-form-utils \
                'django-hstore==1.4.1' \
                'django-oauth-toolkit==0.10.0' \
                django-polymorphic==0.9.2 \
                django-sendfile \
                django-taggit==0.22.2 \
                django-taggit-templatetags \
                django-mailgun \
                'dropbox==1.6' \
                hamlpy \
                lxml \
                markdown \
                networkx \
                nibabel==2.1.0 \
                nidmresults==0.3.2 \
                nidmfsl==0.3.4 \
                nilearn==0.4.2 \
                numexpr \
                raven==6.9.0 \
                Pillow==4.1.1 \
                psycopg2==2.7.3.2 \
                pybraincompare==0.1.18 \
                python-openid \
                'python-social-auth==0.2.13' \
                'rdflib>=4.1.0' \
                requests \
                requests-oauthlib \
                shapely \
                uwsgi \
                zipstream \
                html5lib \
                https://github.com/gallantlab/pycortex/archive/fe58400c8c3a3187d930b8a696cda8fec62c0f19.zip \
                git+https://github.com/benkonrath/django-guardian.git@7cded9081249e9a4cd9f5cd85e67cf843c138b0c#egg=django-guardian \
                nidmviewer==0.1.3 \
                git+git://github.com/neurostuff/NiMARE.git@608516ec3034e356326dfe70df5e9ed77efd2be8 \
                tables \
                statsmodels

WORKDIR /code
RUN /usr/bin/yes | pip uninstall cython
RUN apt-get remove -y gfortran

RUN apt-get autoremove -y
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY ahba_docker/subcortex_mask.npy /ahba_data/subcortex_mask.npy

EXPOSE 3031
