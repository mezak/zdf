zdf
===

A python script for handling zoning definition files (ZDF) for hydrographic surveying as defined by CARIS.

Given ZDF, write geojson, using python library geojson.
Given shapefile convert to geojson, then convert to ZDF.

Perform simple QC tests on input file and output file to ensure closed polygons and eliminate sliver polygons or gaps.

Create map of output file.
