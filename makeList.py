###########################################################################################################################
# Brief : Scan specified folders and their sub folders for files and write
#         the list line-by-line to a file (.m3u). Existing files will be overwritten.
# Author: Jan Blumenthal (eagleeis@gmx.de)
# Usage : python makeList.py -h
###########################################################################################################################
import collections
import traceback
import argparse
import codecs
import locale
import math
import copy
import shutil
import glob
import fnmatch
import traceback
import os
import re
import sys

###########################################################################################################################
defListsFolder			= "lists"

# Default extensions which will be party of m3u lists
extensionsMusic			= ".wma,.mpa,.wav,.mp3,.m4a,.ogg,.flac,.au"
# Ignore the following extensions while scanning for music files (output type: m3u)
ignoreExtensionsMusic	=".txt,.jpg,.bmp,.gif,.png,.tif,.tiff,.ini,.m3u,.lst,.cue,.nfo,.sfv,.pdf,.doc,.rtf,.xls,.xlsx,.html,.htm,.url,.pls,.ape,.apl"
# Default extensions which will be party of m3u lists
extensionsPictures		= ".jpg,.jpeg,.bmp,.gif,.png,.tif,.tiff,.dvi"
extensionsMovies		= ".mov,.mp4,.avi,.mpg,.mpeg,.mkv,.wmv,.webm,.mts,.vob"


###########################################################################################################################
reSplit	= re.compile( r'(\d+)' )
def humanSortIgnoreKey( s ):
	return [ int( t ) if i & 1 else t.lower() for i, t in enumerate( reSplit.split( s ) ) ]

###########################################################################################################################
class MLException( Exception ):
	pass

###########################################################################################################################
class Utils:
	#######################################################################################################################
	def __init__( self, makeList ):
		self.__dryMode			= makeList.getDryMode()
		self.__verbose			= makeList.getVerbose()
		self.__verboseVerbose	= makeList.getVerboseVerbose()

	#######################################################################################################################
	# Copy /srcFile/ to /destFile/ including stat information (date, access...) and mode
	# information (user, group...)
	def copyFile( self, srcFile, destFile, skipErrors = False, overwrite = True, copyStat = True, copyMode = True,
		stripFilenames = True, skipInvalidFilenames = True, skipNonExisting = False, verbose = None ):
		skipEntry		= True
		verbose			= self.__verbose and verbose is None or verbose 
		if stripFilenames:
			srcFile		= srcFile.strip()
			destFile	= destFile.strip()
		if srcFile or not skipInvalidFilenames:
			skipEntry	= False
			if self.__dryMode:
				if verbose:
					print( "Skipped copying \"{}\" to \"{}\".".format( srcFile, destFile ) )
			else:
				if verbose:
					print( "Copying \"{}\" to \"{}\".".format( srcFile, destFile ) )
				try:
					if os.path.exists( srcFile ):
						dirPath	= os.path.dirname( destFile )
						if dirPath and not os.path.isdir( dirPath ):
							def createParent( spDir, dpDir ):
								sppDir	= os.path.dirname( spDir )
								dppDir	= os.path.dirname( dpDir )
								if dppDir and not os.path.isdir( dppDir ):
									createParent( sppDir, dppDir )
								os.makedirs( dpDir )
								if copyStat:
									shutil.copystat( spDir, dpDir )
								elif copyMode:
									shutil.copymode( spDir, dpDir )
							createParent( os.path.dirname( srcFile ), dirPath )
						if os.path.isfile( destFile ):
							if overwrite:
								os.remove( destFile )
							elif overwrite is None:
								if verbose:
									print( "File \"{}\" already exists! Copying skipped.".format( destFile ) )
								return skipEntry, destFile 
							else:
								raise MLException( "File \"{}\" already exists!".format( destFile ) )
						if copyStat:
							shutil.copy2( srcFile, destFile )
						else:
							shutil.copy( srcFile, destFile )
							if copyMode:
								shutil.copymode( srcFile, destFile )
					else:
						if not skipNonExisting:
							raise MLException( "File \"{}\" does not exist!".format( srcFile ) )
						if skipInvalidFilenames:
							skipEntry	= True
				except Exception as e:
					if not skipErrors:
						raise
					else:
						sys.stderr.write( "Copy Error: {}\n".format( e ) )
		return skipEntry, destFile

	#######################################################################################################################
	def moveFile( self, srcFile, destFile, skipErrors = False, overwrite = True ):
		if self.__dryMode:
			if self.__verbose:
				print( "Skipped moving \"{}\" to \"{}\".".format( srcFile, destFile ) )
		else:
			if self.__verbose:
				print( "Moving \"{}\" to \"{}\".".format( srcFile, destFile ) )
			try:
				dirPath	= os.path.dirname( destFile )
				if not os.path.isdir( dirPath ):
					os.makedirs( dirPath )
				if os.path.isfile( destFile ):
					if overwrite:
						os.remove( destFile )
					else:
						raise MLException( "File already exists!" )
				shutil.move( srcFile, destFile )
			except:
				if not skipErrors:
					raise
				else:
					sys.stderr.write( "Move Error: {}\n".format( e ) )

	#######################################################################################################################
	def removeFile( self, srcFile, skipErrors = False, removeEmptyDirs = True ):
		if self.__dryMode:
			if self.__verbose:
				print( "Skipped removing \"{}\".".format( srcFile ) )
		else:
			if self.__verbose:
				print( "Removing \"{}\".".format( srcFile ) )
			try:
				os.remove( srcFile )
				if removeEmptyDirs:
					def __removeDirs( pDir ):
						if os.path.exists( pDir ) and not os.listdir( pDir ):
							if self.__verbose:
								print( "Removing empty directory \"{}\".".format( pDir ) )
							os.removedirs( pDir )
							__removeDirs( os.path.dirname( pDir ) )
					__removeDirs( os.path.dirname( srcFile ) )
			except:
				if not skipErrors:
					raise
				else:
					sys.stderr.write( "Remove Error: {}\n".format( e ) )


