#--------------------------------------------------------------------------
# Tool Name:  SiteStatisticsDatabase
# Tool Label: Site Statistics Database
# Source Name: sitestatsdb.py
# Version: ArcGIS 9.2
# Author: Allison Bailey, Sound GIS
# For: Washington DNR, Submerged Vegetation Monitoring Program (SVMP)
# Date: April 2007, modified June 2007, February 2008, December 2008
# Requires: Python 2.4
#
# This script calculates summary statistics for
# all transects and all sites for a specified year.
# These statistics are stored in two data tables
# within an existing MS Access personal geodatabase
# If the tables exist, they will be repopulated with
# a full set of data

# Parameters:
# (1) ptTransectGDB -- Parent directory for site point shapefiles
# (2) pyGDB -- Parent directory for sample polygon shapefiles
# (3) ctlParentDir -- Parent directory for site control files
# (3) siteFile -- Full path of text file containing list of all sites for year
# (4) siteDB -- Full path to database to store site and transect statistic tables
# (5) surveyYear -- Survey year for data to be processed
# (6) veg_code -- The Veg Code to run statistics on

# This script is expecting a directory structure that is
#   specific to Washington DNR's SVMP it looks as follows:
# Sample input point data directory:
# (all transect shapefiles stored in one directory, named by year)
# \\Snarf\bss3\work\svmp\fieldwork\site_folders\core006\video_transect_data
# Sample input sample polygon directory
# \\Snarf\bss3\work\svmp\fieldwork\site_folders\core006\sample_polygons
# Sample input control file directory
#  J:\AQR\DATA\NEARSHOR\VegMon\2006_Field_Season\Site Folders\core006
#--------------------------------------------------------------------------

#--------------------------------------------------------------------------
#Imports
#--------------------------------------------------------------------------
import sys
import os 
from datetime import datetime
import arcpy
# Import functions used for SVMP scripts
import svmpUtils as utils
# Import the custom Exception class for handling errors
from svmp_exceptions import SvmpToolsError


STEP = 1
def msg(msg):
    global STEP
    #msg = 'Step %s: %s...' % (STEP,msg)
    arcpy.AddMessage(msg)
    STEP += 1
    
#--------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------
#---------------------------   ERROR CLASSES   ----------------------------------------------
#--------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------

class SamplePolygonNotFound( Exception ):
    def __init__(self, message):
        super( self.__class__ , self ).__init__( message )
    def __str__(self):
        return repr(self)

