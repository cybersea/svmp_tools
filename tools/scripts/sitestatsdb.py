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
# (1) ptParentDir -- Parent directory for site point shapefiles
# (2) pyParentDir -- Parent directory for sample polygon shapefiles
# (3) ctlParentDir -- Parent directory for site control files
# (3) siteFile -- Full path of text file containing list of all sites for year
# (4) siteDB -- Full path to database to store site and transect statistic tables
# (5) allsitesFC -- Feature Class containing point locations for all sites
# (6) surveyYear -- Survey year for data to be processed

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
import arcgisscripting 
# Import functions used for SVMP scripts
import svmpUtils as utils
# Import the custom Exception class for handling errors
from svmp_exceptions import SvmpToolsError


STEP = 1
def msg(msg):
    global STEP
    #msg = 'Step %s: %s...' % (STEP,msg)
    gp.AddMessage(msg)
    STEP += 1

#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Create a dictionary with the site name and shapefile
# Assumes shapefiles are prefixed with site_year_
#  and the appropriate suffix is passed in as a parameter
def make_ptShpDict(siteList,parentDir,subDir,yr,shpSuffix):
    siteShpDict = {}
    for site in siteList:
        shp = yr + "_" + site + shpSuffix
        shpPath = os.path.join(parentDir,site,subDir,shp)
        siteShpDict[site] = shpPath
    return siteShpDict
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Create a dictionary with the site name and shapefile
# Assumes shapefiles are prefixed with year_site_
#  and the appropriate suffix is passed in as a parameter
# Note: Sample Polys are prefixed with site then year
#   opposite order from transect site files
def make_pyShpDict(siteList,parentDir,subDir,yr,shpSuffix):
    siteShpDict = {}
    for site in siteList:
        shp = site + "_" + yr + shpSuffix
        shpPath = os.path.join(parentDir,site,subDir,shp)
        siteShpDict[site] = shpPath
    return siteShpDict
#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Make a dictionary with the Site IDS and the lat/long coordinates
def make_siteXYDict(siteList,siteFC,srCode,gp):
    siteCol = utils.sitePtIDCol #"NAME"  # Field that contains the site ID
    sitesXY = {}
    # temp directory to create dummy shapefile for Spatial Reference
    tmpDir = os.path.dirname(siteFC)
    spatRef = utils.make_spatRef(gp,tmpDir,srCode)
    # Create Search Cursor on site point feature class
    # With Geographic spatial reference for lat/long coords
    allpts = gp.SearchCursor(siteFC,'',spatRef)
    pt = allpts.Next()
    while pt:
        # site id
        siteID = pt.GetValue(siteCol)
        # Coordinates
        X = pt.shape.GetPart().x
        Y = pt.shape.GetPart().y
        sitesXY[siteID] = [X,Y]
        pt = allpts.Next()

    del allpts   # remove the cursor    
    return sitesXY   

