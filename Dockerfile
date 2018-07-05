FROM neurovault/ahba

RUN apt-get update && apt-get install -y \
    libopenblas-dev \
    gfortran \
    libhdf5-dev \
    libhdf5-8 \
    libgeos-dev

RUN pip install --upgrade pip

# copy requirements.txt into container so RUN can find it
ADD requirements.txt /code/
RUN pip install -r /code/requirements.txt

WORKDIR /code
RUN /usr/bin/yes | pip uninstall cython
RUN apt-get remove -y gfortran

RUN apt-get autoremove -y
RUN apt-get clean
RUN rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

COPY ahba_docker/subcortex_mask.npy /ahba_data/subcortex_mask.npy

EXPOSE 3031