###########################################################################################################################
class MakeList:

	#######################################################################################################################
	def __init__( self, listsFolder, extensions, ignore, excludedDirectories, outputMode, ignoreScanErrors,
				  fmtOnlyEntries, fmtAllSubEntries, fmtLists, fmt, fmtEntry, initSnippet, snippet,
				  writeEmptyLists, outputType, dryMode, outputEncoding, verbose, verboseVerbose ):
		if listsFolder is None and fmtLists:
			raise MLException( "If option /fmtLists/ is specified, you need to specify a lists folder!" )
		self.__listsFolder			= os.path.abspath( os.path.normpath( listsFolder ) ) if listsFolder else None
		self.__outputType			= outputType
		self.__snippet				= snippet				# Python snippet to filter elements
		self.__dryMode				= dryMode
		self.__verbose				= verbose
		self.__verboseVerbose		= verboseVerbose
		self.__ignoreScanErrors		= ignoreScanErrors
		self.__writeEmptyLists		= writeEmptyLists		# True: Do not write empty lists, just remove existing lists
		self.__excludedDirectories	= excludedDirectories	# folders within /listsFolder/ to be excluded
		self.__globals				= self.__initGlobals( initSnippet )		# Globals for snippets

		defListExtension			= None					# Extension of generated lists
		defExtensions				= None					# Allowed extensions in files or None for all
		defIgnore					= None					# Ignore all other file types which are not in /extensions/
		defOutputMode				= None
		defFmtOnlyEntries			= None					# Format string of file path of a list written after scanning a directory (without contents of sub directories).
		defFmtAllSubEntries			= None					# Format string of file path of a list written after scanning a directory and its sub directories
		defFmtLists					= None					# Format string of file path of same list as described in option --fmtAllSubEntries but to be written to the listsFolder
		defOutputEncoding			= locale.getencoding()

		defFmt						= None					# Format string for output list.
		defFmtEntry					= None					# Format string for an entry in output list.
		if outputType is None:
			pass
		elif outputType == "pictures":
			defListExtension			= ".lst"
			defExtensions				= extensionsPictures
		elif outputType == "movies":
			defListExtension			= ".lst"
			defExtensions				= extensionsMovies
		elif outputType == "music":
			defListExtension			= ".lst"
			defExtensions				= extensionsMusic
		elif outputType == "media":
			defListExtension			= ".lst"
			defExtensions				= "{},{},{}".format( extensionsPictures, extensionsMovies, extensionsMusic )
		elif outputType == "fileList":
			defListExtension			= ".lst"
			defFmtLists					= "{0}{3}"
		elif outputType == "m3u":							# Create m3u lists in all folders and sub folders, uses locale encoding
			defListExtension			= ".m3u"
			defExtensions				= extensionsMusic
			defIgnore					= ignoreExtensionsMusic
			defOutputMode				= "unix"
			defFmtAllSubEntries			= "{0}{3}"
			defFmtLists					= "{0}{3}"
		elif outputType == "m3uExt":						# Create m3uExt lists in all folders and sub folders
			defOutputEncoding			= "utf8"
			defListExtension			= ".m3u8"
			defExtensions				= extensionsMusic
			defIgnore					= ignoreExtensionsMusic
			defOutputMode				= "unix"
			defFmtAllSubEntries			= "{0}{3}"
			defFmtLists					= "{0}{3}"
			#defFmtEntry				= "file:///{0}"
			defFmt						= "#EXTM3U\n{0}"
		else:
			raise MLException( "Unsupported output type \"{}\" specified!".format( outputType ) )


		self.__outputEncoding		= outputEncoding if outputEncoding is not None else defOutputEncoding
		self.__listExtension		= defListExtension

		# extensions:	Extensions to be added to the list. All other extensions are ignored. 
		if extensions is not None:
			self.__extensions		= { _.strip().lower() for _ in self.resolveExtensions( extensions, defExtensions, self.__listExtension ) } \
										if extensions != "" else None
		else:
			self.__extensions		= { _.strip().lower() for _ in defExtensions.split( "," ) } \
										if defExtensions is not None else None

		# ignore:		Extensions to be ignored. All other extension lead to a warning to STDERR. If None, check is disabled. 
		# Files to be ignored and not parts of /self.__extensions/ without warning
		if ignore is not None:
			self.__lIgnore			= { _.strip().lower() for _ in ignore.split( "," ) } \
										if ignore != "" else None
		else:
			self.__lIgnore			= { _.strip().lower() for _ in defIgnore.split( "," ) } \
										if defIgnore is not None else None

		# Default format strings of paths to output lists
		# {0}	default path of specific list without extension, see {3}
		# {1}	original specified name of scanned directory
		# {2}	same as {1} but "." instead of ""
		# {3}	default extension of list
		# {4}	prefix, e.g. $MYMUSIC
		# {5}	os.sep
		# {6}	os.pathsep
		# {7}	lists folder as defined while construction the instance

		# Only files in folder (not sub directories), if defined. Example: "{0}_Single{3}"
		self.__fmtOnlyEntries		= fmtOnlyEntries	if fmtOnlyEntries is not None	else defFmtOnlyEntries
		# All entries and sub entries, if defined.
		self.__fmtAllSubEntries		= fmtAllSubEntries	if fmtAllSubEntries is not None	else defFmtAllSubEntries
		# Lists in separate folder holding all entries incl. contents of sub directories
		self.__fmtLists				= fmtLists			if fmtLists is not None 		else defFmtLists
		self.__fmt					= fmt				if fmt is not None				else defFmt
		self.__fmtEntry				= fmtEntry			if fmtEntry is not None			else defFmtEntry

		if outputMode is None:
			outputMode	= defOutputMode
		if outputMode is None:
			self.__reformatEntries	= self.__reformatNone
		else:
			outputMode	= outputMode.lower()
			if outputMode == "unix":
				self.__reformatEntries	= self.__reformatUNIX
			elif outputMode == "windows":							# rel. path of Windows
				self.__reformatEntries	= self.__reformatWindows
			elif not outputMode or outputMode == "none":
				self.__reformatEntries	= self.__reformatNone
			else:
				raise MLException( "Unsupported output mode option \"{}\" specified!".format( outputMode ) )
		self.__utils				= Utils( self )

	#######################################################################################################################
	def printInputSettings( self ):
		print( "Lists Folder                 :", self.__listsFolder )
		print( "Excluded Directories         :", self.__excludedDirectories ) # folders within /listsFolder/ to be excluded
		print( "Extensions to be included    :", self.__extensions )
		print( "Extensions to be ignored     :", self.__lIgnore )
		print( "Filter Snippet               :", self.__snippet )
		print( "Globals for snippets         :", ", ".join( self.__globals ) if self.__globals else None )

	#######################################################################################################################
	def printOutputSettings( self ):
		print( "Dry Mode                     :", self.__dryMode )
		print( "Output Encoding              :", self.__outputEncoding )
		print( "Output List Entension        :", self.__listExtension )
		print( "Write Empty Lists            :", self.__writeEmptyLists )
		print( "Reformat Entries             :", self.__reformatEntries )
		print( "Format                       :", self.__fmt )
		print( "Format Lists                 :", self.__fmtLists )
		print( "Format Entry                 :", self.__fmtEntry )
		print( "Format Only Entries          :", self.__fmtOnlyEntries )
		print( "Format All Sub Entries       :", self.__fmtAllSubEntries )

	#######################################################################################################################
	# Resolve the following place holders in extenion string:
	#	{0}			default extensions associated with selected output type
	#	{1}			extension of list associated with selected output type
	#	{2}			extensions of pictures
	#	{3}			extensions of movies
	#	{4}			extensions of music
	def resolveExtensions( self, extensions, default, listExtension ):
		pictures	= extensionsPictures
		movies		= extensionsMovies
		music		= extensionsMusic
		return extensions.format( default, listExtension, pictures, movies, music ).split( "," )
	
	#######################################################################################################################
	def getVerbose( self ):
		return self.__verbose

	#######################################################################################################################
	def getUtils( self ):
		return self.__utils

	#######################################################################################################################
	def getVerboseVerbose( self ):
		return self.__verboseVerbose

	#######################################################################################################################
	def getDryMode( self ):
		return self.__dryMode

	#######################################################################################################################
	def __reformatNone( self, s ):
		return s

	#######################################################################################################################
	def __reformatUNIX( self, s ):
		return s.replace( "\\", "/" )

	#######################################################################################################################
	def __reformatWindows( self, s ):
		return s.replace( "/", "\\" )

	#######################################################################################################################
	def __getOutput( self, lines ):
		fmtEntry	= self.__fmtEntry
		if fmtEntry is not None:
			oStr	= "\n".join( [ fmtEntry.format( _ ) for _ in lines ] )
		else:
			oStr	= "\n".join( lines )

		if self.__fmt is not None:
			return self.__fmt.format( oStr )
		return oStr

	#######################################################################################################################
	def __writeList( self, listPath, lines ):
		listPath	= os.path.abspath( listPath )
		dirName		= os.path.dirname( listPath )

		if lines or self.__writeEmptyLists:
			if not os.path.exists( dirName ):
				if self.__verbose:
					print( "Creating new directory \"{}\".".format( dirName ) )
				if not self.__dryMode:
					os.makedirs( dirName )
			if self.__verbose:
				print( "Writing \"{}\" ({} {}).".format( listPath, len( lines ), ( "line" if len( lines ) == 1 else "lines" ) ) )
				if self.__verboseVerbose:
					print( self.__getOutput( lines ) )
		if os.path.exists( listPath ):
			try:
				if self.__verboseVerbose:
					print( "Removing existing file \"{}\".".format( listPath ) )
				if not self.__dryMode:
					os.remove( listPath )
			except:
				sys.stderr.write( "Cannot remove existing path \"{}\"! Ignored.\n".format( listPath ) )
		try:
			if not self.__dryMode:
				if lines or self.__writeEmptyLists:
					if self.__verbose:
						print( "Opening output file \"{}\" with encoding \"{}\".".format( listPath, self.__outputEncoding ) )
					f = codecs.open( listPath, "w", self.__outputEncoding )
					try:
						f.write( self.__getOutput( lines ) )
					except UnicodeEncodeError as e:
						# Most probably an encoding problem. Write line-by-line to ignore problematic line
						for numLine, line in enumerate( lines ):
							try:
								f.write( line + "\n" )
							except:
								sys.stderr.write( "Skipped file \"{}\" while writing with encoding \"{}\". Reason: {}\n".format( line.encode( self.__outputEncoding , "ignore" ), self.__outputEncoding, str( e ) ) )
				elif self.__verbose:
					sys.stderr.write( "Skipping writing empty file \"{}\".\n".format( listPath ) )
			elif self.__verbose:
				sys.stderr.write( "Writing file \"{}\" skipped due to dry mode.\n".format( listPath ) )
		except:
			sys.stderr.write( traceback.format_exc() )
			sys.stderr.write( "Cannot write list to file \"{}\"!\n".format( listPath ) )

	#######################################################################################################################
	def __warnExtension( self, d, f ):
		toIgnore	= self.__lIgnore
		if toIgnore is not None and ( f in toIgnore or os.path.splitext( f )[ 1 ].lower() in toIgnore ):
			sys.stderr.write( "File \"{}\" has a file extension configured to be skipped! Ignored.\n".format( os.path.join( os.getcwd(), d, f ) ) )
			return False
		return True

	#######################################################################################################################
	def __scanDir( self, prefix, d, scanSubDirectories, preventRedundantLists ):
		extensions			= self.__extensions
		reformat			= self.__reformatEntries
		dReal				= d if d else "."
		dBaseName			= os.path.basename( d ) if d else None			# Name of current directory
		excludedDirectories = self.__excludedDirectories

		if not excludedDirectories or not dReal in excludedDirectories:
			if self.__verbose:
				print( "Scanning folder \"{}\".".format( dReal ) )
			try:
				allItems	= [ _ for _ in sorted( os.listdir( dReal ), key = humanSortIgnoreKey ) ]
			except Exception as e:
				if not self.__ignoreScanErrors:
					raise
				sys.stderr.write( "Cannot scan directory \"{}\". Reason: {}\n".format( dReal, e ) )
				allItems	= []
			subDirs		= [ _ for _ in allItems if os.path.isdir( os.path.join( dReal, _ ) ) ]
			files		= [ _ for _ in allItems if _ not in subDirs and ( _ in extensions or os.path.splitext(_)[ 1 ].lower() in extensions and self.__warnExtension( d, _ ) ) ]		\
							if extensions != None else [ _ for _ in allItems if _ not in subDirs and self.__warnExtension( d, _ ) ]
			numFiles	= len( files )

			# Write list of folder contents without contents of sub folders
			if self.__fmtOnlyEntries:
				defListPath	= os.path.join( dReal, os.path.basename( d if dReal != "." else os.getcwd() ) )
				listPath	= self.__fmtOnlyEntries.format( defListPath, d, dReal, self.__listExtension, prefix,
															os.sep, os.pathsep, self.__listsFolder )
				self.__writeList( listPath, files )

			# Scan and add contents of sub folders. Count directories with sub contents to prevent writing redundant
			# lists, if /preventRedundantLists/ is True.
			countDirsWithContents	= 0
			def __count( l ):
				nonlocal countDirsWithContents
				countDirsWithContents	+= 1 if len( l ) else 0
				return l

			if scanSubDirectories:
				[ files.extend( __count( self.__scanDir( prefix, os.path.join( d, _ ) if d else _, scanSubDirectories, preventRedundantLists ) ) ) for _ in subDirs ]

			# Write list of contents (including contents of sub directories) directly into current folder
			if self.__fmtAllSubEntries:
				defListPath	= os.path.join( dReal, os.path.basename( d if dReal != "." else os.getcwd() ) )
				listPath	= self.__fmtAllSubEntries.format( defListPath, d, dReal, self.__listExtension, prefix,
															  os.sep, os.pathsep, self.__listsFolder )
				self.__writeList( listPath, files )

			# Write list of entries (including contents of sub directories) into a separate folder holding all lists.
			if self.__listsFolder and self.__fmtLists:
				if dReal == ".":
					listName= ""
				else:
					listName= d.replace( "\\", "_" ).replace( "/", "_" ).replace( ":", "_" )
				defListPath	= os.path.join( self.__listsFolder, listName )
				listPath	= self.__fmtLists.format( defListPath, d, dReal, self.__listExtension, prefix,
													  os.sep, os.pathsep, self.__listsFolder )
				if preventRedundantLists and countDirsWithContents <= 1 and not numFiles:#len( subDirs ) == 1 or len( subDirs ) > 1 and :# or len( files ) == numFiles + 1:
					if self.__verbose:
						print( "Writing redundant list \"{}\" skipped!".format( listPath ) )
				else:
					if prefix:
						relDir	= os.path.join( prefix, d )
						lFiles	= [ reformat( os.path.join( relDir, _ ) ) for _ in files ]
					else:
						lFiles	= [ reformat( _ ) for _ in files ]
					self.__writeList( listPath, lFiles )

			return [ reformat( os.path.join( dBaseName, _ ) ) for _ in files ] if dBaseName else files
		if self.__verbose:
			print( "Folder \"{}\" excluded from scanning.".format( dReal ) )
		return []

	#######################################################################################################################
	def __initGlobals( self, initSnippet ):
		g	= {	"os"		: os,
				"sys"		: sys,
				"re"		: re,
				"glob"		: glob,
				"math"		: math,
				"copy"		: copy,
				"shutil"	: shutil,
				"fnmatch"	: fnmatch,
				"traceback"	: traceback,
			  }
		if initSnippet is not None:
			l					= {	"makeList"			: self,
									"verbose"			: self.__verbose,
									"verboseVerbose"	: self.__verboseVerbose,
								  }
			exec( initSnippet, g, l )
			g.update( l )
		return g

	#######################################################################################################################
	def getGlobals( self ):
		return self.__globals

	#######################################################################################################################
	def startScanning( self, prefix, directory, scanSubDirectories, preventRedundantLists, ignorePythonErrors ):
		oldDir		= os.getcwd()
		dReal		= directory if directory else "."
		try:
			if prefix is None and self.__listsFolder:
				try:
					prefix	= os.path.relpath( dReal, self.__listsFolder )
				except ValueError:								# dReal and self.__listsFolder are on different drives
					prefix	= os.path.abspath( dReal )
			os.chdir( dReal )
			if self.__verbose:
				print( "Current directory tree : {}".format( os.getcwd() ) )
				if self.__verboseVerbose:
					print( "Excluded directories   : {}".format( self.__excludedDirectories ) )
					print( "Allowed file extensions: {}".format( self.__extensions ) )
					print( "Skipped file extensions: {}".format( self.__lIgnore ) )
				if self.__listsFolder:
					print( "Current lists folder  : {}".format( self.__listsFolder ) )
					print( "Prefix                : {}".format( prefix ) )
			files	= self.__scanDir( prefix, "", scanSubDirectories, preventRedundantLists )

			if self.__snippet:
				try:
					snippet	= compile( self.__snippet, "filterSnippet", "eval" )
					l		= {	# Keep consistent with printing settings using "verboseVerbose"
								"filePath"		: None,
								"curDir"		: dReal,
								"utils"			: makeList.getUtils(),
							  }
					g		= self.__globals
					def checkSnippet( f ):
						l[ "filePath" ]	= f
						try:
							if self.__verboseVerbose:
								print( "Check include filter by python snippet for file \"{}\".".format( f ) )
							return eval( snippet, g, l )
						except Exception as exc:
							if not ignorePythonErrors:
								raise
							if not isinstance( exc, MLException ):
								traceback.print_tb( exc.__traceback__, None, None )
							sys.stderr.write( "Entry \"{}\" excluded.\n".format( f ) )
							return False					# Exclude, if exception occurred.
					files	= [ f for f in files if checkSnippet( f ) ]
				except:
					if not ignorePythonErrors:
						raise
					traceback.print_tb( exc.__traceback__, None, None )
			return files
		finally:
			os.chdir( oldDir )

