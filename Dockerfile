FROM neurovault/ahba:conda

RUN conda install numpy
RUN conda install cython scipy
RUN conda install scikit-learn pandas h5py matplotlib

RUN pip install celery[redis]
RUN pip install certifi==2015.04.28
RUN pip install cognitiveatlas
RUN pip install 'Django==1.8.8'
RUN pip install djangorestframework==3.4.7
RUN pip install django-celery
RUN pip install django-chosen
RUN pip install django-cleanup==0.4.2
RUN pip install django-coffeescript
RUN pip install django-crispy-forms
RUN pip install django-datatables-view
RUN pip install django-dirtyfields
RUN pip install django-file-resubmit==0.4.3
RUN pip install django-filter
RUN pip install django-fixture-media
RUN pip install django-form-utils
RUN pip install 'django-hstore==1.4.1'
RUN pip install 'django-oauth-toolkit==0.10.0'
RUN pip install django-polymorphic==0.9.2
RUN pip install django-sendfile
RUN pip install django-taggit
RUN pip install django-taggit-templatetags
RUN pip install django-mailgun
RUN pip install hamlpy
RUN conda install lxml
RUN pip install markdown
RUN conda install networkx
RUN pip install nibabel
RUN pip install nidmresults==0.3.2
RUN pip install nidmfsl==0.3.4
RUN pip install nilearn
RUN conda install numexpr
RUN pip install opbeat
RUN pip install Pillow
RUN conda install psycopg2
RUN pip install pybraincompare==0.1.18
RUN pip install python-openid
RUN pip install 'python-social-auth==0.2.13'
RUN pip install 'rdflib>=4.1.0'
RUN pip install requests
RUN pip install requests-oauthlib
RUN conda install -c scitools shapely
RUN apt-get update -y && apt-get install -y build-essential && \
    pip install uwsgi && \
    apt-get remove -y build-essential && \
    apt-get -y autoremove
RUN pip install zipstream

RUN apt-get update -y && apt-get install -y build-essential && \
    pip install https://github.com/gallantlab/pycortex/archive/fe58400c8c3a3187d930b8a696cda8fec62c0f19.zip --egg && \
    apt-get remove -y build-essential && \
    apt-get -y autoremove
RUN pip install git+https://github.com/benkonrath/django-guardian.git@7cded9081249e9a4cd9f5cd85e67cf843c138b0c#egg=django-guardian
RUN pip install nidmviewer==0.1.3

RUN conda install pytables
RUN conda install statsmodels

RUN apt-get update
RUN apt-get install -y npm
RUN ln -s /usr/bin/nodejs /usr/bin/node
RUN npm install -g coffee-script

RUN mkdir -p /code
WORKDIR /code

EXPOSE 3031
