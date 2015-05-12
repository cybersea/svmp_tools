__author__ = 'Allison Bailey, Sound GIS'

"""
Major Classes and Data Structures for SVMP Tools Module

"""

import sys
import os
import svmpUtils as utils
import arcpy


class Site:
    """ Represents the SVMP data for an individual site

    Attributes
    id -- individual site identifier
    sampling_occasion -- sampling occasion (for example, year)
    veg_col -- vegetation column of interest
    veg_col_exists -- Flag for existence of vegetation column in transect_pt_fc
    transect_gdb -- geodatabase containing transect point feature classes
    transect_pt_fc -- Transect point feature class (full path)
    transect_pt_fc_exists -- Flag for existence of transect point feature class
    sample_poly -- Sample polygon feature
    ctl_file -- Control file name (full path)
    ctl_file_exists -- Flag for existence of control file

    """

    def __init__(self, id, sampling_occasion, veg_col, transect_gdb, sample_poly_fc, ctl_directory):
        self.id = id
        self.sampling_occasion = sampling_occasion
        self.veg_col = veg_col
        self.transect_gdb = transect_gdb
        self.ctl_directory = ctl_directory
        #self.set_transect_pt_fc(sample_poly_fc)
        #self.set_ctl_file(ctl_directory)

    # def set_transect_pt_fc(self):
    #     """ Specify Transect Point Feature class name and full path """
    #     self.transect_pt_fc = "".join((self.id, "_", self.sampling_occasion, utils.ptFCSuffix))
    #     print self.transect_pt_fc
    #     try:
    #         self.transect_pt_fc_full = os.path.join(self.transect_gdb, self.transect_pt_fc)
    #         print self.transect_pt_fc_full
    #     except:
    #         pass

    @property
    def transect_pt_fc(self):
        """ Transect Point Feature class full path"""
        fc_name = "".join((self.id, "_", self.sampling_occasion, utils.ptFCSuffix))
        return os.path.join(self.transect_gdb, fc_name)

    @property
    def ctl_file(self):
        file_name = "".join((self.id, utils.ctlSuffix))
        return os.path.join(self.ctl_directory, self.id, file_name)

    # def set_ctl_file(self,dir=None):
    #     """ Specify Control file name and full path """
    #     self.ctl_file = "".join((self.id, utils.ctlSuffix))
    #     print self.ctl_file
    #     try:
    #         self.ctl_file_full = os.path.join(dir, self.id, self.ctl_file)
    #         print self.ctl_file_full
    #         self.ctl_file_check()
    #     except:
    #         pass

    @property
    def transect_pt_fc_exists(self):
        """ Flag for existence of transect point feature class """
        if arcpy.Exists(self.transect_pt_fc):
            return True
        else:
            return False

    # def transect_pt_fc_check(self):
    #     if arcpy.Exists(self.transect_pt_fc_full):
    #         self.transect_pt_fc_exists = True
    #     else:
    #         self.transect_pt_fc_exists = False
    #     print self.transect_pt_fc_exists

    @property
    def ctl_file_exists(self):
        """ Flag for existence of control file """
        if os.path.exists(self.ctl_file):
            return True
        else:
            return False

    # def ctl_file_check(self):
    #     """ Check for existence of control file """
    #     if os.path.exists(self.ctl_file_full):
    #         self.ctl_file_exists = True
    #     else:
    #         self.ctl_file_exists = False
    #     print self.ctl_file_exists

    @property
    def veg_col_exists(self):
        """ Flag for existence of vegetation column"""
        if self.transect_pt_fc_exists:
            field_name_list = [i.name for i in arcpy.ListFields(self.transect_pt_fc)]
            if self.veg_col in field_name_list:
                return True
            else:
                return False
        else:
            return False

    # def veg_col_check(self):
    #     """ Check for existence of vegetation column"""
    #     field_name_list = [i.name for i in arcpy.ListFields(self.transect_pt_fc_full)]
    #     if self.veg_col in field_name_list:
    #         self.veg_col_exists = True
    #     else:
    #         self.veg_col_exists = False
    #     print self.veg_col, self.veg_col_exists


class SiteGroup:
    """ Represents a group of SVMP sites to be processed together with common parameters

    Attributes
    sites -- a list of site objects
    sampling_occasion -- sampling occasion (for example, year)
    veg_type -- vegetation type to be summarized
    transect_gdb -- geodatabase containing transect point feature classes
    sample_poly_fc -- Sample polygon feature class
    ctl_directory -- Parent directory for control files
    site_db -- output database with template tables (sites, transects)
    """

    def __init__(self, sites_list, sampling_occasion, veg_type, transect_gdb, sample_poly_fc, ctl_directory, site_db):
        self.sites = []
        self.import_sites(sites_list)
        self.sampling_occasion = sampling_occasion
        self.veg_type = veg_type
        self.transect_gdb = transect_gdb
        self.sample_poly_fc = sample_poly_fc
        self.ctl_directory = ctl_directory
        self.site_db = site_db


    def import_sites(self, sites_list):
        """
        Create Site objects from a list of site data.
        Append these sites objects to a sample
        """

    def _addSite(self, site):
        """ Adds individual site objects to the sample. """
        self.sites.append(site)

    def _site_attrs(self, attr):
        return [getattr(site, attr) for site in self.sites]


if __name__ == '__main__':
    import doctest

    doctest.testmod(verbose=True, report=True)

    mysite = Site("hdc2344", "2014", "Native_SG",
                  r"Z:\Users\allison\projects\dnr_svmp2015\eelgrass_svmp\00-14_monitoring_results\transect_data\svmp_TD_abtest.mdb",
                  r"Z:\Users\allison\projects\dnr_svmp2015\eelgrass_svmp\00-14_monitoring_results\svmp_site_info.mdb\sample_polygons",
                  r"Z:\Users\allison\projects\dnr_svmp2015\eelgrass_svmp\2014_test\site_folders")

    print "Transect Feature Class: " + mysite.transect_pt_fc
    print "Transect Feature Class exists? %s " % (mysite.transect_pt_fc_exists)
    print "Control File: " + mysite.ctl_file
    print "Control File exists? %s" % (mysite.ctl_file_exists)
    print "Veg Column:" + mysite.veg_col
    print "Veg Column exists? %s" % (mysite.veg_col_exists)