#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Create a dictionary with the site name and featureclass
# Assumes shapefiles are prefixed with site_year_
#  and the appropriate suffix is passed in as a parameter
def make_ptShpDict(siteList,transectGDB,yr,shpSuffix):
    siteShpDict = {}
    for site in siteList:
        shp = site + "_" + yr + shpSuffix
        shpPath = os.path.join(transectGDB,shp)
        siteShpDict[site] = shpPath
    return siteShpDict
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Create a dictionary with the site name and in-memory feature_layer
# Assumes featureclass are prefixed with site_year_
#  and the appropriate suffix is passed in as a parameter
#
def make_pyFCDict(siteList,sample_poly_path,yr,fcSuffix):
    siteFCDict = {}
    missingPolygons = []
    for site in siteList:
        site_stat_poly_id = site + "_" + yr
        fl_output_name = site + "_" + yr + fcSuffix
        sample_poly_fc = sample_poly_path
        #
        #
        #  this creates a global temporary feature_layer
        #  we can reference it later just with it's name
        #  especially if we are using it in another arcpy
        #  Geoprocessing tool that takes a FeatureLayer as input
        #  such as a SearchCursor( < feature_layer> ) or SelectLayerByLocation
        #  the call to MakeFeatureLayer *will not* bomb if the
        #  the select statement is bad -- a null layer will exist
        #
        #
        #msg( "Creating temp feature layer '%s'" % fl_output_name )
        arcpy.MakeFeatureLayer_management( sample_poly_fc, fl_output_name, where_clause="[%s] = '%s'" % ('sitestat_id', site_stat_poly_id) )
        if arcpy.Exists( fl_output_name ):
            siteFCDict[site] = fl_output_name
        else:
            missingPolygons.append( site )

    return ( siteFCDict, missingPolygons )
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Convert transect point shapefiles to line files
# Assign point attributes to the line ahead of it
def trans_pt2line(ptFC,lnFC,transID):
    try: 
        spatRef = arcpy.Describe(ptFC).SpatialReference
        msg( "Creating line featureclass = %s" % lnFC )
        arcpy.CreateFeatureclass_management(os.path.dirname(lnFC),os.path.basename(lnFC),"Polyline",ptFC,"#","#",spatRef)
        # Open a cursor for the ouput line shapefile
        cur = arcpy.InsertCursor(lnFC)
        # Get a list of fields in the input point feature class
        pt_fields = utils.get_fieldnames(ptFC,arcpy)
        # Cursor for iterating through Point Feature class
        allpts = arcpy.SearchCursor(ptFC)
        pt = allpts.next()
        lastTrk = 0   # Initialize the transect counter
        lineArray = arcpy.CreateObject("Array")  # Make an array object for the line
        fromPt = arcpy.CreateObject("Point") # Make an array object for the "From" point
        toPt = arcpy.CreateObject("Point") # Make an array object for the "To" point

        while pt:
            # Get the current Transect ID
            trkID = pt.getValue(transID)
            # IF it's a new transect, store the coordinates
            # and the attributes of this point
            if trkID != lastTrk:
                # Get the coordinates and Transect ID
                fromPt.X = pt.shape.getPart().X
                fromPt.Y = pt.shape.getPart().Y
                fromPt.ID = trkID
                lastTrk = trkID
                # List to contain the attributes
                pt_attributes = {}
                # Get the attributes
                for fld in pt_fields:
                    pt_attributes[fld] = pt.getValue(fld)
            # Otherwise, this point is the end point
            # of a two point line, starting with the previous point
            else:
                # Get the coordinates of the end point of line
                toPt.X = pt.shape.getPart().X
                toPt.Y = pt.shape.getPart().Y
                toPt.ID = trkID
                # Create a new row in the feature class
                lineArray.removeAll()
                # Add the To/From points
                lineArray.add(fromPt)
                lineArray.add(toPt)
                # Create a new feature
                feat = cur.newRow()
                # Set the new feature's shape to the Line Array
                feat.shape = lineArray
                for fld in pt_fields:
                    feat.setValue(fld, pt_attributes[fld])
                # Insert this Row into the feature class
                cur.insertRow(feat)

                # Then, save these coordinates for
                # the start coordinates of the next line
                fromPt.X = toPt.X
                fromPt.Y = toPt.Y
                # And the associated attributes go with the next line
                for fld in pt_fields:
                    pt_attributes[fld] = pt.getValue(fld)

                # Get the next point from the transect point file   
            pt = allpts.next()
            # Get rid of cursors
        del cur
        del allpts
    except:
        e.call("Problem creating Line Feature Class from: " + ptFC)
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Get Transect Max/Min Depth Flags and Track Type from Control File
# These are the attributes which will control output eelgrass statistics
# Assumes format is two columns separated by commas (and some extra whitespace)
#  first column is the attribute name and second column is the value 
# Change Yes/No values to numeric: 1 or 0 for database input
def get_Flags(site,ctlFile):

    # initialize Track ID comparison
    trk = 0
    trkFlagDict = {}

    for line in open(ctlFile):
        # Get rid of white space at beginning and end of line 
        line = line.strip()
        [att,val] = line.split(',')
        val = val.strip()

        # Get Track Number
        if att == utils.ctlTrkAtt:
            # After the first track, output track and 
            # max/min flags from previous track
            if trk > 0:
                trkFlagDict[trk] = [maxFlag,minFlag,trkType]
            # Convert Track Number to an integer
            trk = int(val)
        # Get Track Type
        if att == utils.ctlTrktypeAtt:
            trkType = val
        # Get Maximum Depth Flag
        if att == utils.ctlMaxAtt:
            if val == utils.ctlYes:  
                maxFlag = 1
            elif val == utils.ctlNo:  
                maxFlag = 0
        # Get Minimum Depth Flag
        if att == utils.ctlMinAtt:
            if val == utils.ctlYes:  
                minFlag = 1
            elif val == utils.ctlNo:  
                minFlag = 0

    # Get info from final track        
    trkFlagDict[trk] = [maxFlag,minFlag,trkType]
    return trkFlagDict         

