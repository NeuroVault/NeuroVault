FROM python:2.7
ENV PYTHONUNBUFFERED 1
RUN apt-get update && apt-get install -y \
    libopenblas-dev \
    gfortran \
    libhdf5-dev \
    libgeos-dev

RUN pip install numpy \
    cython
RUN pip install -v scipy
RUN pip install scikit-learn pandas h5py matplotlib
RUN pip install https://github.com/gallantlab/pycortex/archive/master.zip --egg
RUN pip install uwsgi
RUN pip install 'Django>=1.7.1,<1.8'
RUN pip install 'python-social-auth==0.2.7'
RUN pip install djangorestframework
RUN pip install markdown
RUN pip install django-filter
RUN pip install django-taggit
RUN pip install django-form-utils
RUN pip install hamlpy
RUN pip install django-crispy-forms
RUN pip install django-coffeescript
RUN pip install South
RUN pip install django-taggit-templatetags
RUN pip install django-dirtyfields
RUN pip install 'dropbox==1.6'
RUN pip install 'django-dbbackup<2.3'
RUN pip install numpy
RUN pip install nibabel
RUN pip install psycopg2
RUN pip install cython
RUN pip install h5py
RUN pip install matplotlib
RUN pip install scipy
RUN pip install numexpr
RUN pip install lxml
RUN pip install shapely
RUN pip install Pillow
RUN pip install requests
RUN pip install requests-oauthlib
RUN pip install python-openid
RUN pip install django-sendfile
RUN pip install django-polymorphic
RUN pip install networkx
RUN pip install 'rdflib>=4.1.0'
RUN pip install celery[redis]
RUN pip install django-celery
RUN pip install scikit-learn
RUN pip install nilearn
RUN pip install https://github.com/vsoch/pybraincompare/archive/v1.0.zip
RUN pip install django-cleanup==0.4.1
RUN pip install django-chosen
RUN pip install 'git+https://github.com/sinnwerkstatt/django-file-resubmit.git#egg=file_resubmit'
RUN pip install nidmfsl
RUN pip install opbeat
RUN pip install djrill
RUN pip install 'django-hstore==1.3.5'
RUN pip install cognitiveatlas
RUN pip install django-datatables-view
RUN pip install 'git+git://github.com/vsoch/nidmviewer.git@0.1'
RUN pip install https://github.com/benkonrath/django-guardian/archive/django-polymorphic.zip
RUN pip install 'django-oauth-toolkit==0.9.0'
RUN pip install certifi==2015.04.28

RUN apt-get install -y npm
RUN ln -s /usr/bin/nodejs /usr/bin/node
RUN npm install -g coffee-script

RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip install -r requirements.txt
RUN /usr/bin/yes | pip uninstall cython
RUN apt-get remove -y gfortran

RUN apt-get autoremove -y
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

EXPOSE 3031
