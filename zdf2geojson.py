# -*- coding: utf-8 -*-
"""
Created on Fri Jul 18 15:04:22 2014

@author: mzieserl

read Caris ZDF
convert to geojson format and returns list holding both geojson outputs
 
zones are polygon, tide stations are points
does not handle multiple stations per zone (only 1)
only puts one tide station per zone under the TIDE_AVERAGE section
assumes coordinates are NAD83 lat, lon

QC
checks that all polygons are closed
that each geometry has zoning attributes
that adjacent coordintates are the same, so there are no slivers or overlaps 
between zones

"""

import shapefile, copy
from geojson import Point, Polygon, Feature, FeatureCollection

# create the PRJ file
#prj = open("%s.prj" % filename, "w")
#epsg = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]'
#prj.write(epsg)
#prj.close()


# get a section of the zdf into a list
# returns list with 4 lines
# 0 number of lines in this section
# 1 line number
# 2 list of the lines that were read, split by commas
# 3 any messages created
def zdfsection(i,zdflines,sectiontype):
    
    numlinesadded = 0
    thelines = []
    
    firstline = zdflines[i].replace('\n', '').strip()
    i+=1 # move to next line
    if firstline == '[ZONE]':
        this_section = 'geometry'
    elif firstline == '[TIDE_ZONE]': 
        this_section = 'zoning factors'
    elif firstline == '[TIDE_STATION]':
        this_section = 'tide stations'
    elif firstline == '[TIDE_AVERAGE]':        
        this_section = 'tide average'       
    elif firstline == '[OPTIONS]':
        this_section = 'options'
    elif sectiontype:
        this_section = sectiontype 
        i-=1
    else:
        logmsg = 'Section type is missing:',firstline
        this_section = 'unknown'
        return {'lines added': 0,'current line':i,
        'readlines':[],'current section':this_section,'msg':logmsg}
    

    #stops at end of file or at a blank line, split on commas
    while i < len(zdflines) and zdflines[i].replace('\n', '').strip():
        thestring = zdflines[i].replace('\n', '').strip()
        strlist = thestring.split(',')
        for item in strlist:
            item.strip()
        thelines.append(strlist)
        numlinesadded+=1
        i+=1

    if numlinesadded==0:
        logmsg = 'Nothing read for this section: {}'.format(zdflines[i-1].replace('\n', '').strip())
    else:
        logmsg="Read {:.0f} lines from this section.".format(numlinesadded)
        
    #print logmsg

    return {'lines added':numlinesadded,'current line':i,
    'readlines':thelines,'current section':this_section,'msg':logmsg}
 
# read polygon geometry under ZONE  
def read_zone(thelines):
    azone = {}
    zonename = str(thelines[0][0])
    azone['point_number'] = int(thelines[0][1])
    thecoords=[]
    error = False
    
    for pnt in thelines[1:]:
        thecoords.append([float(pnt[0]),float(pnt[1])])   #lat,lon
    azone['coordinates'] = copy.copy(thecoords)

    logmsg = ''
    if len(thecoords)!=azone['point_number']:
        logmsg = '\n'+azone['name']+': given number of points ('+str(azone['point_number'])
        logmsg = logmsg+') does not equal list length: '+str(len(thecoords))+'\n'
        error = True

    if azone['coordinates'][0]!=azone['coordinates'][-1]:
        logmsg = logmsg + '\nFirst and last coordinates are not the same: \n'
        logmsg = logmsg+str(azone['coordinates'][0])+'   '
        logmsg = logmsg+str(azone['coordinates'][-1])+'\n'
        error = True
        
    return  {'zonename': zonename, 'readzone': azone, 'error' : error,'msg': logmsg}


# read in the zoning factors in TIDE_ZONE
def read_tide_zone(thelines):
##    print thelines
    alltidezones= {}
    for oneline in thelines:
        zone_name = str(oneline[0])
        if not alltidezones.has_key(zone_name):
            alltidezones[zone_name] = {'TS1':int(oneline[1]), 
                                        #'STYPE':str(oneline[2]), # don't include this
                                        'ATC1':int(oneline[3]),
                                        'R1':float(oneline[4])}
        else:
            print 'Duplicate tide zones: {}'.format(zone_name)
            
    return alltidezones


