import arcpy
import os
import svmpUtils as utils
import sys
# Not working, yet.....
# tool_path = os.path.dirname(os.path.realpath(__file__))
# script_path = os.path.join(tool_path, "scripts")
# sys.path.append(script_path)


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "SVMP Tools v.4.0"
        self.alias = "svmp40"

        import svmpUtils as utils

        # List of tool classes associated with this toolbox
        self.tools = [TransectDatatoPtFC, TransectAndSiteStatistics]


class TransectDatatoPtFC(object):

    def __init__(self):
        """Tool to convert SVMP video survey point files (csv) to point feature classes"""
        self.label = "(1) Transect Data to Point Feature Class"
        self.description = "This tool converts SVMP video survey files from csv format to point feature classes"
        self.canRunInBackground = True

    def getParameterInfo(self):
        """Define parameter definitions"""

        # Input parameter 1:  Parent directory for site data folders and input csv files
        in_dir = arcpy.Parameter(
            displayName="Input Data Parent Directory",
            name="in_dir",
            datatype="Folder",
            parameterType="Required",
            direction="Input"
        )
        # Input parameter 2:  Text file with list of sites to process
        sites_file = arcpy.Parameter(
            displayName="List of Sites file",
            name="sites_file",
            datatype="File",
            parameterType="Required",
            direction="Input"
        )
        # Input parameter 3: Table with vegetation codes
        vegcode_table = arcpy.Parameter(
            displayName="Vegetation Code Table",
            name="vegcode_table",
            datatype="Table",
            parameterType="Required",
            direction="Input"
        )

        out_gdb = arcpy.Parameter(
            displayName="Output Geodatabase",
            name="out_gdb",
            datatype="Workspace",
            parameterType="Required",
            direction="Input"
        )
        out_gdb.filter.list = ['Local Database','Remote Database']

        err_dir = arcpy.Parameter(
            displayName="Output Error Log Directory",
            name="err_dir",
            datatype="Folder",
            parameterType="Required",
            direction="Input"
        )

        # Default values  -- Change or remove these for DNR paths
        in_dir.value = "Y:/projects/dnr_svmp2016/data/2014_test/site_folders"
        sites_file.value = os.path.join("Y:/projects/dnr_svmp2016/data/2014_test", "sites2process_all.txt")
        vegcode_table.value = "Y:/projects/dnr_svmp2016/db/SVMP_2000_2015_DB.v4_20170109/SVMP_DB_v4_20170109.mdb/veg_codes"
        out_gdb.value = "Y:/projects/dnr_svmp2016/data/2014_test/2014_test_pgdb.mdb"
        err_dir.value = "Y:/projects/dnr_svmp2016/data/2014_test/site_folders"

        params = [in_dir, sites_file, vegcode_table, out_gdb, err_dir]

        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[2].value:
            vegcode_table = parameters[2].value
            vegcode_field = 'veg_code'
            # table = arcpy.Describe(vegcode_path).baseName
            field_names = [f.name for f in arcpy.ListFields(vegcode_table)]
            if vegcode_field not in field_names:
                errtext = "[SVMP ERROR]: The selected table, {0}, has no field {1}.".format(vegcode_table, vegcode_field)
                errtext += "\nChoose a different table."
                parameters[2].setErrorMessage(errtext)
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        import csv2pt
        reload(csv2pt)  # Remove this after development

        # Input parameter 1:  Parent directory for site data folders and input csv files
        in_dir = parameters[0].valueAsText # "Y:/projects/dnr_svmp2016/data/2014_test/site_folders"

        # Input parameter 2:  Text file with list of sites to process
        sites_file = parameters[1].valueAsText # os.path.join("Y:/projects/dnr_svmp2016/data/2014_test", "sites2process_all.txt")

        # Input parameter 3: Table with vegetation codes
        vegcode_table = parameters[2].valueAsText # "Y:/projects/dnr_svmp2016/db/SVMP_2000_2015_DB.v4_20170109/SVMP_DB_v4_20170109.mdb/veg_codes"

        # Input parameter 4: Output Geodatabase to store point feature classes
        out_gdb = parameters[3].valueAsText # "Y:/projects/dnr_svmp2016/data/2014_test/2014_test_pgdb.mdb"

        # Input parameter 5: Error Log directory
        err_dir = parameters[4].valueAsText  # in_dir

        # Call the main function to process the csv point data
        csv2pt.main(in_dir, sites_file, vegcode_table, out_gdb, err_dir)

        return


