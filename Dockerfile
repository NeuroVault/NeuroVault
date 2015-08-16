FROM python:2.7
ENV PYTHONUNBUFFERED 1
RUN apt-get update && apt-get install -y \
    libopenblas-dev \
    gfortran \
    libhdf5-dev

RUN pip install numpy \
    cython
RUN pip install -v scipy
RUN pip install scikit-learn pandas h5py matplotlib

RUN pip install https://github.com/gallantlab/pycortex/archive/master.zip --egg

RUN pip install uwsgi

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

ADD . /code/

CMD /code/run_uwsgi.sh

EXPOSE 3031