#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Calculate transect-based statistics
# Creates a list of lists containing attributes for each transect
# Attributes are ordered according to output data fields in transect table
def calc_transStats(site,lnFC,trkFlagDict, selected_veg_code):
    # Empty List to Store data for all transects at this site
    allTrkStats = []

    # List indexes for max/min/track types
    maxFlagIdx = 0
    minFlagIdx = 1
    trkTypeIdx = 2

    # String Version of this list for SQL IN statement
    inclTrkTypesString = "(\'" + "\',\'".join(utils.trkType4Stats) + "\')"
    # Feature Layer Name
    lnFL = "line_layer" 

    # Create list of all transects to be included in Stats Calculations  (right now, just SLPR)       
    tracks = [trk for trk in sorted(trkFlagDict) if trkFlagDict[trk][trkTypeIdx] in utils.trkType4Stats]
    
    startDate = 0 # initialize startDate

    # Loop through each transect
    if tracks:
        for trk in tracks:
            # Initialize values
            samplen = 0  # Sample length in meters
            zmlen = 0 # Zostera marina length in meters
    
            # Select lines from a particular track that have the correct track type (SLPR) for eelgrass area calculations
            # NOTE:  Don't need track type in SQL, because already filtered for that in creating list of tracks
            # Need to form a select statment like "tran_num" = 1
            selStatement = '''"%s" = %s''' % (utils.trkCol,trk)
            # Create a search cursor for rows that meet the query's criteria
            rows = arcpy.SearchCursor(lnFC,selStatement)
            row = rows.next()
            # If records returned from query, do processing for that transect
            if row:   
                # Initialize Max and Min depth 
                # Can't use first row, because that may have the nonsense depth null value of -9999
                # So, use these extremely large and small values to initialize
                trk_maxdep_ft = zm_maxdep_ft = init_max = 10000
                zm_mindep_ft = trk_mindep_ft = init_min = -10000
                # Get date of first transect:
                if startDate == 0:
                    startDate = row.getValue(utils.shpDateCol)
                ## Loop through all rows for the transect
                while row:
                    feat = row.shape  # Get the Shape field
                    trkDate = row.getValue(utils.shpDateCol)
                    dep = row.getValue(utils.shpDepCol)
                    vidQual = row.getValue(utils.videoCol)
                    zmPresence = row.getValue(selected_veg_code)
                    # length of the current feature 
                    segLen = feat.length   
                    # Only use rows that have good video quality (good = 1, bad = 0)
                    if vidQual:
                        # This segment length gets added to total length of sample
                        samplen = samplen + segLen
                        # Comparisons for max and min look backward because
                        # Depths below MLLW are recorded with negative numbers
                        # So, a maximum depth is actually the lowest number
                        #  and minimum depth is the highest number
                        if dep != utils.nullDep:
                            if dep <  trk_maxdep_ft:
                                trk_maxdep_ft = dep
                            if dep > trk_mindep_ft:
                                trk_mindep_ft = dep                
                        # For eelgrass length, only use rows with 
                        #  good video quality and Zostera marina (Zm <> 0)
                        if zmPresence:
                            # This segment length is added to total length of Z.marina
                            zmlen = zmlen + segLen
                            # Max and min eelgrass depths, same caveat as track depths
                            if dep != utils.nullDep:
                                if dep < zm_maxdep_ft:
                                    zm_maxdep_ft = dep
                                if dep > zm_mindep_ft:
                                    zm_mindep_ft = dep
                    row = rows.next()
        
                # If the max/min depths are the same as the initialized value, 
                #    then, change it to the null value
                if trk_maxdep_ft == init_max:
                    trk_maxdep_ft = utils.nullDep
                if trk_mindep_ft == init_min:
                    trk_mindep_ft = utils.nullDep
                if zm_maxdep_ft == init_max:
                    zm_maxdep_ft = utils.nullDep
                if zm_mindep_ft == init_min:
                    zm_mindep_ft = utils.nullDep
        
                #msg("Z marina transect length: " + str(zmlen))
                #msg("transect sample length: " + str(samplen))    
                # Calculate eelgrass fraction for this Track
                if samplen > 0:
                    zm_fraction = zmlen / samplen
                else:
                    zm_fraction = 0
        
                #msg("Zm fraction: " + str(zm_fraction))
        
                # Get the flags (0,1) for max/min depth for this transect
                trkMaxDepFlag = trkFlagDict[trk][maxFlagIdx]
                trkMinDepFlag = trkFlagDict[trk][minFlagIdx]

                #----------------  SITE_RESULTS_ID ----------------------------  
                #
                #
                #  Q: do we need to more QC here because we are actually doing a FKey to
                #  site_results_id in site table? If so we should do a lookup here
                #  wait until we meet with Allison second week of April to choose
                #
                #
                site_results_id = site + "_" + startDate.strftime( "%Y%m%d" ) + "_" + selected_veg_code
                
                #----------------  TRAN_RESULTS_ID ----------------------------
                trk_string = str( trk ).zfill(2)                    
                tran_results_id = site_results_id + "_" + trk_string
                
               
                # return all values in a list in the same order as the output database table
                # for use in an InsertCursor
                trkStats = [ tran_results_id,site,startDate,trkDate,selected_veg_code,trk,samplen,zmlen,zm_fraction,
                            trk_maxdep_ft,zm_maxdep_ft,zm_mindep_ft,trk_mindep_ft,
                            trkMaxDepFlag,trkMinDepFlag, site_results_id ]
                allTrkStats.append(trkStats)
                
            # No rows returned for transect query.  Transect likely outside of sample polygon   
            else:
                errtext = "No transect data retrieved for Site %s, Transect %s, Transect Type: %s" % (site,trk,'or'.join(utils.trkType4Stats))
                #errtext += "\nIt has Z. marina, good video quality, and transect type: %s" % ('or'.join(utils.trkType4Stats))
                errtext += "\nThe transect may be located outside the sample polygon."
                e.call(errtext)

        del rows # Get rid of cursor
                
    else:
        errtext = "Site %s has Z. marina, a Sample Polygon, but No transects of Type: %s " % (site,'or'.join(utils.trkType4Stats))
        #
        #  Q: do we really want to throw an error
        #  or just tell the people that this site 
        #  was not processed. Reslve with Allison
        #  the scond week of April
        #
        #e.call(errtext)

        
    return allTrkStats

