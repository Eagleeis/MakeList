###########################################################################################################################
# Brief:	Script to copy pictures in sub directories (acc. filter defined in options)
#			to a target folder. (Movies and other filetypes will be ignored)
#			Helper class for Python script makeList.py to
#				1) copy Apple pictures
#				2) resize or rotate pictures
# Author:	Jan Blumenthal (eagleeis@gmx.de)
#
# Examples:
#
# Copy apple pictures from folder "%SRCDIR%" to "%DESTDIR%" but each picture only once (extended or orginal)
# Note:	This script must only be called once because next turn would move original pictures since extended
#		were moved in first run!
# python makeList.py -a -d="%SRCDIR%" --is="import toolsPictures;tp=toolsPictures.ApplePictureTools(makeList,True)" --filterSnippet="tp.checkIPhonePicture(curDir,filePath)" --os="utils.moveFile(filePath,os.path.join(r'%DESTDIR%', os.path.basename(filePath)),overwrite=False)" --ip -D -v
###########################################################################################################################
import os
import traceback
import shutil
from PIL import Image


###########################################################################################################################
class ApplePictureTools:	
	""" This class is used to copy/move pictures from a folder holding unchanged copies of image data
		directly copied from IPhone (e.g. IMG_1234.aae, IMG_1234.jpg, IMG_E1234...). Focus is to copy
		just the desired pictures (Extended (IMG_E1234.JPG) or if not exist, the orginal (IMG_1234.JPG)).
	"""

	#######################################################################################################################
	def __init__( self, makeList, printExcluded = False ):
		self.__makeList			= makeList						# Not fully initialized at this moment!
		self.__dryMode			= makeList.getDryMode()
		self.__verbose			= makeList.getVerbose()
		self.__verboseVerbose	= makeList.getVerboseVerbose()
		self.__printExcluded	= printExcluded

	#######################################################################################################################
	def checkIPhoneAdaptedPicture( self, srcDir, srcFile ):
		bName, ext	= os.path.splitext( srcFile )
		try:
			prefix, suffix	= bName.split( "_", 1 )
		except:
			return None

		for b in ( True, False ):
			for e in ( True, False ):
				testFileName	= "{}_E{}{}".format( ( prefix.upper() if b else prefix ), suffix, ext.upper() if e else ext )
				return os.path.isfile( testFileName )
		return None

	#######################################################################################################################
	def __checkIPhonePicture(	self, srcDir, srcFile, srcPath, selectOriginalAlways, selectSingularOriginal,
								selectExtended, selectOthers, selectAAE ):
		if srcFile:
			srcLower	= srcFile.lower()
			if srcLower.endswith( ".aae" ):
				if self.__verboseVerbose:
					print( "File \"{}\" is an apple extension file. {}.".format( srcPath, "Included" if selectAAE else "Excluded" ) )
				return selectAAE
			if srcLower.startswith( "img_" ):
				if srcLower.startswith( "img_e" ):
					if self.__verboseVerbose:
						print( "The file \"{}\" is already an extended file. Included.".format( srcPath ) )
					return selectExtended
				if selectOriginalAlways:
					if self.__verboseVerbose:
						print( "The file \"{}\" is an image file. Included.".format( srcPath ) )
					return True
				# Check, if there is an "EXTENDED" file (e.g. IMG_1234.JPG -> IMG_E1234.JPG)
				checkName = self.checkIPhoneAdaptedPicture( srcDir, srcFile )
				if checkName:
					if self.__verboseVerbose:
						print( "The file \"{}\" has an extended file and is therefore ignored.".format( srcPath ) )
					return False
				if self.__verboseVerbose:
					print( "The file \"{}\" has no extended file and is therefore included.".format( srcPath ) )
				return selectSingularOriginal
		if self.__verboseVerbose:
			print( "The file \"{}\" is not a supported image file. {}.".format( srcPath, "Included" if selectOthers else "Excluded" ) )
		return selectOthers

	#######################################################################################################################
	def checkIPhonePicture(	self, srcDir, srcFile, selectOriginalAlways = False, selectSingularOriginal = True,
							selectExtended = True, selectOthers = True, selectAAE = False, inverseSelection = False ):
		srcPath	= os.path.join( srcDir, srcFile ) if srcDir else srcFile
		rc		= self.__checkIPhonePicture( srcDir, srcFile, srcPath, selectOriginalAlways, selectSingularOriginal,
											 selectExtended, selectOthers, selectAAE )
		result	= rc ^ inverseSelection
		if self.__verboseVerbose and inverseSelection:
			print( "Selection of \"{}\" inverted to: ".format( srcPath, result ) )
		if self.__printExcluded and not result:
			print( "File \"{}\" excluded.".format( srcPath ) )
		return result


###########################################################################################################################
class PictureTools:	

	#######################################################################################################################
	def __init__( self, makeList, maxWidth = None, maxHeight = None, swapFormat = False ):
		self.__makeList			= makeList		# Not fully initialized at this moment!
		self.__dryMode			= makeList.getDryMode()
		self.__verbose			= makeList.getVerbose()
		self.__verboseVerbose	= makeList.getVerboseVerbose()
		self.__maxHeight		= maxHeight		# \ maxHeight + maxWidth for
		self.__maxWidth			= maxWidth		# / landscape formats (default)
		self.__swapFormat		= swapFormat	# swap maxHeight and maxWidth in portrait format 

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

