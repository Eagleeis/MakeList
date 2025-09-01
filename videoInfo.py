###########################################################################################################################
# Brief : Helper class for Python script makeList.py to create lists of movies
#         The output shall contain relative file path with size (as configured)
#         and codec of embedded video.
#         This script requires Python module "videoprops".
# Author: Jan Blumenthal (eagleeis@gmx.de)
# Usage : python makeList.py -d=%MOVIES% -t=movies --initSnippets="import videoInfo;wi=videoInfo.VideoChecker(makeList,'{0:<90}\t{3:>15_.2f}\t{4}',1/1024/1024))" --filterSnippet="wi.filter(curDir,filePath)" --os=outputEntry=wi.output(filePath) -o="-"
###########################################################################################################################
import os
import traceback
from videoprops import get_video_properties


###########################################################################################################################
class VideoChecker:
	#######################################################################################################################
	def __init__( self, makeList, fmtOutputline = None, convSize = 1 ):
		# fmtOutputline: Format string for one output line.
		#	{0}		
		#	{1}		
		#	{2}		
		#	{3}		
		#	{4}		
		# convSize: Multiplier to recalculate the size of a file.
		#			Usually set to: 1 / 1024 / 1024
		#			Resulting calculation will be a float!.
		self.__verbose			= makeList.getVerbose()
		self.__verboseVerbose	= makeList.getVerboseVerbose()
		self.__videos			= {}
		self.__fmtOutputline	= fmtOutputline if fmtOutputline else "{0};{3:_};{4}"
		self.__convSize			= convSize

	#######################################################################################################################
	def filter( self, curDir, subFilePath ):
		if self.__verbose:
			print( "Checking \"{}\".".format( subFilePath ) )
		filePath		= os.path.join( curDir, subFilePath )
		size			= os.path.getsize( filePath )
		if self.__convSize is not None:
			size		= self.__convSize * size
		try:
			props		= get_video_properties( filePath )
			codec		= props[ "codec_name" ]
			outputLine	= self.__fmtOutputline.format(	subFilePath,
														curDir,
														filePath,
														size,
														codec,
													 )
			self.__videos[ subFilePath ] = outputLine
			return True
		except Exception as e:
			if self.__verbose:
				print( "Error while checking \"{}\".".format( subFilePath ) )
			if self.__verboseVerbose:
				traceback.print_tb( e.__traceback__ )
			return False

	#######################################################################################################################
	def output( self, filePath ):
		return self.__videos[ filePath ]