###########################################################################################################################
examples = r"""
This script supports the following output types:
m3u      Create m3u lists in any specified directory and its sub directories
m3uext   Create m3u lists in any specified directory and its sub directories
music    Scan for music
movies   Scan for movies
pictures Scan for pictures
fileList Make a list of all files

Here are some examples, how to use this script (Note: Option -D activates dry mode!):

###########################################################################################################################
Scan current folder and sub folders and write relative path of each file to STDOUT
Usage: makeList.py

###########################################################################################################################
Create a list of all files in specified directory "%SCANFOLDER%" and its sub directories, but
not the files within sub directory "foo\bar". All files shall be written with absolute path
and encoded with "utf8".
Usage: makeList.py --type=fileList -d="%SCANFOLDER%" -x="foo\bar" -v --absPath -E=utf8 -o="%TARGETLIST%"

###########################################################################################################################
Scan current folder and sub folders for supported pictures and write relative
path of each file to STDOUT
Usage: makeList.py -t=pictures -o="-"

###########################################################################################################################
Scan specified folder "e:\music" and its sub folders. Write an m3u list to any
folder and to the "__lists__" folder.
Usage: makeList.py -d=e:\music -l=e:\music\_lists_ -t=m3u

###########################################################################################################################
Create lists of folder "e:\music" and all its sub folders and write all
m3u lists to the specified folder. Each line in written files shall have
the prefix "../" followed by the relative path of any selected file.
Usage: makeList.py -d=e:\music --fmtOnlyEntries="" --fmtAllSubEntries="" -l=lists -p=../ -t=m3u

###########################################################################################################################
Just print all .py and .lst files to STDOUT
Usage: makeList.py -D -o=- -d=myDir -e=.py,.lst

###########################################################################################################################
Print all movies in specified folder and its sub folders to STDOUT. Ignore all other
file extensions. If dryMode is removed (-D), all sub folder lists will be written to
"c:\data\temp\list" in the "m3uExt" format and a relative path prefix "../../" which
can easily be opened in VLC.
makeList.py -o=- -i="" -e=".mov,.mp4,.avi,.mpg,.mpeg,.mkv,.wmv,.webm,.mts,.vob" -i="" --fmtOnlyEntries="" --fmtAllSubEntries="" -l=c:\data\temp\list -p=../../ -t=m3uExt -d="e:\gfx" -D

###########################################################################################################################
Print all .ogg and .mp3 files filtered by external custom snippet which checks, if the file path
contains " Bach" in the path.
makeList.py -e=.mp3,.ogg -d="e:\music\Jazz" --filterSnippet="fnmatch.fnmatch( filePath, '* Bach*')"

###########################################################################################################################
Copy all media files (pictures,music,movies) located at %SRC% including applicable folder structure
to %DEST%. Consider to set utils.copyFile(skipError=True)
makeList.py -d="%SRC%" -t=media --os="utils.copyFile(r'%SRC%\\'+filePath,r'%DEST%\\'+filePath)" -v

###########################################################################################################################
Move all media files (pictures,music,movies) located at %SRC% into one(!) %DEST% folder. Consider
to set utils.moveFile(skipError=True)
makeList.py -d="%SRC%" -t=media --os="utils.moveFile(r'%SRC%\\'+filePath,r'%DEST%\\'+os.path.basename(filePath))" -v

###########################################################################################################################
Copy all selected files (filePath contains "* Bach*") to the folder "c:\data\temp\list" using
a custom Python snippet. All files will be copied into one folder!
makeList.py -a -o="" -d="e:\music\Jazz" --filterSnippet="fnmatch.fnmatch( filePath, '* Bach*')" --os="utils.copyFile( filePath, 'c:\\data\\temp\\list\\' + os.path.basename( filePath ) )" -v

###########################################################################################################################
Copy all selected movies with partial parts "*\\HT0*" to the existing folder "c:\data\temp\list"
using a custom Python snippet.
makeList.py -a -o="" -t=movies -d="e:\gfx\Ausflüge" --filterSnippet="fnmatch.fnmatch( filePath, '*\\*HT0*')" --os="utils.copyFile( filePath, 'c:\\data\\temp\\list\\' + os.path.basename( filePath ) )" -v -D

###########################################################################################################################
Remove all list files of types (.sld, .m3u, .m3u8) within folder %GFX% but not in sub folder "_Playlisten_".
Consider activated dry mode!
makeList.py -a -o="" -d=%GFX% -e=".sld,.lst,.m3u,.m3u8" -x=_Playlisten_ --vv -v --outputSnippet="sys.stdout.write('Skipping removal of \"{}\" due to activated dry mode.\n'.format(filePath)) if dryMode else (sys.stdout.write('Removing \"{}\".\n'.format(filePath)) and os.remove(filePath))" -D

###########################################################################################################################
Print table of movies with file size and used codec. This examples shows how to import an external class
used for filtering and outputting.
makeList.py -d=%GFX% -t=movies --initSnippet="import videoInfo;wi=videoInfo.VideoChecker(makeList,'{0:<90}\t{3:>15_}\t{4}')" --filterSnippet="wi.filter(curDir,filePath)" --os=outputEntry=wi.output(filePath) -o="-"

###########################################################################################################################
Same as before but size if printed in GB with 2 decimal places.
makeList.py -d=%GFX% -t=movies --initSnippet="import videoInfo;wi=videoInfo.VideoChecker(makeList,'{0:<90}\t{3:>15_.2f}\t{4}',1/1024/1024)" --filterSnippet="wi.filter(curDir,filePath)" --os=outputEntry=wi.output(filePath) -o="-"

###########################################################################################################################
Copy files defined a list (line-by-line) to another folder including directory structure.
makeList.py -d=e:\copyListe.txt --os="src='m:\\Movies_1\\'+filePath.strip();outputEntry='d:\\'+filePath.strip();utils.copyFile(src,outputEntry ) if filePath.strip() and not os.path.exists(outputEntry) else print('Skipped')" --ip -v

"""

