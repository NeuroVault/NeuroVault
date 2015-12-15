FROM neurovault/neurovault

RUN wget -qO- ftp://surfer.nmr.mgh.harvard.edu/pub/dist/freesurfer/5.3.0/freesurfer-Linux-centos4_x86_64-stable-pub-v5.3.0.tar.gz | tar zxv -C /opt --exclude='freesurfer/subjects/bert' --exclude='freesurfer/trctrain' --exclude='freesurfer/subjects/fsaverage_sym' --exclude='freesurfer/subjects/fsaverage3' --exclude='freesurfer/subjects/fsaverage4' --exclude='freesurfer/subjects/fsaverage5' --exclude='freesurfer/subjects/fsaverage6' --exclude='freesurfer/subjects/cvs_avg35' --exclude='freesurfer/subjects/cvs_avg35_inMNI152' --exclude='freesurfer/subjects/lh.EC_average' --exclude='freesurfer/subjects/rh.EC_average' --exclude='freesurfer/average/mult-comp-cor' --exclude='freesurfer/subjects/V1_average'

ENV FREESURFER_HOME /opt/freesurfer
ENV FS_FREESURFERENV_NO_OUTPUT 1
RUN /bin/bash -c "source $FREESURFER_HOME/FreeSurferEnv.sh"

RUN /bin/bash -c 'echo "krzysztof.gorgolewski@gmail.com\n5172\n *CvumvEV3zTfg" > /opt/freesurfer/.license'

RUN svn export --force https://github.com/NeuroVault/neurovault_data/trunk/pycortex_datastore /usr/local/share/pycortex/

RUN apt-get update && apt-get -y install tcsh libglu1-mesa libxmu6

RUN /opt/freesurfer/bin/mri_convert /opt/freesurfer/subjects/fsaverage/mri/brain.mgz /opt/freesurfer/subjects/fsaverage/mri/brain.nii.gz

RUN mkdir /usr/local/share/pycortex/db/fsaverage/transforms/

RUN pip install tornado