#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
# Insert the calculated statistics data into the specified database table
# Assumes that the data are stored as a list of lists
# and they are in the same order as the output data table column list
def insert_stats(table,data,cols):
    cur = arcpy.InsertCursor(table)
    for line in data:
        # Create a New Row in the table
        row = cur.newRow()
        # Set all the attributes
        # Assumes data list is in the same order as column list
        for (col,val) in zip(cols,line):
            #msg( "col = %s , value = %s , type = %s" % ( col, val, type(val) ) )
            row.setValue(col,val)
        cur.insertRow(row)

    del cur  # Remove the cursor
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
# Calculate statistics for sites with Zostera marina, based on transect table
def calc_siteStats(sites,inTable,pyDirDict,selected_veg_code):
    # Empty List to Store output data for all sites
    allSiteStats = []

    # Column Names
    siteCol = utils.siteCol  
    dateCol = utils.samplestartdateCol 
    samplenCol = utils.samplenCol 
    zmlenCol = utils.zmlenCol 
    zmmaxdepCol = utils.zmmaxdepCol 
    zmmindepCol = utils.zmmindepCol 
    maxdepflagCol = utils.maxdepflagCol  
    mindepflagCol = utils.mindepflagCol     

    for site in sites:
        #msg("In the site loop for: '%s'" % site)
        # Initialize lists to hold transect data for site
        samplenList = []  # Sample length values
        zmlenList = [] # Eelgrass length values
        maxdepList = [] # Maximum eelgrass depth values
        mindepList = [] # Minimum eelgrass depth values

        # full path for sample Polygon Feature Class
        pyFC = pyDirDict[site]
        # SQL statement for selecting site data
        # Fields are indicated by square brackets because it's a geodatabase
        selStatement = '[' + siteCol + ']' + ' = ' + '\'' + str(site) + '\''
        # Create Search Cursor for Input Transect Data Table
        print inTable, selStatement
        rows = arcpy.SearchCursor(inTable,selStatement)
        row = rows.next()
        # Get date from first row 
        if row == None:
            print "No rows returned"
            e.call("site %s:  No data in table %s" % (site, inTable))

        startDate = row.getValue(dateCol)
        #msg("Start Date: %s  | type = %s" % (startDate, type( startDate )) )
        n = 0  # Counter for number of transects used in calculations
        # Gather necessary data from data table
        while row:
            # Add values to Sample Length and Eelgrass Length Lists
            samplenList.append(row.getValue(samplenCol))
            zmlenList.append(row.getValue(zmlenCol))
            # If transect is Flagged for use in max eelgrass depth, add
            #  its maximum eelgrass depth value to the list
            maxDepZM = row.getValue(zmmaxdepCol)
            minDepZM = row.getValue(zmmindepCol)
            if row.getValue(maxdepflagCol):
                if maxDepZM <> utils.nullDep:
                    maxdepList.append(maxDepZM)
            if row.getValue(mindepflagCol):
                if minDepZM <> utils.nullDep:
                    mindepList.append(minDepZM)
            n = n + 1 # increment the transect counter 
            #msg("Number of rows processed for sample length and eelgrass length: %s" % (n))           
            row = rows.next()
        del row
        del rows  # Get rid of cursor
        

        # Calculate the Site Statistics
        #----------------------- AREA STATISTICS --------------------------------
        # Sum of Sample and Eelgrass Lengths for this site
        sum_samplen = sum(samplenList)
#        print "Sum of Sample Length: " + str(sum_samplen)
        sum_zmlen = sum(zmlenList)
#        print "Sum of Z. marina length: " + str(sum_zmlen)
        # Estimated mean eelgrass fraction (P Bar Hat)
        estmean_zmfraction = sum_zmlen / sum_samplen
#        print "P Bar Hat: " + str(estmean_zmfraction)
        # Mean transect lengths (L bar)
        mean_translen = sum_samplen / n
#        print "Mean transect length: " + str(mean_translen)
        # Estimated Variance of eelgrass fraction
        estvar_zmfraction = utils.ratioEstVar(samplenList,zmlenList,estmean_zmfraction,n,mean_translen)
        # Sampling area
        sample_area = sampPolyArea(pyFC)
        # Estimated basal area coverage (i.e. area of Zostera marina)
        est_basalcov = estmean_zmfraction * sample_area
        # Estimated variance of basal area coverage 
        estvar_basalcov = estvar_zmfraction * (sample_area ** 2)
        # standard error of eelgrass area
        se_basalcov = estvar_basalcov ** 0.5
#        print "Standard error of eelgrass area: " + str(se_basalcov)
        # coefficient of Variation of basal area coverage
        cv_basalcov = se_basalcov / est_basalcov