###########################################################################################################################
# Main
parser = argparse.ArgumentParser( prog = "Make a file list", description = "Scan specified folders and their sub folders for files and output the list line-by-line." )
parser.add_argument( "-v", "--verbose", action = "store_true", help = "Enable verbose mode." )
parser.add_argument( "--vv", "--verboseVerbose", dest = "verboseVerbose", action = "store_true", help = "Enable very verbose mode." )
parser.add_argument( "--ex", "--examples", dest = "examples", action = "store_true", help = "Show some examples how to use this script." )

gInput = parser.add_argument_group( "Input options" )
gInput.add_argument( "-d", "--directory", dest = "directories", help = "Start directory to be scanned. Option may be multiple defined. Default: \"\"", action = "append", default = None )
gInput.add_argument( "-x", "--excludeDirectory", dest = "excludedDirectories", help = "Directory to be excluded from scanning. Path must be relative to --directory. Option may be multiple defined. Default: \"\"", action = "append", default = None )
gInput.add_argument( "-e", "--extensions", help = "List of supported extensions as comma-separated string which will be part of the output list. The following place holders will be resolved: {0} comma-separated list of extensions associated with the output type, {1}: default list extension, {2}: default picture extensions, {3}: default movies extensions, {4}: default music extensions. Set to \"\" to add all files. Default: Default extensions of output type", default = None )
gInput.add_argument( "-i", "--ignore", help = "List of extensions to be ignored while scanning. All other extensions will raise a warning to STDOUT. Set to \"\" to skip this feature. Default: Default ignores of output type", default = None )
gInput.add_argument( "-N", "--noSubDirs", action = "store_true", help = "Do not scan sub directories." )
gInput.add_argument( "--is", "--initSnippet", dest = "initSnippet", help = "Python snippet to initialize the snippets and prepare globals for Python snippets. The following globals are provided: os, sys, re, glob, copy, math, shutil, fnmatch, traceback. The following locals are provided: makeList, verbose and verboseVerbose. Default: None", default = None )
gInput.add_argument( "-I", "--inputEncoding", help = "The encoding to be used in input lists. Default: {}".format( locale.getencoding() ), default = None )
gInput.add_argument( "--ie", "--ignoreScanErrors", dest = "ignoreScanErrors", action = "store_true", help = "Ignore errors while scanning. Default: False.", default = False )

