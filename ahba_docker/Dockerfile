FROM python:2.7.15-jessie
ENV PYTHONUNBUFFERED 1

RUN sed -i '/jessie-updates/d' /etc/apt/sources.list  # Now archived

RUN apt-get update && apt-get install -y \
    libhdf5-dev \
    libhdf5-8 && \
    apt-get clean autoclean

RUN pip install numpy==1.11.0
RUN pip install nibabel \
                tables==3.3.0 \
                h5py==2.6.0 \
                pandas==0.20.3 \
                pybraincompare==0.1.18

RUN mkdir /code
WORKDIR /code

ADD preparing_AHBA_data.py /code/scripts/preparing_AHBA_data.py
RUN python /code/scripts/preparing_AHBA_data.py
