FROM continuumio/miniconda:4.1.11
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    libhdf5-dev \
    libhdf5-8 && \
    apt-get clean autoclean

RUN conda update conda
RUN conda config --add channels intel
ENV ACCEPT_INTEL_PYTHON_EULA=yes
RUN conda install intelpython2_core
RUN conda install numpy
RUN pip install nibabel
RUN conda install pytables
RUN conda install h5py
RUN conda install pandas
RUN conda install cython
RUN conda install scikit-learn
RUN conda install scikit-image
RUN conda install matplotlib
RUN pip install pydicom
RUN conda install networkx
RUN conda install dask
RUN conda install toolz
RUN pip install pybraincompare==0.1.18

RUN mkdir /code
WORKDIR /code

ADD preparing_AHBA_data.py /code/scripts/preparing_AHBA_data.py
RUN python /code/scripts/preparing_AHBA_data.py