gOutput = parser.add_argument_group( "Output options" )
gOutput.add_argument( "-t", "--type", dest = "outputType", help = "Type of output lists. Valid options are: fileList, pictures, movies, music, media, m3u, m3uExt. Default: None", default = None )
gOutput.add_argument( "-m", "--mode", dest = "outputMode", help = "Output Mode of directory separators. Options are: None: Native separator, UNIX: Output list with \"/\" separator, Windows: Output list with \"\\\" separator. Default: Default output mode of output type", default = None )
gOutput.add_argument( "-l", "--listsFolder", help = "A folder any list shall also be written to. All path and drive separators shall be converted to \"_\". Default: Disabled", default = None )
gOutput.add_argument( "-s", "--filterSnippet", help = "Python snippet (type eval) to be customized while scanning to check, if an entry should be included or not. The following globals are defined: os, re, sys, glob, copy, math, shutil, fnmatch, traceback. The following locals are defined: filePath, curDir, utils. Default: Disabled", default = None )
gOutput.add_argument( "-p", "--prefix", help = "A prefix which shall be added to any element in the lists written to the lists folder (--listsFolder). This can be used to replace e.g. \"..\" to a place holder, e.g. $MYMUSIC. Default: Auto detected relative path from lists folder (--listsFolder) to folder to be scanned (see option --directory).", default = None )
gOutput.add_argument( "-E", "--encoding", help = "The encoding to be used in output lists. Default: {}".format( locale.getencoding() ), default = None )
gOutput.add_argument( "-W", "--writeEmptyLists", action = "store_true", help = "Do write empty lists. Default: Overwrite any list and write even empty content." )
gOutput.add_argument( "-D", "--dryMode", action = "store_true", help = "Dry mode. No changes will be done to disc. Default: False.", default = False )
gOutput.add_argument( "-o", "--output", help = "Output final list to specified file. Set to \"-\" to print to STDOUT. Set to \"\" to prevent printing to STDOUT. Default: STDOUT if outputType and --fmt* are not specified. Otherwise: None", default = None )
gOutput.add_argument( "-a", "--absPath", dest = "absPath", action = "store_true", help = "Create absolute path of entries in final outputs. Option has no effect to fmt lists. Default: False.", default = False )
gOutput.add_argument( "--os", "--outputSnippet", dest = "outputSnippet", help = "Python snippet (type: exec) executed for any final entry of output list in any case and independently on other options for any final line. The following globals are defined: os, re, sys, glob, copy, math, shutil, fnmatch, traceback. The following locals are defined: filePath, curDir, dryMode, utils. If locals[\"outputEntry\"] is defined after executing the snippet, it shall be written to the output instead \"filePath\". If locals[\"skipEntry\"] is True, the filePath shall be skipped. Default: Undefined.", default = None )
gOutput.add_argument( "--ip", "--ignorePythonErrors", dest = "ignorePythonErrors", action = "store_true", help = "Ignore exceptions in executed Python snippets. Default: False.", default = False )
	
