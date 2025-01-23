FROM python:3.10-slim AS neurovault

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

RUN apt-get update && apt-get install --no-install-recommends -y \
  # dependencies for building Python packages
  build-essential \
  # psycopg2 dependencies
  libpq-dev \
  git

RUN apt-get -y update \
    && apt-get install -y wget subversion && \
    wget -qO- ftp://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/6.0.0/freesurfer-Linux-centos6_x86_64-stable-pub-v6.0.0.tar.gz | tar zxv -C /opt \
    --exclude='freesurfer/trctrain' \
    --exclude='freesurfer/subjects/fsaverage_sym' \
    --exclude='freesurfer/subjects/fsaverage3' \
    --exclude='freesurfer/subjects/fsaverage4' \
    --exclude='freesurfer/subjects/fsaverage5' \
    --exclude='freesurfer/subjects/fsaverage6' \
    --exclude='freesurfer/subjects/fsaverage/xhemi' \
    --exclude='freesurfer/subjects/cvs_avg35' \
    --exclude='freesurfer/subjects/cvs_avg35_inMNI152' \
    --exclude='freesurfer/subjects/bert' \
    --exclude='freesurfer/subjects/V1_average' \
    --exclude='freesurfer/subjects/fsaverage/label' \
    --exclude='freesurfer/average/mult-comp-cor' \
    --exclude='freesurfer/average/aseg+spmhead+vermis+pons.ixi.gca' \
    --exclude='freesurfer/average/RB_all_withskull_2016-05-10.vc700.gca' \
    --exclude='freesurfer/average/RB_all_2016-05-10.vc700.gca' \
    --exclude='freesurfer/average/711*' \
    --exclude='freesurfer/average/SVIP*' \
    --exclude='freesurfer/average/Yeo_Brainmap_MNI152' \
    --exclude='freesurfer/lib/cuda' \
    --exclude='freesurfer/lib/qt' \
    --exclude='freesurfer/lib/vtk' \
    && \
    find /opt/freesurfer/bin -type f ! -name 'tkregister2' ! -name 'mris_convert' ! -name 'mri_surf2surf' ! -name 'mri_surf2vol' -delete && \
    apt-get install -y tcsh bc tar libgomp1 perl-modules curl  && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set up the environment
ENV OS Linux
ENV FS_OVERRIDE 0
ENV FIX_VERTEX_AREA=
ENV SUBJECTS_DIR /opt/freesurfer/subjects
ENV FSF_OUTPUT_FORMAT nii.gz
ENV MNI_DIR /opt/freesurfer/mni
ENV LOCAL_DIR /opt/freesurfer/local
ENV FREESURFER_HOME /opt/freesurfer
ENV FSFAST_HOME /opt/freesurfer/fsfast
ENV MINC_BIN_DIR /opt/freesurfer/mni/bin
ENV MINC_LIB_DIR /opt/freesurfer/mni/lib
ENV MNI_DATAPATH /opt/freesurfer/mni/data
ENV FMRI_ANALYSIS_DIR /opt/freesurfer/fsfast
ENV PERL5LIB /opt/freesurfer/mni/lib/perl5/5.8.5
ENV MNI_PERL5LIB /opt/freesurfer/mni/lib/perl5/5.8.5
ENV PATH /opt/freesurfer/bin:/opt/freesurfer/fsfast/bin:/opt/freesurfer/tktools:/opt/freesurfer/mni/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH
RUN echo "cHJpbnRmICJrcnp5c3p0b2YuZ29yZ29sZXdza2lAZ21haWwuY29tXG41MTcyXG4gKkN2dW12RVYzelRmZ1xuRlM1Si8yYzFhZ2c0RVxuIiA+IC9vcHQvZnJlZXN1cmZlci9saWNlbnNlLnR4dAo=" | base64 -d | sh

RUN git clone --depth 1 https://github.com/NeuroVault/neurovault_data.git /tmp/neurovault_data && \
    cp -r /tmp/neurovault_data/pycortex_datastore /usr/local/share/pycortex/ && \
    rm -rf /tmp/neurovault_data
RUN apt-get update && apt-get -y install tcsh libglu1-mesa libxmu6
RUN /opt/freesurfer/bin/mri_convert /opt/freesurfer/subjects/fsaverage/mri/brain.mgz /opt/freesurfer/subjects/fsaverage/mri/brain.nii.gz
RUN mkdir /usr/local/share/pycortex/db/fsaverage/transforms/
RUN pip install tornado

RUN apt-get update && apt-get -y install zip
RUN wget https://ndownloader.figshare.com/files/6891069 -O icbm.zip && unzip icbm.zip -d /opt/freesurfer/subjects/ && rm icbm.zip

COPY ./compose/django/requirements.txt requirements.txt
RUN pip install -r requirements.txt

WORKDIR /code

EXPOSE 8000