class TransectAndSiteStatistics(object):
    def __init__(self):
        """Tool to calculate SVMP transect and site statistics from transect point features """
        self.label = "(2) Calculate Transect and Site Statistics"
        self.description = "This tool calculates SVMP transect and site statistics from transect point features"
        self.canRunInBackground = True

    def getParameterInfo(self):
        """Define parameter definitions"""
        # Input parameter 1:  Geodatabase with Transect Point Feature Class(es)
        transect_gdb = arcpy.Parameter(
            displayName="Transect Point Geodatabase",
            name="transect_gdb",
            datatype="Workspace",
            parameterType="Required",
            direction="Input"
        )
        transect_gdb.filter.list = ['Local Database','Remote Database']

        # Input parameter 2:  SVMP Geodatabase with Tables needed for selecting correct transects
        svmp_gdb = arcpy.Parameter(
            displayName="SVMP Core Geodatabase",
            name="svmp_gdb",
            datatype="Workspace",
            parameterType="Required",
            direction="Input"
        )
        svmp_gdb.filter.list = ['Local Database','Remote Database']

        # Input parameter 3: Site Statistics Geodatabase with Template results tables
        stats_gdb = arcpy.Parameter(
            displayName="Site Statistics Database",
            name="stats_db",
            datatype="Workspace",
            parameterType="Required",
            direction="Input"
        )
        stats_gdb.filter.list = ['Local Database','Remote Database']
        #
        # Input parameter 4: Survey Year to be Processed
        survey_year = arcpy.Parameter(
            displayName="Survey Year",
            name="survey_year",
            datatype="String",
            parameterType="Required",
            direction="Input"
        )
        survey_year.enabled = False  # Disabled until value in svmp_gdb
        # Input parameter 5: Vegetation Type to be Processed
        veg_code = arcpy.Parameter(
            displayName="Vegetation Type",
            name="veg_code",
            datatype="String",
            parameterType="Required",
            direction="Input"
        )
        veg_code.enabled = False # Disabled until value in svmp_gdb
        # Input parameter 6: Optional List of Sites file
        sites_file = arcpy.Parameter(
            displayName = "List of Sites File",
            name = "sites_file",
            datatype="File",
            parameterType="Optional",
            direction="Input",
        )
        # Input parameter 6: Study or Studies to Be Processed
        study = arcpy.Parameter(
            displayName="Study",
            name="study",
            datatype="String",
            parameterType="Optional",
            direction="Input",
            multiValue=True,
            category="Optional - Choose Study"
        )
        study.filter.type = "ValueList"
        study.filter.list = ['SVMPsw','SVMPfocus','SVMPsupp','Stressor','Suquamish',
                             'SitesConcern','Reserves','ProIsland','MRC-Elwha','FOSJ2003','Elwha','DNRparks','CityBham']
        # study.values = [['SVMPsw','SVMPfocus','SVMPsupp','Stressor']]

        # Input parameter 7: Vegetation Type to be Processed
        samp_sel = arcpy.Parameter(
            displayName="Sample Selection Method",
            name="samp_sel",
            datatype="String",
            parameterType="Optional",
            direction="Input",
            multiValue=True,
            category="Optional - Sample Selection Method"
        )
        samp_sel.filter.type = "ValueList"
        samp_sel.filter.list = ['SRS','STR','SUBJ','SUBJ-SRS','SYS']
        # samp_sel.values = [['SRS','STR','SUBJ','SUBJ-SRS','SYS']]

        # err_dir = arcpy.Parameter(
        #     displayName="Output Error Log Directory",
        #     name="err_dir",
        #     datatype="Folder",
        #     parameterType="Required",
        #     direction="Input"
        # )

        # Default values  -- Change or remove these for DNR paths
        transect_gdb.value = "Y:/projects/dnr_svmp2016/data/svmp_pt_data\svmptoolsv4_td2fc_testing_11-15.mdb"
        svmp_gdb.value = "Y:/projects/dnr_svmp2016/db/SVMP_2000_2015_DB.v5_20170125/SVMP_DB_v5_20170123_ABwork.mdb"
        stats_gdb.value = "Y:/projects/dnr_svmp2016/svmp_tools/tools/svmp_db/svmp_sitesdb.mdb"
        sites_file.value = os.path.join("Y:/projects/dnr_svmp2016/data/2014_test", "sites2process_all.txt")

        params = [transect_gdb, svmp_gdb, stats_gdb, survey_year, veg_code, sites_file, study, samp_sel]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # Populate Vegetation Type parameter with values from veg_codes table
        if parameters[1].value:
            svmp_gdb = str(parameters[1].value)
            # Vegetation Type - from veg_code column in veg_codes table
            vegcode_table = os.path.normpath(os.path.join(svmp_gdb, utils.vegcodesTbl))
            vegcode_field = utils.vegcodeCol
            vegcodes_list = utils.unique_values(vegcode_table, vegcode_field)
            parameters[4].filter.list = vegcodes_list
            parameters[4].enabled = True
            # Survey year - from visit_year column in site_visits table
            sitevisits_table = os.path.normpath(os.path.join(svmp_gdb, utils.sitevisitsTbl))
            surveyyr_field = utils.visityearCol # 'visit_year' #
            surveyyrs_list = utils.unique_values(sitevisits_table, surveyyr_field)
            parameters[3].filter.list = sorted(surveyyrs_list,reverse=True)
            parameters[3].enabled = True
        else:
            # Disable parameter if no Core SVMP Geodatabase parameter provided
            parameters[3].enabled = False
            parameters[4].enabled = False



        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        return
