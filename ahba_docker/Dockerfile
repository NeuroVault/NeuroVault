FROM python:2.7.15-jessie
ENV PYTHONUNBUFFERED 1

RUN sed -i '/jessie-updates/d' /etc/apt/sources.list  # Now archived

RUN apt-get update && apt-get install -y \
    libhdf5-dev \
    libhdf5-8 && \
    apt-get clean autoclean

RUN pip install numpy
RUN pip install nibabel
RUN pip install tables==3.3.0
RUN pip install h5py
RUN pip install pandas==0.20.3
RUN pip install pybraincompare==0.1.18

RUN mkdir /code
WORKDIR /code

ADD preparing_AHBA_data.py /code/scripts/preparing_AHBA_data.py
RUN python /code/scripts/preparing_AHBA_data.py