#        print "CV eelgrass area: " + str(cv_basalcov)
        # 95% confidence interval of basal area coverage
        ci95_basalcov = utils.ci95(se_basalcov)
#        print "95% confidence interval: " + str(ci95_basalcov)

        #-------------------- DEPTH STATISTICS --------------------------------
        # Number of samples for Max and Min Eelgrass Depth summaries
        n_maxdep = len(maxdepList)
#        print "Samples for Zm max dep: " + str(n_maxdep)
        n_mindep = len(mindepList)
#        print "Samples for Zm min dep: " + str(n_mindep)
        # Sort the depth lists
        maxdepList.sort()
        mindepList.sort()
        # Range, Mean, Stdev, variance,SE, and 95% confidence interval
        #    for Maximum Depth Values
        if n_maxdep > 0: 
            # If there is at least one max depth transect, use the formulas
            max_maxdep = maxdepList[-1] # last value in sorted list
#            print "Maximum max depth: " + str(max_maxdep)
            min_maxdep = maxdepList[0] # first value in sorted list
#            print "Minimum max depth: " + str(min_maxdep)
            mean_maxdep = sum(maxdepList) / len(maxdepList)
#            print "Mean max depth: " + str(mean_maxdep)
        else:
            # If there is 0 max depth transects, fill with null values
            max_maxdep = utils.nullDep
            min_maxdep = utils.nullDep
            mean_maxdep = utils.nullDep
        if n_maxdep > 1:
            # If there are at least two max depth transects, you can calculate
            # calculate Standard deviation, variance, standard error and 95%CI
            std_maxdep = utils.stdDev(maxdepList)
#            print "Std Dev max depth: " + str(std_maxdep)
            var_maxdep = utils.variance(std_maxdep)
#            print "Variance max depth: " + str(var_maxdep)
            se_maxdep = utils.stdErr(std_maxdep,n_maxdep)
#            print "SE max depth: " + str(se_maxdep)
            ci95_maxdep = utils.ci95(se_maxdep) 
#            print "95% CI max depth: " + str(ci95_maxdep)
        else:
            # Otherwise assign null values
            std_maxdep = utils.nullDep
            var_maxdep = utils.nullDep
            se_maxdep = utils.nullDep
            ci95_maxdep = utils.nullDep
        # Range, Mean, StdDev, variance, SE, and 95% confidence interval
        #   for Minimum Depth Values
        if n_mindep > 0: 
            max_mindep = mindepList[-1] # last value in sorted list
#            print "Maximum min depth: " + str(max_mindep)
            min_mindep = mindepList[0]  # first value in sorted list
#            print "Minimum min depth: " + str(min_mindep)
            mean_mindep = sum(mindepList) / len(mindepList) 
#            print "Mean min depth: " + str(mean_mindep)
        else:
            # If there are 0 min depth transects, fill with null values
            max_mindep = utils.nullDep
            min_mindep = utils.nullDep
            mean_mindep = utils.nullDep
        if n_mindep > 1:
            # If there are at least two min depth transects, you can 
            # calculate Standard deviation, variance, standard error and 95%CI        
            std_mindep = utils.stdDev(mindepList)
#            print "Std Dev min depth: " + str(std_mindep)
            var_mindep = utils.variance(std_mindep)
#            print "Variance min depth: " + str(var_mindep)
            se_mindep = utils.stdErr(std_mindep,n_mindep)
#            print "SE min depth: " + str(se_mindep)
            ci95_mindep = utils.ci95(se_mindep)
#            print "95% CI min depth: " + str(ci95_mindep)
        else:
            # Otherwise assign null values
            std_mindep = utils.nullDep
            var_mindep = utils.nullDep
            se_mindep = utils.nullDep
            ci95_mindep = utils.nullDep


        #------------------- LOCATION -------------------------------
#        try:
#            lon,lat = siteCoords(site,siteXYDict)
#        except:
#            e.call("Error finding coordinates for site: " + site)

        #-------------------- SITE_RESULTS_ID ------------------------
        site_results_id = site + "_" + startDate.strftime( "%Y%m%d" ) + "_" + selected_veg_code

        #-------------------- SITESTAT_ID ----------------------------
        sitestat_id = site + "_" + startDate.strftime( "%Y" )
      
        #
        #  Q: Allison and i need to review these column names.
        #  we also need to talk about class-based modules
        #  helping with edits in the future
        #  where are the following column keys calculated:
        #  zmareaSECol  = se_basalcov for now
        #  
        #  
        siteStats = [ site_results_id, site, startDate, selected_veg_code, n, estmean_zmfraction, 
                     sample_area, est_basalcov, se_basalcov,
                     n_mindep, mean_mindep, max_mindep, min_mindep, se_mindep,
                     n_maxdep, mean_maxdep, max_maxdep, min_maxdep, se_maxdep, sitestat_id]

        allSiteStats.append(siteStats)

    return allSiteStats
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
# Calculate Area of Sample Polygon 
# Optional parameter to pass in a multiplier to convert 
# from units in the source shapefile to some other area units
# Default is to return units from shapefile
def sampPolyArea(pyFC, areaConvConstant=1):
    # Create a search cursor on the sample polygon
    # Get Area, and convert from survey feet to square meters
    polys = arcpy.SearchCursor(pyFC)
    poly = polys.next()
    pyArea = 0 # initialize polygon area total
    # accumulate area from each polygon in the shapefile
    while poly:
        pyArea = pyArea + (poly.shape.area * areaConvConstant )
        poly = polys.next()
    del polys, poly
    return pyArea  

