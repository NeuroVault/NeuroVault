FROM python:2.7
ENV PYTHONUNBUFFERED 1
RUN apt-get update && apt-get install -y \
    libopenblas-dev \
    gfortran \
    libhdf5-dev
RUN pip install numpy \
    cython 
RUN pip install scipy
RUN mkdir /code
WORKDIR /code
ADD requirements.txt /code/
RUN pip install git+https://github.com/gallantlab/pycortex.git#egg=pycortex --egg
RUN pip install -r requirements.txt
ADD . /code/
