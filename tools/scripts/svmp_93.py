"""Major Classes and Data Structures for the SVMP Tools Module."""

"""
    svmp_93.py
    Version: ArcGIS 9.3, uses v.9.3 geoprocessor, not 9.2
    Author: Allison Bailey, Sound GIS
    For: Washington DNR, Submerged Vegetation Monitoring Program (SVMP)
    Date: 2010-01-25
    Requires: Python 2.5.1
"""

# This module contains shared functions and constants that are used
import svmpUtils
import math
import svmp_spatial_93 as spatial
import random
import copy


# Mapping of Geo and Sampling stratum to analysis stratum and extrapolation type

# This one is used for Area calculations where Persistent flats are reported
# separately from core sites

core_extrap = ("core","none")
pfl_extrap = ("persistent flats","none")
fl_extrap = ("flats","area")
fr_extrap = ("fringe","linear")
frw_extrap = ("wide fringe","linear")

#(stratum_geo,stratum_samp) : (stratum_analysis,extrapolation)
sw_Stratum4AreaCalcs ={
("frw","core"):("core","none"),
("fr","core"):("core","none"),
("fl","core"):("core","none"),
("fl","persistent"):("persistent flats","none"),
("fl","rotational"):("flats","area"),
("fr","rotational"):("fringe","linear"),
("frw","rotational"):("wide fringe","linear")
}

# This one is used for Area Change calculations where 
# Persistent flats are reported together with core sites
sw_Stratum4AreaChgCalcs ={
("frw","core"):("core","none"),
("fr","core"):("core","none"),
("fl","core"):("core","none"),
("fl","persistent"):("core","none"),
("fl","rotational"):("flats","area"),
("fr","rotational"):("fringe","linear"),
("frw","rotational"):("wide fringe","linear")
}

 
class Site(object):
    """ Represents the SVMP data for an individual site.
    
    Attributes:
    id -- individual site identifier
    zmArea -- site Zostera marina area
    zmAreaVar -- site Zostera marina area variance
    a2j -- [optional] sample area (for rotational flats only)
    conversion -- [optional] unit conversion flag (final units must be meters)
    
    """
    def __init__(self,id,zmArea,zmAreaVar,a2j=None,conversion=None):
        self.id = id
        self.zmArea = zmArea
        self.zmAreaVar = zmAreaVar
        self.a2j = a2j
        self.conversion = conversion

        # Convert units if necessary
        if conversion is not None:
            self.convert_units(conversion)
       
    def __repr__(self):
        return repr((self.id,self.zmArea,self.zmAreaVar,self.a2j,self.conversion))
    
    def convert_units(self,conversion):
        # should this return something?
        if conversion == "sf2m":
            self.zmArea = self.zmArea * (svmpUtils.sf_m ** 2)
            self.zmAreaVar = self.zmAreaVar * (svmpUtils.sf_m ** 4)
            if self.a2j:
                self.a2j = self.a2j * (svmpUtils.sf_m ** 2)
        else:
            err_text = "Conversion type, %s, is not available" % conversion
            raise ValueError(err_text)
        
    def simulate(self):
        """ Not currently using this code because I couldn't figure out how
            to incorporate it into this class cleanly.   The work is done
            in the function, measurement_error
            Big question was -- return a new value?  or change self.ZmArea in place
            (like a setter)
        """
        randNum = random.normalvariate(0,1)
        sim_zmArea = self.zmArea + ((self.zmAreaVar ** 0.5) * randNum)
        newSite = Site(self.id,sim_zmArea,self.zmAreaVar,self.a2j)
        return newSite
        
    
class BaseStratum(object):
    """ Represents an analysis stratum for grouping of SVMP sites.
     
    Attributes:
    analysis -- analysis stratum
    extrapolation -- extrapolation stratum
    
    """ 
    def __init__(self,analysis,extrapolation):
        self.analysis = analysis
        self.extrapolation = extrapolation
    
