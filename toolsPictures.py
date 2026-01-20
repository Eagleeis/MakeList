###########################################################################################################################
# Brief : Helper class for Python script makeList.py to create lists of movies
#         including video properties.
#         The output shall contain relative file path with size (as configured)
#         and codec of embedded video.
#         This script requires Python module "videoprops".
# Author: Jan Blumenthal (eagleeis@gmx.de)
# Usage : python makeList.py -d="%MOVIES%" -t=movies --initSnippets="import videoInfo;wi=videoInfo.VideoChecker(makeList,'{0:<90}\t{3:>15_.2f}\t{4}',1/1024/1024)" --filterSnippet="wi.filter(curDir,filePath)" --os=outputEntry=wi.output(filePath) -E=utf8 -o="-"
###########################################################################################################################
import os
import traceback
import shutil
from PIL import Image

###########################################################################################################################
class PictureTools:
	#######################################################################################################################
	def __init__( self, makeList, maxWidth = None, maxHeight = None, swapFormat = False ):
		self.__dryMode			= makeList.getDryMode()
		self.__verbose			= makeList.getVerbose()
		self.__verboseVerbose	= makeList.getVerboseVerbose()
		self.__maxHeight		= maxHeight		# \ maxHeight + maxWidth for
		self.__maxWidth			= maxWidth		# / landscape formats (default)
		self.__swapFormat		= swapFormat	# swap maxHeight and maxWidth in portrait format 

	#######################################################################################################################
	def copyFile( self, srcFile, destFile ):
		if self.__dryMode:
			if self.__verbose:
				print( "Skipped copying \"{}\" to \"{}\".".format( srcFile, destFile ) )
		else:
			if self.__verbose:
				print( "Copying \"{}\" to \"{}\".".format( srcFile, destFile ) )
			dirPath	= os.path.dirname( destFile )
			if not os.path.isdir( dirPath ):
				os.makedirs( dirPath )
			if os.path.isfile( destFile ):
				os.remove( destFile )
			shutil.copy2( srcFile, destFile )

	#######################################################################################################################
	def resizeImage( self, srcFile, destFile ):
		verbose	= self.__verbose
		if self.__dryMode:
			if verbose:
				print( "Skipped resizing \"{}\" to \"{}\".".format( srcFile, destFile ) )
		else:
			dirPath	= os.path.dirname( destFile )
			if not os.path.isdir( dirPath ):
				os.makedirs( dirPath )
			if os.path.isfile( destFile ):
				os.remove( destFile )
			img			= Image.open( srcFile )
			maxHeight	= self.__maxHeight
			maxWidth	= self.__maxWidth
			if self.__swapFormat and img.width < img.height:
				maxHeight	= self.__maxWidth
				maxWidth	= self.__maxHeight
			if img.height > maxHeight or img.width > maxWidth:
				if verbose:
					print( "Resizing \"{}\" to \"{}\".".format( srcFile, destFile ) )

				# Verhältnis berechnen
				widthRatio	= maxWidth / img.width
				heightRatio	= maxHeight / img.height

				# Kleineren Skalierungsfaktor wählen, um beide Bedingungen einzuhalten
				scale		= min( widthRatio, heightRatio )

				# Neue Größe berechnen
				newWidth	= int( img.width * scale )
				newHeight	= int( img.height * scale )

				img_resized = img.resize( ( newWidth, newHeight ), Image.LANCZOS )  # LANCZOS = hochwertige Skalierung
				img_resized.save( destFile, quality = 75 )
				shutil.copystat( srcFile, destFile )
			else:
				if verbose:
					print( "Copying non.resized image \"{}\" to \"{}\".".format( srcFile, destFile ) )
				shutil.copy2( srcFile, destFile )

