FROM python:2.7
ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y \
    libhdf5-dev \
    libhdf5-8 && \
    apt-get clean autoclean && \
    rm -rf /var/lib/apt /var/lib/dpkg /var/lib/cache /var/lib/log

RUN pip install numpy
RUN pip install nibabel
RUN pip install tables
RUN pip install h5py
RUN pip install pandas
RUN pip install pybraincompare

RUN mkdir /code
WORKDIR /code

ADD preparing_AHBA_data.py /code/scripts/preparing_AHBA_data.py
RUN python /code/scripts/preparing_AHBA_data.py