class FlatsStratum(BaseStratum):
    """ Constants associated with Rotational Flats Stratum.
    
    Subclass of BaseStratum

    Attributes:
    analysis -- analysis stratum
    extrapolation -- extrapolation stratum
    gp -- ESRI ArcGIS Geoprocessing object
    stratum_fc -- full path to ArcGIS feature class representing the stratum
    conversion -- [optional] unit conversion flag
    query_string -- an ArcGIS query string (the "where" clause)
    Ni -- count of sites in stratum
    A2 -- sum of stratum area
    
    """
    def __init__(self,analysis,extrapolation,gp,stratum_fc,conversion=None):
        BaseStratum.__init__(self,analysis,extrapolation)
        
        self.gp = gp 
        self.stratum_fc = stratum_fc
        self.conversion = conversion
        self.query_string = '"NAME" <> \'\' and "focus_stra" not in (\'c\',\'pfl\')'
        
        self.Ni = self.get_Ni()
        self.A2 = self.get_A2()

    def get_Ni(self):
        """ count the number of rotational flats in the stratum """
        qry = spatial.FeatureQuery(self.gp,self.stratum_fc,self.query_string)
        count = qry.record_count
        del qry
        return count
        
    def get_A2(self):
        """ get the sum of the rotational flats stratum area """
        qry = spatial.FeatureQuery(self.gp,self.stratum_fc,self.query_string)
        if self.conversion:
            if self.conversion == "sf2m":
                area = qry.geometry_sum * (svmpUtils.sf_m ** 2)
            else:
                err_text = "Conversion type, %s, is not available" % conversion
                raise ValueError(err_text)
        else:
            area = qry.geometry_sum
        del qry
        return area
    
  
class FringeStratum(BaseStratum):
    """Constants associated with Fringe (Regular and Wide) Strata.
    
    Subclass of BaseStratum

    Attributes:
    analysis -- analysis stratum
    extrapolation -- extrapolation stratum
    gp -- ESRI ArcGIS Geoprocessing object
    stratum_fc -- full path to ArcGIS feature class representing the stratum
    conversion -- [optional] unit conversion flag
    Ni -- count of sites in stratum
    LT -- sum of stratum length
    LN -- length of sampling frame - 
          NOTE: units must be meters for LN calculation to be correct
    
    """
    def __init__(self,analysis,extrapolation,gp,stratum_fc,conversion=None):
        BaseStratum.__init__(self,analysis,extrapolation)
        
        self.gp = gp
        self.stratum_fc = stratum_fc
        self.conversion = conversion
        self.Ni = self.get_Ni()
        self.LT = self.get_LT()
        self.LN = float(self.Ni) * 1000
        
    def get_Ni(self):
        """ count the number of fringe sites in the stratum """
        # Query for the correct set of sites, based on analysis stratum
        if self.analysis == "fringe":
            query_string = '"2002TYPE" = \'fr\' and "REGION" <> \'sps\''
        elif self.analysis == "wide fringe":
            query_string = '"2002TYPE" = \'frw\' and "REGION" <> \'sps\''
        else:
            err_text = "Analysis stratum type, %s, is not a valid fringe stratum" % self.analysis
            raise ValueError(err_text)
        qry = spatial.FeatureQuery(self.gp,self.stratum_fc,query_string)
        count = qry.record_count
        del qry
        return count
       
    def get_LT(self):
        """ Sum of the Length of all fringe sites in the stratum """
        # Query for the correct set of sites, based on analysis stratum - includes "orphans"
        if self.analysis == "fringe":
            query_string = '"2002TYPE" in (\'fr\',\'fr-orphan<984m\') and "REGION" <> \'sps\''
        elif self.analysis == "wide fringe":
            query_string = '"2002TYPE" in (\'frw\',\'frw-orphan<984m\') and "REGION" <> \'sps\''
        else:
            err_text = "Analysis stratum type, %s, is not a valid fringe stratum" % self.analysis
            raise ValueError(err_text)
        # spatial query object
        qry = spatial.FeatureQuery(self.gp,self.stratum_fc,query_string)
        # Calculate total length, with unit conversion if necessary
        if self.conversion:
            if self.conversion == "sf2m":
                length = qry.geometry_sum * (svmpUtils.sf_m)
            else:
                err_text = "Conversion type, %s, is not available" % self.conversion
                raise ValueError(err_text)
        else:
            length = qry.geometry_sum
        del qry
        return length