#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
# Get Location of Site in Decimal Degrees
# This info was extracted from the svmp_all_sites shapefile
def siteCoords(site,siteXYDict):
    x = siteXYDict[site][0]
    y = siteXYDict[site][1]
    return float(x),float(y)
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------


#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
#MAIN

if __name__ == "__main__":

    try:

        #  make overwriteOutput ENV = True
        arcpy.env.overwriteOutput = True

        # Create the custom error class
        # and associate it with the arcpy
        e = SvmpToolsError( arcpy )
        # Set some basic defaults for error handling
        e.debug = True
        e.full_tb = True
        #e.exit_clean = False
        #e.pdb = True

        #Get parameters
        # Input Transect Point Shapefile Parent Directory 
        # Transect ASCII files are located in subdirectories below here 
        ptTransectGDB = arcpy.GetParameterAsText(0)  
        # Input Sample Polygon Shapefile Parent Directory 
        pyGDB = arcpy.GetParameterAsText(1)
        # Control File Parent Directory
        ctlParentDir = arcpy.GetParameterAsText(2)
        # Full Path of text file containing list of sites to process
        siteFile = arcpy.GetParameterAsText(3) 
        # Full Path to database to store site and transect statistic tables
        siteDB = arcpy.GetParameterAsText(4)   
        # Survey Year for data to be processed
        surveyYear = arcpy.GetParameterAsText(5)
        # Veg Code
        selected_veg_code = arcpy.GetParameterAsText(6)
        
        # Suffix for Transect Point Shapefiles
        ptSuffix = utils.ptFCSuffix  
        # Suffix for Sample Polygon shapefiles
        pySuffix = utils.sampPyShpSuffix  
        # Field name for Unique Transect Number within a site
        transID = utils.trkCol   
        # File suffix for control file
        ctlSuffix = utils.ctlSuffix 

        # Template table for sites statistics
        template_sites = utils.templateSites
        template_sites_fullpath = os.path.join(siteDB,template_sites)
        #msg("Template Sites:" + template_sites_fullpath)        
        # Template table for transect statistics
        template_transects = utils.templateTransects  
        template_transects_fullpath = os.path.join(siteDB,template_transects)
        # msg("Template Transects" + template_transects_fullpath)

        # Output Statistics Table Names -- use year as prefix 
        site_table = template_sites + surveyYear # surveyYear + template_sites
        site_table_fullpath = os.path.join(siteDB,site_table)
        trans_table = template_transects + surveyYear # surveyYear + template_transects
        trans_table_fullpath = os.path.join(siteDB,trans_table)

        # Site and Transect Table Field Names
        siteCols = utils.siteTabCols
        transCols = utils.transTabCols

        #----------------------------------------------------------------------------------
        #--- CHECK TO MAKE SURE SAMP OCCASION VALUE IS SITE_STATUS.SAMP_OCCASION ----------
        #----------------------------------------------------------------------------------
        #
        #
        #  user can still submit form when [ ERROR ]: text is set
        #  in situation where Veg Code table is pointed somewhere where
        #  site_status table does not exist. So we check for it here
        # 
        #
        if surveyYear.startswith("[ ERROR ]:"):
            errtext = "You need to select a samp occasion year from dropdown list"
            e.call( errtext )
            

        
        #
        #
        #  keep this here for double extra juicy QC
        #  the user can still change the text value 
        #  once it's been set so just to make sure, check it
        #
        #
        gdb_lookup = os.path.dirname( pyGDB )
        sites_status_table = os.path.join( gdb_lookup, 'sites_status' )
        sites_status_exists = arcpy.Exists( sites_status_table )
        if sites_status_exists:
            rows = arcpy.SearchCursor( sites_status_table, where_clause="[samp_occasion] = '%s'" % surveyYear )
            row = rows.next()
            if not row:
                errtext = "The table %s has no samp_occasion year = '%s'...please submit a new samp occasion year" % ( sites_status_table, surveyYear )
                e.call( errtext ) 
        else:
            errtext = "The sites_status table does not exist at path %s" % sites_status_table
            e.call( errtext ) 
            
                
        #
        #
        #  make sure parent dir and samp_occasion match up
        #
        #  Q: better QC method might be to put SearchCursor on start_date
        #  of input field and use that instead
        #
        folder_grep = [ i for i in os.path.split( ctlParentDir ) if i.find( surveyYear ) >= 0 ]
        if not folder_grep:
            errtext = "The samp occasion year '%s' differs from the contorl file directory year '%s'" % (surveyYear, ctlParentDir)
            e.call( errtext )
        #----------------------------------------------------------------------------------
        #--- END MAKE SURE SAMP OCCASION VALUE IS IN SITE_STATUS.SAMP_OCCASION ------------
        #----------------------------------------------------------------------------------
        
        
        #----------------------------------------------------------------------------------
        #--- MAKE SURE SELECTED VEG CODE VALUE IS IN VEG_CODES.VEG_CODE -------------------
        #----------------------------------------------------------------------------------
        #
        #
        #  user can still submit form when [ ERROR ]: text is set
        #  in situation where Veg Code table is pointed somewhere where
        #  veg_code table does not exist. So we check for it here
        # 
        #
        if surveyYear.startswith("[ ERROR ]:"):
            errtext = "You need to select a veg code to run from dropdown list"
            e.call( errtext )
            

        
        #
        #
        #  keep this here for double extra juicy QC
        #  the user can still change the text value 
        #  once it's been set so just to make sure, check it
        #
        #
        gdb_lookup = os.path.dirname( pyGDB )
        veg_codes_table = os.path.join( gdb_lookup, 'veg_codes' )
        veg_codes_exists = arcpy.Exists( veg_codes_table )
        if veg_codes_exists:
            rows = arcpy.SearchCursor( veg_codes_table, where_clause="[veg_code] = '%s'" % selected_veg_code )
            row = rows.next()
            if not row:
                errtext = "The table %s has no veg_code = '%s'...please submit a new veg code" % ( veg_codes_table, selected_veg_code )
                e.call( errtext ) 
        else:
            errtext = "The veg_codes table does not exist at path %s" % veg_codes_table
            e.call( errtext ) 
            
        #----------------------------------------------------------------------------------
        #--- END MAKE SURE SELECTED VEG CODE VALUE IS IN VEG_CODES.VEG_CODE ---------------
        #----------------------------------------------------------------------------------
        
        

        # Get site list 
        siteList = utils.make_siteList(siteFile)
        msg("List of sites to calculate statistics:")
        for site in siteList:
            msg(site)

        #
        # Initialize lists to hold sites with and without veg_codes
        # for later QC
        #
        siteList_NoVegCode = []
        siteList_VegCode = []

        # Make a dictionary containing the sites and the 
        #  full path to transect point shapefiles
        ptDirDict = make_ptShpDict(siteList,ptTransectGDB,surveyYear,ptSuffix)
        # check for missing transect point shapefiles
        missingPtShapes = []
        for site in siteList:
            ptFeatureClass = ptDirDict.get(site)
            if not arcpy.Exists( ptFeatureClass ):
                # add to list of sites with missing transect shapefiles
                missingPtShapes.append(site)
        # Check for missing control files
        missingCtlFiles = []
        for site in siteList:
            # construct control file name and full path
            ctlFile = "".join((site,ctlSuffix))
            ctlFileFull = os.path.join(ctlParentDir,site,ctlFile)
            if not os.path.exists(ctlFileFull):
                # add to list of sites with missing control files
                missingCtlFiles.append(site)
        errtext = ""
        if missingPtShapes or missingCtlFiles:        
            if missingPtShapes:
                errtext += "The following sites are missing transect point shapefiles for %s:\n" % surveyYear
                errtext += '\n'.join(missingPtShapes)
            if missingCtlFiles:
                errtext += "\nThe following sites are missing control files for %s:\n" % surveyYear
                errtext += '\n'.join(missingCtlFiles)
            e.call(errtext)

        
        # Loop through all sites and make a list of those without vegetation
        # columns that match the selected_veg_code input
        # the purpose of this code here is to make sure we are only
        # running stats for sites that have valid veg_code columns
        # 
        #
        # Q: Currently, we create a list of sites with and without selected_veg_code columns
        # but we could through and error if needed here. Since we can expect
        # that some sites *will not* contain the selected_veg_code then we gracefully handle this
        # and throw them into a list. Check with Allison when we meet the second week of April
        #
        # Q: should we be doing a higher-level Search filter here for sites
        # to process based on site_id and presences of selected_veg_code?
        # that way we are only running sites with that veg_code column
        # and it's known before we try to access it with SearchCursor below
        # not sure how this question fits into expected workflow so 
        # save this for Allison when we meet the second week of April
        #
        #
        for site, featureclass in ptDirDict.items():
            try:
                field_list = arcpy.ListFields( featureclass )
                field_name_list = [ i.name for i in field_list ]
                if selected_veg_code not in field_name_list:
                    siteList_NoVegCode.append( site )
                    continue
                siteList_VegCode.append( site )
            except Exception:
                e.call("Sorry, there was a problem accessing or querying feature class %s" % site)
                
        siteList_VegCode.sort()
        siteList_NoVegCode.sort()        
        msg("Sites with Veg Code = %s:\n" % ( selected_veg_code ) +  '\n'.join(siteList_VegCode))
        msg("Sites without Veg Code = %s:\n" % ( selected_veg_code ) + '\n'.join(siteList_NoVegCode))

        #
        # Make a dictionary containing the sites and the temp feature_layer name
        # this function will also hand back a list of problem polygons
        # that are not found in the target feature class
        #
        # Q: since we are creating potentially a lot of temporary feature layers
        # this workflow might slow things down. However, this is the only
        # solution that i can come up with at this time. 
        #
        if not arcpy.Exists( pyGDB ):
            errtext = "The sample polygons feature class does not exist '%s' " % pyGDB
            e.call(errtext)
        pyDirDict, missingSamplePolys = make_pyFCDict(siteList,pyGDB,surveyYear,pySuffix)
                
        if missingSamplePolys:
            errtext = "The following sites have Z. marina, but are missing sample polygons for %s:\n" % surveyYear
            errtext += '\n'.join(missingSamplePolys)
            e.call(errtext)

        # Create Tables for Annual Site and Transect Data Summary Statistics
        # NOte:  This will overwrite existing tables and replace them
        try:
            arcpy.CreateTable_management(siteDB,trans_table,template_transects_fullpath)
            arcpy.CreateTable_management(siteDB,site_table,template_sites_fullpath)
        except:
            errtext = ("Problem Creating Annual Stats Table(s): '%s' and/or '%s' in \n%s\n" % (trans_table,site_table,siteDB))
            errtext += ("Make sure that the database is not open in ArcGIS or MS Access")
            e.call(errtext)
            
        # Loop throught all sites with Eelgrass
        for site in siteList_VegCode:
            msg("-------- SITE ID: %s --------" % site)
            msg("Calculating statistics for site: '%s'" % site)
            ptFC = ptDirDict[site]  # get point feature class name
            msg("The point feature class is: '%s'" % ptFC)
            
            # GDB location of temp files
            gdb_temp_dir_path = os.path.dirname(ptFC)
            # name for Line Feature Class (put in same directory as input points)
            shape_name = "_%s_%s_transect_line" % (surveyYear,site)
            lnFC = os.path.join( gdb_temp_dir_path, shape_name)
            # full path for sample Polygon Feature Class
            pyFC = pyDirDict[site]
            # Output clipped Line Feature Class name
            shape_name = "_%s_%s_transect_line_clip" % (surveyYear,site)
            cliplnFC = os.path.join( gdb_temp_dir_path, shape_name )
            # Control File Name
            ctlFile = "".join((site,ctlSuffix))
            ctlFileFull = os.path.join(ctlParentDir,site,ctlFile)
            # Should not need this because check for all point shapefiles done up front
            #if not os.path.isfile(ctlFileFull):
                #e.call("Control File '%s'\nfor site %s does not exist" % (ctlFileFull,site))

            # Create the Line Feature Class with same attributes as input points
            try:
                msg("Creating temporary line file")
                trans_pt2line(ptFC,lnFC,transID)                    
            except:
                e.call("Problem creating a line from:" + ptFC)

            # Clip the Line Feature Class with the sample polygon
            if arcpy.Exists(pyFC):  
                msg("Clipping the Line to the sample poly")             
                arcpy.Clip_analysis(lnFC,pyFC,cliplnFC)
            else:
                e.call("'%s' does not exist" % pyFC)

            # Extract Transect Max/Min Depth Flags from Site Control File
            trkFlagDict = get_Flags(site,ctlFileFull)

            # Calculate Transect Statistics 
            #Transect statistics (list of lists, in order by columns in output tables
            msg("Calculating transect statistics")
            transStats = calc_transStats(site,cliplnFC,trkFlagDict,selected_veg_code)

            # Insert Transect Statistics into annual Transects data table
            msg("Inserting transect statistics into data table")
            #
            #
            #  Q: skips non SLPR trans stuff
            #
            #
            if transStats:
                insert_stats(trans_table_fullpath,transStats,transCols)

            # Delete the temporary line files:
            arcpy.Delete_management(lnFC)
            arcpy.Delete_management(cliplnFC)

        # Calculate Site Statistics for Z. marina sites
        if siteList_VegCode:
            msg("Calculating site statistics for sites with Veg Code = %s" % selected_veg_code )
            siteStats_Zm = calc_siteStats(siteList_VegCode,trans_table_fullpath,pyDirDict,selected_veg_code)
            # Insert site Statistics into annual Sites data table
            msg("Inserting site statistics into data table")
            insert_stats(site_table_fullpath,siteStats_Zm,siteCols)
            
        
    except SystemExit:
        pass
    except:
        e.call()
        del arcpy