#assumes 1 station per zone
def read_tide_station(thelines):
    allstations = []   
    for oneline in thelines:
        allstations.append({'coordinates':[float(oneline[1]),float(oneline[2])],
                                            'attributes':{'Station':oneline[0]}})
    return allstations


# assumes 2 stations numbers per zone
def read_tide_average(thelines):
    allaverages = []
    for oneline in thelines:
        allaverages.append([str(oneline[0]),int(oneline[1]),int(oneline[2])])
    return allaverages


def read_options(thelines):
    options={}
    options['Outage'] = thelines[0][1]
    options['Interval'] = thelines[1][1]
    
    return options
    
    
def create_zones(zones):
    
    featurelist = []
    i = 0
    for azonekey in sorted(zones):
        azone = zones[azonekey]
        g = Polygon(azone['coordinates'])
        a = azone['attributes']
        a['ZONE'] = str(azonekey)
        f = Feature(geometry = g, properties = a, id = i)
        i+=1
        featurelist.append(f)
    
    geozones = FeatureCollection(featurelist)
    
    return geozones


def create_stations(tide_stations):
    
    featurelist = []
    i = 0
    for arec in tide_stations:
        a = arec['attributes']
        g = Point(arec['coordinates'])
        f = Feature(geometry = g, properties = a, id = i)
        i+=1
        featurelist.append(f)
    
    geostations = FeatureCollection(featurelist)   
    
    return geostations
    
    
def readzdf():
    
    zdfpath ='C:/WORK/python/git/zdf/tests/JOA Zoning 20131008b.zdf'
    try:
        zdf_file = open(zdfpath,'r')
    
        zone = {}
        unique_zonegeo = 0
        zone_attributes = 0
        tide_station = []
        tide_average = []
        options = {}
        valid_format = 0
        current_section = None
    
        # read in ZDF file
        #try:
        zdf_file = open(zdfpath,'r')
        zdflines = zdf_file.readlines()
        
        i = 0
        while i<len(zdflines):
            oneline = zdflines[i].replace('\n','').strip()
            if not oneline:
                pass 
            elif oneline == '[ZONE_DEF_VERSION_2]': #header
                valid_format = 2
                current_section = 'header'
            else:
                #read in a section of the file (ends at a blank line)
                section_return = zdfsection(i,zdflines,current_section)
                current_section = section_return['current section']
                #print section_return['msg']
                #print current_section
                
                if section_return['lines added'] > 0: #actually read something
                    
                    if current_section == 'geometry': # [ZONE]
                        zone_return = read_zone(section_return['readlines'])
                    
                        if zone_return['error']:
                            print zone_return['msg']
                    
                        if zone.has_key(zone_return['zonename']): #problem
                            msg = 'Duplicate zone defintions for '+zone_return['zonename']+'\n'
                            print msg
                        else:
                            zone[zone_return['zonename']] = zone_return['readzone']
                            unique_zonegeo +=1
                        
                    elif current_section == 'zoning factors': # [TIDE_ZONE]
                        tide_zone = read_tide_zone(section_return['readlines'])
                        zone_attributes = len(tide_zone)
    
                    elif current_section == 'tide stations': # [TIDE_STATION]
                        tide_station = read_tide_station(section_return['readlines'])
                        
                    elif current_section == 'tide average': # [TIDE_AVERAGE]
                        tide_average.append(read_tide_average(section_return['readlines']))
                        
                    elif current_section == 'options': # [OPTIONS]
                        options = read_options(section_return['readlines'])
                        
                    else:
                        print 'problem'
                    
                i = section_return['current line'] 
                #print i              
            i+=1
            #print i
            
        #combine zone geometry and zone attributes
        #loop through each attribute record in tide_zone list
        for attkey in tide_zone.keys():
            if zone.has_key(attkey):
                zone[attkey]['attributes'] = tide_zone[attkey]
            else:
                pass
                #error, there are attributes without geometry
        
        for akey in zone.keys():
            if not zone[akey].has_key('attributes'):
                print 'missing attributes for',akey
        
        # create zoning geojson
        geozones = create_zones(zone)
        #print geozones
        
        geostations = create_stations(tide_station)
        print geostations

#    except:
#        print 'ok'
    finally:
        zdf_file.close()    
    return {'zones':geozones,'stations':geostations}
    
if __name__ == '__main__':

    readzdf()