class Sample(object):
    """ Represents a sample of SVMP sites.
    
    A sample has Sites and a Stratum.
    
    Attributes:
    sites -- a list of site objects
    stratum  -- a stratum object
    site_ids - list of individual site ids in sample
    zm_areas -- list of individual site Zm Area values
    zm_vars -- list of individual site Zm Variance values
    ni -- count of sites in sample

    
    """    
    def __init__(self,sites_list,stratum,conversion=None):
        """ Create a Sample from a list of sites. """
        self.sites = []
        self.conversion = conversion
        # import all the sites and set the stratum
        self.importSites(sites_list) 
        self.set_stratum(stratum)
        
        # Properties of the Sample
        # Lists of individual site values
        self.site_ids = self._site_attrs('id')
        self.zm_areas = self._site_attrs('zmArea')
        self.zm_vars = self._site_attrs('zmAreaVar')
        
        self.ni = len(self.sites)
       
    def __repr__(self):
        return repr(self.sites)
        
    def importSites(self,sites_list):
        """Create Site objects from a list of site data.
        
        Append these sites objects to a sample
        
        """ 
        for s in sites_list:
            args = s[:3]
            if len(s) == 4:
                a2j = s[3]
            else:
                a2j = None
            kwargs = {'a2j':a2j,'conversion':self.conversion}
            mySite = Site(*args,**kwargs)
            self._addSite(mySite)
    
    def _addSite(self,site):
        """ Adds individual site objects to the sample. """
        self.sites.append(site)

    def set_stratum(self,stratum):
        """ Sets the stratum object for the sample """
        self.stratum = stratum
        
    def _site_attrs(self,attr):
        return [getattr(site,attr) for site in self.sites]
    
    def bootstrap(self):
        #def sample_wr(population, _choose=random.choice):
            #while True: yield _choose(population)
        # This would be easier if could just return a whole new Site object, using 
        bootstrap_sites = [random.choice(self.sites) for i in range(self.ni)]
        self.sites = bootstrap_sites
        self.site_ids = self._site_attrs('id')
        self.zm_areas = self._site_attrs('zmArea')
        self.zm_vars = self._site_attrs('zmAreaVar')

        return bootstrap_sites

    
