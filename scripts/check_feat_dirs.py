import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurovault.settings")
django.setup()

from nidmfsl.fsl_exporter.fsl_exporter import FSLtoNIDMExporter
from neurovault.apps.statmaps.utils import detect_feat_directory, get_traceback


if __name__ == '__main__':
    feat_dirs_path = raw_input("Enter location of test data: ")
    find = 0
    parse = 0
    fail = 0

    for root, _, _ in os.walk(feat_dirs_path, topdown=False):
        if detect_feat_directory(root):
            print 'found feat directory at {0}'.format(root)
            find += 1
            try:
                fslnidm = FSLtoNIDMExporter(feat_dir=root, version="0.2.0")
                fslnidm.parse()
                export_dir = fslnidm.export()
                parse += 1
            except:
                fail += 1
                print("Unable to parse the FEAT directory: \n{0}.".format(get_traceback()))
    print 'found {0} FEAT dirs, {1} successfully processed, {2} failures.'.format(find,parse,fail)