#--------------------------------------------------------------------------
#--------------------------------------------------------------------------
# Convert transect point shapefiles to line files
# Assign point attributes to the line ahead of it
def trans_pt2line(ptFC,lnFC,gp,transID):
    try: 
        spatRef = gp.Describe(ptFC).SpatialReference
        gp.CreateFeatureClass(os.path.dirname(lnFC),os.path.basename(lnFC),"Polyline",ptFC,"#","#",spatRef)
        # Open a cursor for the ouput line shapefile
        cur = gp.InsertCursor(lnFC)
        # Get a list of fields in the input point feature class
        pt_fields = utils.get_fieldnames(ptFC,gp)
        # Cursor for iterating through Point Feature class
        allpts = gp.SearchCursor(ptFC)
        pt = allpts.next()
        lastTrk = 0   # Initialize the transect counter
        lineArray = gp.CreateObject("Array")  # Make an array object for the line
        fromPt = gp.CreateObject("Point") # Make an array object for the "From" point
        toPt = gp.CreateObject("Point") # Make an array object for the "To" point

        while pt:
            # Get the current Transect ID
            trkID = pt.GetValue(transID)
            # IF it's a new transect, store the coordinates
            # and the attributes of this point
            if trkID != lastTrk:
                # Get the coordinates and Transect ID
                fromPt.x = pt.shape.GetPart().x
                fromPt.y = pt.shape.GetPart().y
                fromPt.Id = trkID
                lastTrk = trkID
                # List to contain the attributes
                pt_attributes = {}
                # Get the attributes
                for fld in pt_fields:
                    pt_attributes[fld] = pt.GetValue(fld)
            # Otherwise, this point is the end point
            # of a two point line, starting with the previous point
            else:
                # Get the coordinates of the end point of line
                toPt.x = pt.shape.GetPart().x
                toPt.y = pt.shape.GetPart().y
                toPt.Id = trkID
                # Create a new row in the feature class
                lineArray.RemoveAll()
                # Add the To/From points
                lineArray.Add(fromPt)
                lineArray.Add(toPt)
                # Create a new feature
                feat = cur.NewRow()
                # Set the new feature's shape to the Line Array
                feat.Shape = lineArray
                for fld in pt_fields:
                    feat.SetValue(fld, pt_attributes[fld])
                # Insert this Row into the feature class
                cur.InsertRow(feat)

                # Then, save these coordinates for
                # the start coordinates of the next line
                fromPt.x = toPt.x
                fromPt.y = toPt.y
                # And the associated attributes go with the next line
                for fld in pt_fields:
                    pt_attributes[fld] = pt.GetValue(fld)

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
def calc_transStats(site,lnFC,trkFlagDict,gp):
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
            rows = gp.SearchCursor(lnFC,selStatement)
            row = rows.Next()
            # If records returned from query, do processing for that transect
            if row:   
                # Initialize Max and Min depth 
                # Can't use first row, because that may have the nonsense depth null value of -9999
                # So, use these extremely large and small values to initialize
                trk_maxdep_ft = zm_maxdep_ft = init_max = 10000
                zm_mindep_ft = trk_mindep_ft = init_min = -10000
                # Get date of first transect:
                if startDate == 0:
                    startDate = row.GetValue(utils.shpDateCol)
                ## Loop through all rows for the transect
                while row:
                    feat = row.shape  # Get the Shape field
                    trkDate = row.GetValue(utils.shpDateCol)
                    dep = row.GetValue(utils.shpDepCol)
                    vidQual = row.GetValue(utils.videoCol)
                    zmPresence = row.GetValue(utils.zmCol)
                    # length of the current feature 
                    segLen = feat.Length   
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
                    row = rows.Next()
        
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
        
                # return all values in a list in the same order as the output database table
                # for use in an InsertCursor
                trkStats = [site,startDate,trkDate,trk,samplen,zmlen,zm_fraction,trk_maxdep_ft,zm_maxdep_ft,zm_mindep_ft,trk_mindep_ft,trkMaxDepFlag,trkMinDepFlag]
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
        e.call(errtext)

        
    return allTrkStats