class SampleStats(Sample):
    """ Represents a sample of SVMP sites with all the statistics as properties
    
    Subclass of Sample
  
    Attributes:
    sites -- a list of site objects
    stratum  -- a stratum object
    ni -- count of sites in sample
    site_ids - list of individual site ids in sample
    zm_areas -- list of individual site Zm Area values
    zm_vars -- list of individual site Zm Variance values
    zm_area -- Estimated Zm Area for the Sample (based on extrapolation type)
    zm_area_var -- Estimated Zm Area Variance for the Sample (based on extrapolation type)
    se -- Standard Error (same for all extrapolation types)
    cv -- Coefficient of variation (same for all extrapolation types)
    meanZmArea -- Mean Zm Area for the Sample
    variance -- Variance of the Sample's Zm site areas
    
    Example Doctest:
    >>> site1 = ["core001",318285957.367152,7.81016158406864E+14,"fl","core"]
    >>> site2 = ["core002",244910.733927743,364666178.032925,"fl","core"]
    >>> frSamp = Sample([site1,site2])
    >>> frSamp.sites[1]
    ('core002', 244910.73392774299, 364666178.03292501, 'fl', 'core')
    >>> frSamp.sites[1].siteid
    'core002'
    >>> len(frSamp.sites)
    2
    >>> frSamp.ni
    2
    >>> frSamp.countSites()
    2
    >>> frSamp.ni
    2
    
    """    
    def __init__(self,sites_list,stratum,conversion=None):
        """ Create a Sample from a list of sites. """

        Sample.__init__(self,sites_list,stratum,conversion)
        
        # Stats on entire Sample
        self.meanZmArea = self.meanZmArea(self.sites)
        self.variance = self.variance(self.sites,self.meanZmArea)
        if self.stratum.extrapolation == "area":
            self.a2js = self._site_attrs('a2j')
            self.Aij = sum(self.a2js)
            self.R = sum(self.zm_areas) / self.Aij
               
        # Soundwide Estimates
        self.zm_area = self.zm_area()
        self.zm_area_var = self.zm_area_var()
        self.se = self.se(self.zm_area_var)
        self.cv = self.cv(self.zm_area,self.se)
        
    def zm_area(self):
        """ Calculate Area of Zostera marina based on extrapolation type """
        #-- NO EXTRAPOLATION
        if self.stratum.extrapolation == "none":
            zmArea = sum(self.zm_areas)
        #-- AREA EXTRAPOLATION
        #   Appendix L, Equation 9 (Skalski, 2003)
        if self.stratum.extrapolation == "area":
            zmArea = sum(self.zm_areas) * self.stratum.A2 / self.Aij
        #-- LINEAR EXTRAPOLATION
        #   Appendix L, Equation 7 (Skalski, 2003)
        if self.stratum.extrapolation == "linear":
            zmArea = self.stratum.LT / self.stratum.LN * self.meanZmArea * self.stratum.Ni
        return zmArea
    
    def zm_area_var(self):
        """ Calculate Variance of Zostera marina Area based on extrapolation type """
        #-- NO EXTRAPOLATION
        if self.stratum.extrapolation == "none":
            zmAreaVar = sum(self.zm_vars)
        #-- AREA EXTRAPOLATION
        #   Appendix L, Equation 11 (Skalski, 2003)
        if self.stratum.extrapolation == "area":
            numerator1 = 0
            for x2j,a2j,id,var in zip(self.zm_areas,self.a2js,self.site_ids,self.zm_vars):
                site_calc = (x2j - a2j * float(self.R)) ** 2
                numerator1 = numerator1 + site_calc                
            term1 = (self.stratum.Ni ** 2)
            term2 = 1 - (float(self.ni)/self.stratum.Ni)
            term3 = numerator1 / (float(self.ni) * (self.ni - 1))
            term4 = self.stratum.Ni * sum(self.zm_vars) / float(self.ni)
            zmAreaVar = term1 * term2 * term3 + term4
        #-- LINEAR EXTRAPOLATION
        #   Appendix L, Equation 8 (Skalski, 2003)
        if self.stratum.extrapolation == "linear":
            term1 = (self.stratum.LT / float(self.stratum.LN)) ** 2 
            term2 = ((self.stratum.Ni ** 2) * (1 - self.ni / float(self.stratum.Ni)) * self.variance) / self.ni
            term3 = (self.stratum.Ni / float(self.ni)) * sum(self.zm_vars)
            zmAreaVar = term1 * (term2 + term3)
        return zmAreaVar
    
    def se(self,variance):
        """ Calculate the Standard Error """
        # Standard Error = Square Root of Variance
        return variance ** 0.5
    
    def cv(self,area,se):
        """ Calculate the coefficient of variation """
        # Coefficient of Variation = Standard Error / Zm Area
        try:
            return se / area
        except ZeroDivisionError:
            return 0.0
        
    def meanZmArea(self,sites):
        """ Mean Z marina area for the Sample"""
        sumArea = 0
        for site in sites:
            sumArea = sumArea + site.zmArea
        meanArea = sumArea / float(len(sites))
        return meanArea
    
    def variance(self,sites,meanZmArea):
        """ Variance of Sample's Zm site areas """
        sum_sqdif = 0 # initialize sum of squared differences
        # Calculate sum of squared differences
        for site in sites:
            sqdif = (site.zmArea - meanZmArea) ** 2
            sum_sqdif = sqdif + sum_sqdif  
        # Standard Deviation
        stddev = ((1 / ( float(len(sites)) - 1 )) * sum_sqdif ) ** 0.5
        # Variance
        var = stddev ** 2
        return var

