Sources for Docker image with data from Allen Human Brain Atlas.

* http://human.brain-map.org/static/download
* https://hub.docker.com/r/neurovault/ahba/

The data location is `/ahba_data`. Source CSVs are converted into
HDF5 optimized for indexing and removed.
```
/ahba_data
├── [640K]  Richiardi_Data_File_S2.xlsx
├── [223K]  corrected_mni_coordinates.csv
├── [1.6M]  probe_info_max1.csv
└── [489M]  store_max1_reduced.h5
```
