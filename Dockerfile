FROM python:2.7
ENV PYTHONUNBUFFERED 1
RUN apt-get update && apt-get install -y \
    libopenblas-dev \
    gfortran \
    libhdf5-dev \
	default-jre
RUN pip install numpy \
    cython 
RUN pip install scipy
RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip install git+https://github.com/gallantlab/pycortex.git#egg=pycortex --egg
RUN pip install -r requirements.txt
RUN wget -O /tmp/toolbox-0.6.1-release.zip http://search.maven.org/remotecontent?filepath=org/openprovenance/prov/toolbox/0.6.1/toolbox-0.6.1-release.zip
RUN apt-get install -y unzip
RUN unzip /tmp/toolbox-0.6.1-release.zip -d /opt
RUN apt-get -y remove unzip
RUN rm -rf /tmp/toolbox-0.6.1-release.zip
ENV PATH "/opt/provToolbox/bin:$PATH"
ADD . /code/
