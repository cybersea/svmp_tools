__author__ = 'allison'

import svmpUtils as utils
import arcpy
import svmp_10x as svmp
# Import the custom Exception class for handling errors
from svmp_exceptions import SvmpToolsError
import svmpUtils as utils

if __name__ == '__main__':

    site = "core002" #"hdc2344"

    mysite = svmp.Site(site, "2014", "Native_SG",
                  r"Z:\Users\allison\projects\dnr_svmp2015\eelgrass_svmp\00-14_monitoring_results\transect_data\svmp_TD_abtest_new.mdb",
                  r"Z:\Users\allison\projects\dnr_svmp2015\eelgrass_svmp\00-14_monitoring_results\svmp_site_info.mdb\sample_polygons",
                  r"Z:\Users\allison\projects\dnr_svmp2015\eelgrass_svmp\2014_test\site_folders")

    print "SITE: %s" % (mysite.id)
    print "Transect Feature Class: " + mysite.transect_pt_fc
    print "Transect Feature Class exists? %s " % (mysite.transect_pt_fc_exists)
    print "Control File: " + mysite.ctl_file
    print "Control File exists? %s" % (mysite.ctl_file_exists)
    print "Veg Column:" + mysite.veg_col
    print "Veg Column exists? %s" % (mysite.veg_col_exists)
    print "Veg Exists? %s" % (mysite.veg_exists)
    print "Sample Polygon ID: %s_%s" % (mysite.id, mysite.sampling_occasion)
    print "Sample Polygon Exists? %s" % (mysite.sample_poly_exists)
    print "Transects: %s" % (mysite.transect_list)
    print "Transect Lines exist: %s" % arcpy.Exists(mysite.transect_ln_fc)
    print "Clipped Transect Lines exist: %s" % arcpy.Exists(mysite.transect_ln_clip_fc)
    #print mysite.transect_ln_clip_fc
    #mysite.make_line_fc()
    #mysite.clip_line_fc()

    mytransects = svmp.Transects(mysite)

    print mytransects.transect_results_ids
    print mytransects.trktypes
    print mytransects.maxflags
    print mytransects.minflags
    print mytransects.transect_list
    print mytransects.mintransdeps
    print mytransects.maxtransdeps
    print mytransects.minvegdeps
    print mytransects.maxvegdeps

    print "Transect lengths: %s" % mytransects.trans_lengths
    print "Veg lengths: %s" % mytransects.veg_lengths
    mytransects.calc_vegfractions()
    mytransects.get_dates()

    mysitestats = svmp.SiteStatistics(mytransects)
    print "Site Results ID: %s" % mysitestats.site_results_id
    print "Site %s" % mysitestats.siteid
    print "Number of Transect for area calcs: %s" % mysitestats.n_area
    print "Veg Fraction: %s" % mysitestats.veg_fraction
    print "Sample Area %s" % mysitestats.sample_area
    print "Veg Area: %s" % mysitestats.veg_area
    print "Standard Error of Veg Area: %s" % mysitestats.se_vegarea
    print "Number of Transects - Mins: %s" % mysitestats.n_veg_mindep
    print "Mean Min Veg Dep: %s" % mysitestats.veg_mind_mean
    print "Shallowest Min Veg Dep: %s" % mysitestats.veg_mind_shallowest
    print "Standard Error of Veg Min Dep: %s" % mysitestats.veg_mind_se
    print "Number of Transects - Maxs: %s" % mysitestats.n_veg_maxdep
    print "Mean Max Veg Dep: %s" % mysitestats.veg_maxd_mean
    print "Deepest Max Veg Dep: %s" % mysitestats.veg_maxd_deepest
    print "Standard Error of Veg Max Dep: %s" % mysitestats.veg_maxd_se
    print "Sitestat ID: %s" % mysitestats.sitestat_id

    print "Max Dep List: %s" % mysitestats.max_deps_4stats
    print "Min Dep List: %s" % mysitestats.min_deps_4stats