#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
# Insert the calculated statistics data into the specified database table
# Assumes that the data are stored as a list of lists
# and they are in the same order as the output data table column list
def insert_stats(table,data,cols,gp):
    cur = gp.InsertCursor(table)
    for line in data:
        # Create a New Row in the table
        row = cur.NewRow()
        # Set all the attributes
        # Assumes data list is in the same order as column list
        for (col,val) in zip(cols,line):
            row.SetValue(col,val)
        cur.InsertRow(row)

    del cur  # Remove the cursor
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
# Produce default stats values for sites without Zostera marina
def calc_siteStats_noZm(sites,ptShpDict,siteXYDict,gp):
    # Empty List to Store output data for all sites
    allSiteStats = []
    
    #utils.shpDateCol
    # Sample Size
    n = 0
    # ZM fraction
    estmean_zmfraction = 0
    estvar_zmfraction = 0
    # Areas and variability
    sample_area = est_basalcov = estvar_basalcov = cv_basalcov = se_basalcov = ci95_basalcov = 0
    # Null values for depths
    # Min Depth stats
    n_mindep = 0
    mean_mindep = min_mindep = max_mindep = std_mindep = var_mindep = se_mindep = ci95_mindep = utils.nullDep
    # Max Depth stats
    n_maxdep = 0
    mean_maxdep = min_maxdep = max_maxdep = std_maxdep = var_maxdep = se_maxdep = ci95_maxdep = utils.nullDep
    
    for site in sites:
        #------------------- DATE -----------------------------------
        try:
            ptFC = ptShpDict.get(site)
            rows = gp.SearchCursor(ptFC,"","",utils.shpDateCol)
            row = rows.Next()
            # Get date of first transect:
            startDate = row.GetValue(utils.shpDateCol)
            del rows
            del row
        except:
            e.call("Problem accessing or querying %s" % ptFC)
       
        #------------------- LOCATION -------------------------------
        try:
            lon,lat = siteCoords(site,siteXYDict)
        except:
            e.call("Error finding coordinates for site: " + site)

        #-------------------- OUTPUT --------------------------------
        siteStats = [site, startDate, n, estmean_zmfraction, estvar_zmfraction, 
                     sample_area,est_basalcov, estvar_basalcov,cv_basalcov,se_basalcov,ci95_basalcov,
                     n_mindep, mean_mindep, min_mindep, max_mindep, std_mindep, var_mindep, se_mindep, ci95_mindep,
                     n_maxdep, mean_maxdep, min_maxdep, max_maxdep, std_maxdep, var_maxdep, se_maxdep, ci95_maxdep,
                     lat,lon]

        allSiteStats.append(siteStats)
        #print allSiteStats
        
    return allSiteStats
    
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
# Calculate statistics for sites with Zostera marina, based on transect table
def calc_siteStats(sites,inTable,pyDirDict,siteXYDict,gp):
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
        rows = gp.SearchCursor(inTable,selStatement)
        # are any rows returned?
        #print "are Any rows returned?"
        row = rows.Next()
        #print "Apparently"
        # Get date from first row 
        #if not row:
        if row == None:
            print "No rows returned"
            e.call("site %s:  No data in table %s" % (site, inTable))
        #print row
        #print dateCol
        startDate = row.GetValue(dateCol)
        #msg("Start Date: %s" % startDate)
        n = 0  # Counter for number of transects used in calculations
        # Gather necessary data from data table
        while row:
            # Add values to Sample Length and Eelgrass Length Lists
            samplenList.append(row.GetValue(samplenCol))
            zmlenList.append(row.GetValue(zmlenCol))
            # If transect is Flagged for use in max eelgrass depth, add
            #  its maximum eelgrass depth value to the list
            maxDepZM = row.GetValue(zmmaxdepCol)
            minDepZM = row.GetValue(zmmindepCol)
            if row.GetValue(maxdepflagCol):
                if maxDepZM <> utils.nullDep:
                    maxdepList.append(maxDepZM)
            if row.GetValue(mindepflagCol):
                if minDepZM <> utils.nullDep:
                    mindepList.append(minDepZM)
            n = n + 1 # increment the transect counter 
            #msg("Number of rows processed for sample length and eelgrass length: %s" % (n))           
            row = rows.Next()
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
#        print "Estimated variance of eelgrass fraction: " + str(estvar_zmfraction)
        # Sampling area
        sample_area = sampPolyArea(pyFC,gp)
#        print "Sample area: " + str(sample_area)
        # Estimated basal area coverage (i.e. area of Zostera marina)
        est_basalcov = estmean_zmfraction * sample_area
#        print "Area of Z. Marina: " + str(est_basalcov)
        # Estimated variance of basal area coverage 
        estvar_basalcov = estvar_zmfraction * (sample_area ** 2)
#        print "Variance of basal area coverage: " + str(estvar_basalcov)
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
        try:
            lon,lat = siteCoords(site,siteXYDict)
        except:
            e.call("Error finding coordinates for site: " + site)

        #-------------------- OUTPUT --------------------------------
        siteStats = [site, startDate, n, estmean_zmfraction, estvar_zmfraction, 
                     sample_area,est_basalcov, estvar_basalcov,cv_basalcov,se_basalcov,ci95_basalcov,
                     n_mindep, mean_mindep, min_mindep, max_mindep, std_mindep, var_mindep, se_mindep, ci95_mindep,
                     n_maxdep, mean_maxdep, min_maxdep, max_maxdep, std_maxdep, var_maxdep, se_maxdep, ci95_maxdep,
                     lat,lon]

        allSiteStats.append(siteStats)

    return allSiteStats
