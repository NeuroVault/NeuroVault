FROM continuumio/anaconda
ENV PYTHONUNBUFFERED 1
RUN apt-get update && apt-get install -y default-jre

RUN conda install --yes atlas numpy scipy pandas cython scikit-learn scikit-image matplotlib h5py lxml numexpr hdf5


RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/

RUN pip install git+https://github.com/gallantlab/pycortex.git#egg=pycortex --egg
RUN pip install -r requirements.txt

RUN wget -O /tmp/toolbox-0.6.1-release.zip http://search.maven.org/remotecontent?filepath=org/openprovenance/prov/toolbox/0.6.1/toolbox-0.6.1-release.zip
RUN apt-get install -y unzip
RUN unzip /tmp/toolbox-0.6.1-release.zip -d /opt
ENV PATH /opt/provToolbox/bin:$PATH
RUN apt-get -y remove unzip
RUN rm -rf /tmp/toolbox-0.6.1-release.zip

RUN apt-get autoremove -y
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ADD . /code/