class AnnualEstimate(object):
    """ Represents the annual Zostera marina area estimate and associated error estimates.
    
    An annual estimate has a list of Sample objects 
    
    Attributes:
    zm_areas -- list of all Sample estimated areas
    zm_vars -- list of all Sample estimated variances
    zm_area -- Estimated Zm Area for the Annual Estimate
    zm_area_var -- Estimated Zm Area Variance for the Annual Estimate
    se -- Standard Error 
    cv -- Coefficient of variation      
    
    """
    def __init__(self,samples):
        self.samples = samples

    def __repr__(self):
        return repr((self.zm_area,self.zm_area_var,self.se,self.cv))
    
    def _sample_attrs(self,attr):
        return [getattr(sample,attr) for sample in self.samples]

    @property
    def zm_areas(self):
        """ Fetch a list of the sample's site ZM areas """
        return self._sample_attrs('zm_area')

    @property
    def zm_vars(self):
        """ Fetch a list of the sample's site ZM area variances """
        return self._sample_attrs('zm_area_var')
    
    @property
    def zm_area(self):
        """ Calculate Area of Zostera marina by summing Sample areas """
        return sum(self.zm_areas)
    
    @property
    def zm_area_var(self):
        """ Calculate Variance of Zostera marina Area by summing Sample variances"""
        return sum(self.zm_vars)
    
    @property
    def se(self):
        """ Calculate the Standard Error """
        # Standard Error = Square Root of Variance
        return self.zm_area_var ** 0.5
    
    @property
    def cv(self):
        """ Calculate the coefficient of variation """
        # Coefficient of Variation = Standard Error / Zm Area
        try:
            return self.se / self.zm_area
        except ZeroDivisionError:
            return 0.0
    

class ChangeStats(object):
    """ Represents the Statistics for Year-to-Year Change Analysis for a Stratum
    
    A ChangeStats object has three Samples:
    Samples y1m and y2m contain the matching sites sampled in both years
    Sample y1 contains all the sites sampled in Year 1
    
    """
    def __init__(self,sample_y1m,sample_y2m,sample_y1):
        self.y1m = sample_y1m
        self.y2m = sample_y2m
        self.y1 = sample_y1
        self.xs = self.y1m.zm_areas
        self.ys = self.y2m.zm_areas
        self.x2sum = self.sum_of_squares(self.xs)
        self.y2sum = self.sum_of_squares(self.ys)
        self.xysum = self.sum_xy()
        self.m = self.slope()
        self.m_se = self.se_slope()
        self.change_prop = self.proportion_change()
        self.area_change = self.calc_area_change()
        self.area_change_se = self.calc_area_change_se()
    
    #def _sample_attrs(self,attr):
        #return [getattr(sample,attr) for sample in self.samples]

    #@property
    #def zm_areas(self):
        #""" Fetch a list of the sample's site ZM areas """
        #return self._sample_attrs('zm_area')  
    
    def sum_of_squares(self,vals):
        """ Sum of the individual squared ZM areas in a sample """
        val2 = [v ** 2 for v in vals]
        return sum(val2)
    
    def sum_xy(self):
        """ Sum of the product of matching Zm areas for two different years """
        xy = []
        for (x,y) in zip(self.xs,self.ys):
            xy.append(x * y)
        return sum(xy)
    
    def slope(self):
        """ Slope of the regression line for two years ZM Areas
            Line goes through origin
        """
        try:
            return float(self.xysum) / self.x2sum
        except ZeroDivisionError:
            return 0.0

    
    def se_slope(self):
        """ Calculate standard error of the slope      
        """
        try:
            slope_var = ((self.y2sum - (self.xysum ** 2) / self.x2sum) / (len(self.xs) - 1)) / self.x2sum
        except ZeroDivisionError:
            slope_var = 0.0
        # Capture situations where value is essentially zero, but somehow ends up as a small negative number
        # if 0 > slope_var > -0.0001:
        if slope_var < 0 and abs(slope_var) < 0.0001:
            slope_var = 0.0
        return slope_var ** 0.5
 
    def proportion_change(self):
        """ The proportion change of Zm area between two years
            referred to as percent change, but proportion is used in equations"""
        return self.m - 1
    
    def calc_area_change(self):
        """ The total area change between two years """
        return self.change_prop * self.y1.zm_area
    
    def calc_area_change_se(self):
        """ The standard error of the total area change """
        variance = self.y1.zm_area_var * (self.change_prop ** 2) + ((self.m_se * self.y1.zm_area)**2) - self.y1.zm_area_var * (self.m_se ** 2)
        return variance ** 0.5


