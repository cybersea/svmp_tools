__author__ = 'Allison Bailey, Sound GIS'

"""
Major Classes and Data Structures for SVMP Tools Module

"""

import sys
import os
import svmpUtils as utils
import arcpy
import numpy


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
    sample_poly_fc -- Feature Class containing all sample polygons
    sample_poly -- Sample polygon feature
    sample_poly_exists -- Flag for existence of sample polygon
    ctl_file -- Control file name (full path)
    ctl_file_exists -- Flag for existence of control file

    """

    def __init__(self, id, sampling_occasion, veg_col, transect_gdb, sample_poly_fc, ctl_directory):
        self.id = id
        self.sampling_occasion = sampling_occasion
        self.veg_col = veg_col
        self.transect_gdb = transect_gdb
        self.sample_poly_fc = sample_poly_fc
        self.ctl_directory = ctl_directory

    @property
    def transect_pt_fc(self):
        """ Transect Point Feature class full path"""
        fc_name = "".join((self.id, "_", self.sampling_occasion, utils.ptFCSuffix))
        return os.path.join(self.transect_gdb, fc_name)

    @property
    def ctl_file(self):
        file_name = "".join((self.id, utils.ctlSuffix))
        return os.path.join(self.ctl_directory, self.id, file_name)

    @property
    def transect_pt_fc_exists(self):
        """ Flag for existence of transect point feature class """
        if arcpy.Exists(self.transect_pt_fc):
            return True
        else:
            return False

    @property
    def ctl_file_exists(self):
        """ Flag for existence of control file """
        if os.path.exists(self.ctl_file):
            return True
        else:
            return False

    @property
    def veg_col_exists(self):
        """ Flag for existence of vegetation column"""
        if self.transect_pt_fc_exists:
            field_name_list = [f.name for f in arcpy.ListFields(self.transect_pt_fc)]
            if self.veg_col in field_name_list:
                return True
            else:
                return False
        else:
            return False

    @property
    def veg_exists(self):
        """Flag for existence of specified vegetation"""
        if self.veg_col_exists:
            # Make NumPy Array from table and see if it returns a result
            results = arcpy.da.TableToNumPyArray(self.transect_pt_fc, self.veg_col)
            print "Max of %s: %s" % (self.veg_col, results[self.veg_col].max())
            if results[self.veg_col].max() > 0:
                 return True
            else:
                 return False

        return False

    @property
    def sample_poly_exists(self):
        """ Flag for existence of sample polygon"""
        # Build where clause like this: sitestat_id = "hdc2334_2014"
        samppoly_id = "".join((self.id,"_",self.sampling_occasion))
        delimited_field = arcpy.AddFieldDelimiters(self.sample_poly_fc, utils.sitestatidCol)
        where_clause = delimited_field + " = " + "'%s'" % (samppoly_id)
        # Make NumPy Array from table and see if it returns a result
        results = arcpy.da.TableToNumPyArray(self.sample_poly_fc, utils.sitestatidCol, where_clause)
        #print results - for debugging
        if results:
            return True
        else:
            return False

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

    mysite = Site("swh1626", "2014", "Native_SG",
                  r"Z:\Users\allison\projects\dnr_svmp2015\eelgrass_svmp\00-14_monitoring_results\transect_data\svmp_TD_abtest.mdb",
                  r"Z:\Users\allison\projects\dnr_svmp2015\eelgrass_svmp\00-14_monitoring_results\svmp_site_info.mdb\sample_polygons",
                  r"Z:\Users\allison\projects\dnr_svmp2015\eelgrass_svmp\2014_test\site_folders")

    print "Transect Feature Class: " + mysite.transect_pt_fc
    print "Transect Feature Class exists? %s " % (mysite.transect_pt_fc_exists)
    print "Control File: " + mysite.ctl_file
    print "Control File exists? %s" % (mysite.ctl_file_exists)
    print "Veg Column:" + mysite.veg_col
    print "Veg Column exists? %s" % (mysite.veg_col_exists)
    print "Veg Exists? %s" % (mysite.veg_exists)
    print "Sample Polygon ID: %s_%s" % (mysite.id, mysite.sampling_occasion)
    print "Sample Polygon Exists? %s" % (mysite.sample_poly_exists)
