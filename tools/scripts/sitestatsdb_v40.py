__author__ = 'allison'

import svmpUtils as utils
import arcpy
import svmp_10x as svmp
# Import the custom Exception class for handling errors
from svmp_exceptions import SvmpToolsError
import svmpUtils as utils

if __name__ == '__main__':

    mysite = svmp.Site("swh1626", "2014", "Native_SG",
                  r"Z:\Users\allison\projects\dnr_svmp2015\eelgrass_svmp\00-14_monitoring_results\transect_data\svmp_TD_abtest_new.mdb",
                  r"Z:\Users\allison\projects\dnr_svmp2015\eelgrass_svmp\00-14_monitoring_results\svmp_site_info.mdb\sample_polygons",
                  r"Z:\Users\allison\projects\dnr_svmp2015\eelgrass_svmp\2014_test\site_folders")

    print "SITE: %s" % (mysite.id)
    # print "Transect Feature Class: " + mysite.transect_pt_fc
    # print "Transect Feature Class exists? %s " % (mysite.transect_pt_fc_exists)
    # print "Control File: " + mysite.ctl_file
    # print "Control File exists? %s" % (mysite.ctl_file_exists)
    # print "Veg Column:" + mysite.veg_col
    # print "Veg Column exists? %s" % (mysite.veg_col_exists)
    # print "Veg Exists? %s" % (mysite.veg_exists)
    # print "Sample Polygon ID: %s_%s" % (mysite.id, mysite.sampling_occasion)
    # print "Sample Polygon Exists? %s" % (mysite.sample_poly_exists)
    print "Transects: %s" % (mysite.transect_list)
    #print mysite.transect_ln_fc
    #print mysite.transect_ln_clip_fc
    #mysite.make_line_fc()
    #mysite.clip_line_fc()

    mytransects = svmp.Transects(mysite)

    # print mytransects.transect_results_ids
    # print mytransects.trktypes
    # print mytransects.maxflags
    # print mytransects.minflags
    # print mytransects.transect_list
    # print mytransects.mintransdeps
    # print mytransects.maxtransdeps
    # print mytransects.minvegdeps
    # print mytransects.maxvegdeps

    print mytransects.trans_lengths
    print mytransects.veg_lengths
    mytransects.calc_vegfractions()
    mytransects.get_dates()