#--------------------------------------------------------------------------    
#--------------------------------------------------------------------------
# Calculate Area of Sample Polygon 
# Optional parameter to pass in a multiplier to convert 
# from units in the source shapefile to some other area units
# Default is to return units from shapefile
def sampPolyArea(pyFC,gp, areaConvConstant=1):
    # Create a search cursor on the sample polygon
    # Get Area, and convert from survey feet to square meters
    polys = gp.SearchCursor(pyFC)
    poly = polys.Next()
    pyArea = 0 # initialize polygon area total
    # accumulate area from each polygon in the shapefile
    while poly:
        pyArea = pyArea + (poly.shape.Area * areaConvConstant )
        poly = polys.Next()
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

        # Create the geoprocessing object
        gp = arcgisscripting.create()
        # Overwrite existing output data 
        gp.OverWriteOutput = 1

        # Create the custom error class
        # and associate it with the gp
        e = SvmpToolsError(gp)
        # Set some basic defaults for error handling
        e.debug = True
        e.full_tb = True
        #e.exit_clean = False
        #e.pdb = True

        #Get parameters
        # Input Transect Point Shapefile Parent Directory 
        # Transect ASCII files are located in subdirectories below here 
        ptParentDir = gp.GetParameterAsText(0)  
        # Input Sample Polygon Shapefile Parent Directory 
        pyParentDir = gp.GetParameterAsText(1)
        # Control File Parent Directory
        ctlParentDir = gp.GetParameterAsText(2)
        # Full Path of text file containing list of sites to process
        siteFile = gp.GetParameterAsText(3) 
        # Full Path to database to store site and transect statistic tables
        siteDB = gp.GetParameterAsText(4)   
        # Full path to shapefile containing point locations of sites
        allSitesFC = gp.GetParameterAsText(5)
        # Survey Year for data to be processed
        surveyYear = gp.GetParameterAsText(6)

        #msg(ptParentDir + '\n' + pyParentDir)

        # Subdirectory for Transect Point Shapefiles
        ptSubDir = utils.ptShpSubDir 
        # Suffix for Transect Point Shapefiles
        ptSuffix = utils.ptShpSuffix  
        # Subdirectory for Sample Polygon shapefiles 
        pySubDir = utils.sampPyShpDir 
        # Suffix for Sample Polygon shapefiles
        pySuffix = utils.sampPyShpSuffix  
        # Field name for Unique Transect Number within a site
        transID = utils.trkCol   
        # File suffix for control file
        ctlSuffix = utils.ctlSuffix 

        # gp.AddMessage("Control file suffix:" + ctlSuffix)

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

        # Get site list 
        siteList = utils.make_siteList(siteFile)
        msg("List of sites to calculate statistics:")
        for site in siteList:
            msg(site)

        # Initialize lists to hold sites with and without eelgrass
        siteList_NoZm = []
        siteList_Zm = []

        # Make a dictionary containing the sites and the 
        #  full path to transect point shapefiles
        ptDirDict = make_ptShpDict(siteList,ptParentDir,ptSubDir,surveyYear,ptSuffix)
        
        # check for missing transect point shapefiles
        missingPtShapes = []
        for site in siteList:
            ptShp = ptDirDict.get(site)
            if not os.path.exists(ptShp):
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

        
        # Loop through all sites and make a list of those without eelgrass
        for site, shapefile in ptDirDict.items():
            try:
                # Create Search Cursor for Input Transect Data Table
                # Sort on Zmarina column, descending -- contains only zero or one for presence/absence
                rows = gp.SearchCursor(shapefile,"","",utils.zmCol, "%s D" % utils.zmCol)
                # First row contains max value
                row = rows.Next()
                ZmFlag = row.GetValue(utils.zmCol)
            except:
                e.call("Sorry, there was a problem accessing or querying feature class %s" % site)

            # if max value is zero, there is no Z. marina at the site.
            # Add site to the the list of sites without Z. marina
            if ZmFlag:
                siteList_Zm.append(site)
            else:
                #msg("No Zostera marina at site %s" % site)
                siteList_NoZm.append(site)
                
        siteList_Zm.sort()
        siteList_NoZm.sort()        
        msg("Sites with Zostera marina:\n" +  '\n'.join(siteList_Zm))
        msg("Sites without Zostera marina:\n" + '\n'.join(siteList_NoZm))

        # Make a dictionary containing the sites and the 
        # full path to sample polygon shapefiles
        pyDirDict = make_pyShpDict(siteList,pyParentDir,pySubDir,surveyYear,pySuffix)
        
        # Check for missing sample polygons (only needed for sites with Z. marina)
        missingSamplePolys = []
        for site in siteList_Zm:
            sampPy = pyDirDict.get(site)
            if not os.path.exists(sampPy):
                # add to list of sites with missing sample polygons
                #msg("Sites with Z. marina, but missing sample polys %s" % sampPy)
                missingSamplePolys.append(site)
                
        if missingSamplePolys:
            errtext = "The following sites have Z. marina, but are missing sample polygons for %s:\n" % surveyYear
            errtext += '\n'.join(missingSamplePolys)
            e.call(errtext)
                

        # Create a dictionary containing all sites and lat/long coordinates
        # why all? - want to only open shapefile once to save time
        siteXYDict = make_siteXYDict(siteList,allSitesFC,utils.wgs84Code,gp)

        # Get a list of input subdirectories for control files
        # need to avoid .svn folder
        #ctlSubDirList = utils.make_subDirList(ctlParentDir)
        #ctlDirDict = utils.make_siteDirDict(siteList,ctlSubDirList)

        # Create Tables for Annual Site and Transect Data Summary Statistics
        # NOte:  This will overwrite existing tables and replace them
        try:
            gp.CreateTable(siteDB,trans_table,template_transects_fullpath)
            gp.CreateTable(siteDB,site_table,template_sites_fullpath)
        except:
            errtext = ("Problem Creating Annual Stats Table(s): '%s' and/or '%s' in \n%s\n" % (trans_table,site_table,siteDB))
            errtext += ("Make sure that the database is not open in ArcGIS or MS Access")
            e.call(errtext)
            
        # Loop throught all sites with Eelgrass
        for site in siteList_Zm:
            msg("-------- SITE ID: %s --------" % site)
            msg("Calculating statistics for site: '%s'" % site)
            ptFC = ptDirDict[site]  # get point feature class name
            msg("The point feature class is: '%s'" % ptFC)
            
            # Should not need this because check for all point shapefiles done up front
            #if not gp.Exists(ptFC):
                #e.call("'%s' does not exist" % ptFC)

            # name for Line Feature Class (put in same directory as input points)
            shape_name = "%s_%s_transect_line.shp" % (surveyYear,site)
            lnFC = os.path.join(os.path.dirname(ptFC),shape_name)
            # full path for sample Polygon Feature Class
            pyFC = pyDirDict[site]
            # Output clipped Line Feature Class name
            shape_name = "%s_%s_transect_line_clip.shp" % (surveyYear,site)
            cliplnFC = os.path.join(os.path.dirname(ptFC),shape_name)
            # Control File Name
            ctlFile = "".join((site,ctlSuffix))
            ctlFileFull = os.path.join(ctlParentDir,site,ctlFile)
            # Should not need this because check for all point shapefiles done up front
            #if not os.path.isfile(ctlFileFull):
                #e.call("Control File '%s'\nfor site %s does not exist" % (ctlFileFull,site))

            # Create the Line Feature Class with same attributes as input points
            try:
                msg("Creating temporary line file")
                trans_pt2line(ptFC,lnFC,gp,transID)                    
            except:
                e.call("Problem creating a line from:" + ptFC)

            # Clip the Line Feature Class with the sample polygon
            if gp.Exists(pyFC):  
                msg("Clipping the Line to the sample poly")             
                gp.clip_analysis(lnFC,pyFC,cliplnFC)
            else:
                e.call("'%s' does not exist" % pyFC)

            # Extract Transect Max/Min Depth Flags from Site Control File
            trkFlagDict = get_Flags(site,ctlFileFull)

            # Calculate Transect Statistics 
            #Transect statistics (list of lists, in order by columns in output tables
            msg("Calculating transect statistics")
            transStats = calc_transStats(site,cliplnFC,trkFlagDict,gp)

            # Insert Transect Statistics into annual Transects data table
            msg("Inserting transect statistics into data table")
            insert_stats(trans_table_fullpath,transStats,transCols,gp)

            # Delete the temporary line files:
            gp.Delete(lnFC)
            gp.Delete(cliplnFC)

        # Calculate Site Statistics for Z. marina sites
#        siteStats = calc_siteStats(siteList,trans_table_fullpath,pyDirDict,siteXYDict,gp)
        if siteList_Zm:
            msg("Calculating site statistics for sites with Z. marina")
            siteStats_Zm = calc_siteStats(siteList_Zm,trans_table_fullpath,pyDirDict,siteXYDict,gp)
            # Insert site Statistics into annual Sites data table
            msg("Inserting site statistics into data table")
            insert_stats(site_table_fullpath,siteStats_Zm,siteCols,gp)
        if siteList_NoZm:
            msg("Calculating site statistics for sites without Z. marina")
            siteStats_NoZm = calc_siteStats_noZm(siteList_NoZm,ptDirDict,siteXYDict,gp)
            msg("Inserting site statistics into data table")
            insert_stats(site_table_fullpath,siteStats_NoZm,siteCols,gp)
        
    except SystemExit:
        pass
    except:
        e.call()
        del gp