gFmtList = parser.add_argument_group( "Output Lists",
"""This script can create lists in folders and sub folders, if the following options are specified. There are defaults depending on the output types. The following format strings can be used to change the file paths of the lists to be written. The following place holders shall be supported: {0}: default path of specific list without extension (see {3}),
{1}: original specified name of scanned directory,
{2}: same as {1} but "." instead of "",
{3}: default extension of list (.m3u),
{4}: applicable prefix (e.g. $MYMUSIC or ".."),
{5}: os.sep,
{6}: os.pathsep,
{7}: lists folder as defined while construction the instance,
""" )
gFmtList.add_argument( "--fmtOnlyEntries", help = "Format string of file path of a list written after scanning a directory (without contents of sub directories). Set to \"\" to skip writing such lists. Default: Default format specifier of output type", default = None )
gFmtList.add_argument( "--fmtAllSubEntries", help = "Format string of file path of a list written after scanning a directory and its sub directories. Set to \"\" to skip writing such lists. Default: Default format specifier of output type", default = None )
gFmtList.add_argument( "--fmtLists", help = "Format string of file path of same lists as described in option --fmtAllSubEntries but to be written to the listsFolder (--listsFolder), if specified. Set to \"\" to skip writing such lists. Default: Default format specifier of output type", default = None )
gOutput.add_argument( "--fmtTemplate", dest = "fmtTemplate", help = "Format template of main content read from specified file. ({0}: Formatted elements (see option --fmtEntry). Option cannot be specified together with --fmt! Default: \"{0}\"", default = None )
gOutput.add_argument( "--fmt", help = "Format template of main content ({0}: Formatted elements (see option --fmtEntry). Default: \"{0}\"", default = None )
gOutput.add_argument( "--fmtEntry", help = "Format template of a single entry ({0}: Path as read from source). Default: \"{0}\"", default = None )

