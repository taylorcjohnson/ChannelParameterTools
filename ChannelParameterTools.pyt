import arcpy
import os

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Channel Parameter Tools"
        self.alias = "ChannelParameter"

        # List of tool classes associated with this toolbox
        self.tools = [ChannelWidth]


class ChannelWidth(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Calculate Average Channel Width"
        self.description = "Determine average channel width of the Colorado River for user-defined reaches"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        param0 = arcpy.Parameter(
            displayName='Input River Reaches',
            name='inReach',
            datatype='GPValueTable',
            parameterType='Optional',
            direction='Input')
        param0.columns = [['String', 'Reach ID'], ['Double', 'Mile Begin'], ['Double', 'Mile End']]

        param1 = arcpy.Parameter(
            displayName='Input River Reaches From Text File',
            name='inReachBoo',
            datatype='GPBoolean',
            parameterType='Optional',
            direction='Input')

        param2 = arcpy.Parameter(
            displayName='River Reaches Text File',
            name='inReachTxt',
            datatype='DETextfile',
            parameterType='Optional',
            direction='Input',
            enabled='False')

        param3 = arcpy.Parameter(
            displayName='Output Shapefile',
            name='outShp',
            datatype='DEShapefile',
            direction='Output',
            parameterType='Required')

        param4 = arcpy.Parameter(
            displayName='Approximate River Discharge',
            name='riverFlow',
            datatype='GPString',
            direction='Input',
            parameterType='Required')
        param4.filter.type = 'ValueList'
        #param4.filter.list = ['8,000 cfs', '10,000 cfs', '12,000 cfs']
        param4.filter.list = ['8,000 cfs']
        param4.value = '8,000 cfs'
        
        params = [param4, param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        #Changes GUI depending on whether user intends to manually enter reaches or use pre-defined file
        if parameters[2].valueAsText == 'true':
            parameters[3].enabled='True'
            parameters[1].enabled='False'
        else:
            parameters[3].enabled='False'
            parameters[1].enabled='True'
        
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""

        if parameters[2].valueAsText == 'true' and not parameters[3].value:
            parameters[3].setErrorMessage("You must supply a correctly formatted text file")
            parameters[1].clearMessage()
        elif parameters[2].valueAsText != 'true' and not parameters[1].value:
            parameters[1].setErrorMessage("You must supply at least one user-defined river reach")
            parameters[3].clearMessage()
            
        return
        
    def execute(self, parameters, messages):
        """The source code of the tool."""
        arcpy.AddMessage("\nResults: \n")

        outShp = parameters[4].valueAsText
        prj = r"R:\User Files\Shared\tcjohnson\tasks\20141210_Project3_ChannelWidth\data\intermediate\gdb\20141219_toFinal.gdb\riverXlines" #set to actual .prj on C:\
        arcpy.CreateFeatureclass_management(os.path.dirname(outShp), os.path.basename(outShp), 'POLYGON', '#', '#', '#', prj)
        arcpy.AddField_management(outShp, 'ReachID', 'TEXT')
        arcpy.AddField_management(outShp, 'Width_m', 'FLOAT')
        arcpy.AddField_management(outShp, 'Length_M', 'FLOAT')
        if parameters[2].valueAsText != 'true':                             #Read reach information from tool interface
            reaches = parameters[1].value
            for reach in reaches:
                riverID = str(reach[0])
                startRM = reach[1]
                endRM = reach[2]
                outValues = calcAvg(riverID, startRM, endRM, outShp)
        else:                                                               #Else read reach information from comma-delimited text file
            with open(parameters[3].valueAsText) as reaches:
                for reach in reaches:
                    riverID = reach.split(",")[0]
                    startRM = reach.split(",")[1]
                    endRM = reach.split(",")[2]
                    outValues = calcAvg(riverID, startRM, endRM, outShp)
        arcpy.AddMessage("\n")
        
        return

def calcAvg(river_ID, start_RM, end_RM, out_Shp):
    lineLengths = []
    lineGeom = []
    riverXLines = r"R:\User Files\Shared\tcjohnson\tasks\20141210_Project3_ChannelWidth\data\intermediate\gdb\20141219_toFinal.gdb\riverXlines"
    rivLines = r"R:\User Files\Shared\tcjohnson\tasks\20141210_Project3_ChannelWidth\data\intermediate\gdb\20141219_toFinal.gdb\riverShorelines"
    expression =  '{0} >= {1} AND {0} <= {2}'.format(arcpy.AddFieldDelimiters(riverXLines, 'RiverMile_100ths'), start_RM, end_RM)
    with arcpy.da.SearchCursor(riverXLines, ['RiverMile_100ths', 'XS_Length', 'SHAPE@'], where_clause=expression) as xsLines:
        for xsLine in xsLines:
            lineLengths.append(xsLine[1])
    expression2 = '{0} = {1} OR {0} = {2}'.format(arcpy.AddFieldDelimiters(riverXLines, 'RiverMile_100ths'), start_RM, end_RM)
    with arcpy.da.SearchCursor(riverXLines, 'SHAPE@', where_clause=expression2) as tempCur:
        for temp in tempCur:
            lineGeom.append(temp[0])
    with arcpy.da.SearchCursor(rivLines, 'SHAPE@') as shoreLines:
        for shoreLine in shoreLines:
            lineGeom.append(shoreLine[0])
    inputGeom = ((lineGeom[0].union(lineGeom[1])).union(lineGeom[2])).union(lineGeom[3])
    outGeoms = arcpy.FeatureToPolygon_management(inputGeom, arcpy.Geometry())
    reachAvg = sum(lineLengths)/len(lineLengths)
    reachLen = abs(float(end_RM) - float(start_RM))
    fields =['ReachID', 'Width_m', 'Length_M', 'SHAPE@']
    with arcpy.da.InsertCursor(out_Shp, fields) as outPolys:
        for outGeom in outGeoms:
            outPolys.insertRow([river_ID, reachAvg, reachLen, outGeom])
    arcpy.AddMessage("{0} has an average channel width of {1} meters and a length of {2} miles".format(river_ID, reachAvg, reachLen))
    return river_ID, reachAvg