class ChangeStatsTotal(object):
    """ Represents the Total Year-to-Year Change Analysis for all strata combined
    
    A ChangeStatsTotal object has a list of ChangeStats objects
    And an AnnualEstimate object

    """
    def __init__(self,chgstats,y1annual):
        self.chgstats = chgstats
        self.y1annual = y1annual
        self.y1areas = self.y1annual.zm_areas
        self.y1vars = self.y1annual.zm_vars
        self.area_changes = self._attrs('area_change',self.chgstats)
        self.area_change_ses = self._attrs('area_change_se',self.chgstats)
        self.prop_changes = self._attrs('change_prop',self.chgstats)
        self.prop_change_ses = self._attrs('m_se',self.chgstats)
        self.y1area = self.y1annual.zm_area
        self.area_change = self.calc_area_change()
        self.area_change_se = self.calc_area_change_se()
        self.change_prop = self.proportion_change()
        self.change_prop_se = self.proportion_change_se()
        
    def _attrs(self,attr,objs):
        """ Fetchs a list of attributes from a list of objects"""
        return [getattr(o,attr) for o in objs]

    def calc_area_change(self):
        """ Calculates the sum of stratum-specific area change values """
        return sum(self.area_changes)
        
    def calc_area_change_se(self):
        """ Calculates the total S.E. from a list of stratum-specific S.E.s """
        se2s = [se ** 2 for se in self.area_change_ses]
        return sum(se2s) ** 0.5
    
    def proportion_change(self):
        """ Calculates the overall proportion Zm area change """
        return self.area_change / self.y1area
    
    def proportion_change_se(self):
        """ Calculates the standard error of proportion Zm area change """
        term1 = 0
        term2 = 0
        for area,se in zip(self.y1areas,self.prop_change_ses):
            term1 += (se * area) ** 2
        term1 = term1 / (self.y1area ** 2)
        
        for var,pchange in zip(self.y1vars,self.prop_changes):
            term2 += var * (pchange * self.y1area - self.area_change) ** 2
        term2 = term2 / (self.y1area ** 4)
        se = (term1 + term2) ** 0.5
        return (term1 + term2) ** 0.5


##------------------------------------------------------------------------------
## ------------- FUNCTIONS for Monte Carlo Confidence Intervals-----------------
##------------------------------------------------------------------------------
""" I haven't figured out how best to incorporate these into the classes
   and methods, so for now, they are just stand-alone functions
   AB, 4/14/2010
   Source:  Dowty, Pete.  2005.  Assessment of Sound-Wide Change Estimates
   from Paired-Site Analysis.  (white paper). Washington DNR, Olympia, WA.
   and Pete Dowty, pers. comm.
"""