args	= parser.parse_args()
if args.examples:
	print( examples.strip() )
else:
	verbose			= args.verbose
	verboseVerbose	= args.verboseVerbose
	fmt				= args.fmt
	fmtEntry		= args.fmtEntry
	fmtTemplate		= args.fmtTemplate
	if fmtTemplate:
		if fmt:
			raise MLException( "Specify either --fmtTemplate or --fmt!" )
		fmt			= open( fmtTemplate ).read()
	makeList	= MakeList( args.listsFolder, args.extensions if args.extensions is not None else None,
							args.ignore if args.ignore is not None else None, args.excludedDirectories,
							args.outputMode, args.ignoreScanErrors,
							args.fmtOnlyEntries, args.fmtAllSubEntries, args.fmtLists, fmt, fmtEntry,
							args.initSnippet, args.filterSnippet, args.writeEmptyLists,
							args.outputType, args.dryMode, args.encoding, verbose or verboseVerbose, verboseVerbose )
	results					= []
	preventRedundantLists	= True
	if args.output is not None:
		output				= args.output
	else:
		output				= args.output or \
								( args.outputType is None and args.fmtOnlyEntries is None and args.fmtAllSubEntries is None and args.fmtLists is None )
	ignorePythonErrors		= args.ignorePythonErrors
	absPath					= args.absPath								# Option has no effect on fmt lists
	collectResults			= output or args.outputSnippet
	inputDirectories		= args.directories if args.directories is not None else ( "", )

	if verboseVerbose:
		print( "Using the following input settings:" )
		print( "Input Directories            : \"{}\"".format( "\", \"".join( inputDirectories ) ) )
		print( "Input Encoding               :", args.inputEncoding )
		print( "Init Snippet                 :", args.initSnippet )
		print( "Ignore Python Errors         :", ignorePythonErrors )
		print( "Collect Results              :", collectResults )
		print( "Absolute Path                :", absPath )
		print( "Current directory            :", os.getcwd() )
		print( "Prefix                       :", args.prefix )
		print( "Verbose                      :", verbose )
		print( "Scan sub directories         :", not args.noSubDirs )
		makeList.printInputSettings()
		print( "Locals in Filter Snippets    : filePath, curDir, utils" )
		print( "Locals in Output Snippets    : filePath, curDir, dryMode, utils, skipEntry, [outputEntry]" )

		print( "\nUsing the following output settings:" )
		print( "Output mode                  :", args.outputMode )
		print( "Output Snippet               :", args.outputSnippet )
		print( "Prevent Redundant Lists      :", preventRedundantLists )
		print( "Output                       :", output )
		makeList.printOutputSettings()

		print( "" )

	for directory in inputDirectories:
		if directory == "" or os.path.isdir( directory ):
			if collectResults:
				subResults = makeList.startScanning(	args.prefix, directory, not args.noSubDirs,
														preventRedundantLists, ignorePythonErrors )
				if subResults:
					if absPath:
						subResults	= [ os.path.abspath( os.path.join( directory, _ ) ) for _ in subResults ]
					results.extend( subResults )
			else:
				makeList.startScanning( args.prefix, directory, not args.noSubDirs,
										preventRedundantLists, ignorePythonErrors )
		elif os.path.isfile( directory ):
			results	= open( directory, encoding = args.inputEncoding ).read().split( "\n" )
		else:
			raise FileNotFoundError( "Directory \"{}\" does not exist!".format( directory ) )
	if results:
		if args.outputSnippet:
			try:
				outputSnippet	= compile( args.outputSnippet, "outputSnippet", "exec" )
				l				= {	"filePath"	: None,
									"curDir"	: os.getcwd(),
									"dryMode"	: args.dryMode,
									"utils"		: makeList.getUtils(),
									"skipEntry"	: False,
								  }
				g				= makeList.getGlobals()
				outputEntries	= copy.copy( results )
				skippedEntries	= 0
				for num, f in enumerate( results ):
					l[ "filePath"]		= f
					l[ "skipEntry" ]	= False
					try:
						if verboseVerbose:
							print( "Executing python snippet for file \"{}\".".format( f ) )
						exec( outputSnippet, g, l )
						if "outputEntry" in l:
							outputEntries[ num - skippedEntries ] = l[ "outputEntry" ]
						if l[ "skipEntry" ]:
							del outputEntries[ num - skippedEntries ]
							skippedEntries	+= 1
					except Exception as exc:
						if not ignorePythonErrors:
							raise
						if not isinstance( exc, MLException ):
							traceback.print_tb( exc.__traceback__, None, None )
						sys.stderr.write( "Entry \"{}\" ignored. Reason: {}\n".format( f, exc ) )
				results	= outputEntries
			except Exception as exc:
				if not ignorePythonErrors:
					raise
				traceback.print_tb( exc.__traceback__, None, None )
				sys.stderr.write( "Error while evaluating entries using outputSnippet. Behaviour undefined! Reason: {}\n".format( exc ) )
		if output:
			if output == "-" or output == True:
				print( "\n".join( results ) )
			else:
				if not args.dryMode:
					if verbose:
						print( "Write final output file \"{}\".".format( output ) )
					fh = codecs.open( output, "w+", args.encoding if args.encoding is not None else locale.getencoding() )
					fh.write( "\n".join( results ) )
				elif verbose:
					sys.stderr.write( "Writing file \"{}\" skipped due to dry mode.\n".format( output ) )
sys.exit( 0 )