def bootstrap(data):
    """ A bootstrap technique to simulate sampling error  
    
    Creates a new set of data by randomly selecting members,
    with replacement, from a sample.
    
    """
    #new_data = copy.deepcopy(data)
    bootstrap_data = []
    for i in xrange(len(data)):
        mychoice = random.choice(data)
        bootstrap_data.append(mychoice[:])
    return bootstrap_data

def measurement_error(data,i=None,grp=None,outfile=None):
    """ A function to simulate measurement error at an eelgrass survey site
    
    Calculates a simulated eelgrass area using site eelgrass area,variance, 
    and a random number with a normal distribution, mean of 0, std dev of 1
    
    data parameter is expected to be a list of lists for each site, with
    each interior list representing a site, and for each site, containing
    site_id, Zm Area, and Zm Area Variance (in that order)
    
    If simulated Zm Area is less than zero, generate new random number(s)
    until it is greater than zero
    
    These three parameters are for optional output logging file
    i - the iteration
    grp - the grouping of data (all year 1, year 1 match, year 2 match)
    outfile - output file handle (opened and closed outside of this function)
    
    """
    newdata = copy.deepcopy(data)
            
    for site in newdata:
        site_id = site[0]
        zmArea = site[1]
        zmAreaVar = site[2]
        # Generate the random number and calculate the simulated Zm area
        randNum = random.normalvariate(0,1)
        se = zmAreaVar ** 0.5
        sim_zmArea = zmArea + (se * randNum)
        # If simulated area is less than zero, 
        # continue generating values until it is > 0
        while sim_zmArea < 0:
            randNum = random.normalvariate(0,1)
            se = zmAreaVar ** 0.5
            sim_zmArea = zmArea + (se * randNum)
        site[1] = sim_zmArea
        
        # If output file wanted, create output string and write to file
        #print site_id,zmArea,zmAreaVar,se,randNum,(se * randNum),sim_zmArea
        if outfile:
            print_string = "%i,%s,%s,%r,%r,%r,%r,%r,%r\n" % (i,grp,site_id,zmArea,zmAreaVar,se,randNum,(se * randNum),sim_zmArea)
            #print_string = output_string(i,grp,siteid,zmArea,zmAreaVar,se,randNum,(se * randNum),sim_zmArea)
            outfile.write(print_string)
        
    return newdata

def match_sites(data1,data2):
    """ Finds the data from the year 2 that match the bootstrapped year 1 data """
    data2_match = []
    for site in data1:
        site_id = site[0]
        for site in data2:
            try:
                site.index(site_id)
                data2_match.append(site[:])
                break
            except:
                continue
    return data2_match

def conf_int(rel_changes,pct_ci):
    """ Finds the specified confidence interval from a list of relative change values
    
    rel_changes - a list of Zm relative change values generated from Monte Carlo simulation
    pct_ci - confidence interval value (usually 0.95)
    Calculated such that pct_ci of the values in the list
    are within the Mean of rel_changes plus or minus the CI/2
    
    """
    mean_rc = sum(rel_changes) / len(rel_changes)
    conf_intervals = [abs(mean_rc - rc) for rc in rel_changes]
    cis_sorted = sorted(conf_intervals)
    # Find the index within the sorted list
    #   that corresponds the specified pct_ci
    idx_ci = int(len(cis_sorted) * pct_ci)
    # pct_ci values must be within the range
    #  and 100 - pct_ci values must be outside of the range.
    #  The confidence interval is calculated as a mean between the two postions
    #  in the sorted list of confidence interval values
    ci = (cis_sorted[(idx_ci - 1)] + cis_sorted[idx_ci]) / 2
    return ci

if __name__ == '__main__':
    import doctest
    doctest.testmod(verbose=True,report=True)