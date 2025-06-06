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
extensionsMusic			= ".wma,.mpa,.wav,.mp3,.m4a,.mp4,.mov,.mkv,.avi,.mpg,.mpeg,.wma,.wav,.ogg,.wmv,.flac,.au,.mpg,.mpeg,.mkv,.wmv,.webm,.mts,.vob"
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
class MakeList:

	#######################################################################################################################
	def __init__( self, listsFolder, extensions, ignore, excludedDirectories, outputMode, fmtOnlyEntries, fmtAllSubEntries,
				  fmtLists, fmt, fmtEntry, snippet, writeEmptyLists, outputType, dryMode, outputEncoding,
				  verbose, verboseVerbose ):
		if listsFolder is None and fmtLists:
			raise Exception( "If option /fmtLists/ is specified, you need to specify a lists folder!" )
		self.__listsFolder			= os.path.abspath( os.path.normpath( listsFolder ) ) if listsFolder else None
		self.__outputType			= outputType
		self.__snippet				= snippet				# Python snippet to filter elements
		self.__dryMode				= dryMode
		self.__verbose				= verbose
		self.__verboseVerbose		= verboseVerbose
		self.__writeEmptyLists		= writeEmptyLists		# True: Do not write empty lists, just remove existing lists
		self.__excludedDirectories	= excludedDirectories	# folders within /listsFolder/ to be excluded

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
			#defFmtEntry					= "file:///{0}"
			defFmt						= "#EXTM3U\n{0}"
		else:
			raise Exception( "Unsupported output type \"{}\" specified!".format( outputType ) )


		self.__outputEncoding		= outputEncoding if outputEncoding is not None else defOutputEncoding
		self.__listExtension		= defListExtension

		# extensions:	Extensions to be added to the list. All other extensions are ignored. 
		if extensions is not None:
			self.__extensions		= { _.strip().lower() for _ in extensions.split( "," ) } \
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
				raise Exception( "Unsupported output mode option \"{}\" specified!".format( outputMode ) )

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
			sys.stderr.write( "File \"{}\" has an unsupported file extension! Ignored.\n".format( os.path.join( os.getcwd(), d, f ) ) )
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
			allItems	= [ _ for _ in sorted( os.listdir( dReal ), key = humanSortIgnoreKey ) ]
			subDirs		= [ _ for _ in allItems if os.path.isdir( os.path.join( dReal, _ ) ) ]
			files		= [ _ for _ in allItems if _ not in subDirs and ( _ in extensions or os.path.splitext(_)[ 1 ].lower() in extensions or self.__warnExtension( d, _ ) ) ]		\
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
	@staticmethod
	def getGlobals():
		return  {	"os"		: os,
					"sys"		: sys,
					"re"		: re,
					"sys"		: sys,
					"glob"		: glob,
					"shutil"	: shutil,
					"fnmatch"	: fnmatch,
					"traceback"	: traceback,
				}

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
					l		= {	"filePath"		: None,
								"curDir"		: dReal		}
					g		= self.getGlobals()
					def checkSnippet( f ):
						l[ "filePath" ]	= f
						try:
							if self.__verboseVerbose:
								print( "Check include filter by python snippet for file \"{}\".".format( f ) )
							return eval( snippet, g, l )
						except Exception as exc:
							if not ignorePythonErrors:
								raise
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
Create lists of folder "e:\\music" and all its sub folders and write all
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
Copy all selected files (filePath contains "* Bach*") to the folder "c:\data\temp\list" using
an custom Python snippet.
makeList.py -a -o="" -d="e:\music\Jazz" --filterSnippet="fnmatch.fnmatch( filePath, '* Bach*')" --os="shutil.copyfile( filePath, 'c:\\data\\temp\\list\\' + os.path.basename( filePath ) )" -v

###########################################################################################################################
Copy all selected movies with partial parts "*\\HT0*" to the existing folder "c:\data\temp\list"
using a custom Python snippet.
makeList.py -a -o="" -t=movies -d="e:\gfx\Ausflüge" --filterSnippet="fnmatch.fnmatch( filePath, '*\\*HT0*')" --os="shutil.copyfile( filePath, 'c:\\data\\temp\\list\\' + os.path.basename( filePath ) )" -v -D

###########################################################################################################################
Remove all list files of types (.sld, .m3u, .m3u8) within folder %GFX% but not in sub folder "_Playlisten_".
Consider activated dry mode!
makeList.py -a -o="" -d=%GFX% -e=".sld,.lst,.m3u,.m3u8" -x=_Playlisten_ --vv -v --outputSnippet="sys.stdout.write('Skipping removal of \"{}\" due to activated dry mode.\n'.format(filePath)) if dryMode else (sys.stdout.write('Removing \"{}\".\n'.format(filePath)) and os.remove(filePath))" -D
"""

###########################################################################################################################
# Main
parser = argparse.ArgumentParser( prog = "Make a file list", description = "Scan specified folders and their sub folders for files and write the list line-by-line to a file (.lst). Existing lists will be overwritten." )
parser.add_argument( "-v", "--verbose", action = "store_true", help = "Enable verbose mode." )
parser.add_argument( "--vv", "--verboseVerbose", dest = "verboseVerbose", action = "store_true", help = "Enable very verbose mode." )
parser.add_argument( "--ex", "--examples", dest = "examples", action = "store_true", help = "Show some examples how to use this script." )

gInput = parser.add_argument_group( "Input options" )
gInput.add_argument( "-d", "--directory", dest = "directories", help = "Start directory to be scanned. Option may be multiple defined. Default: \"\"", action = "append", default = None )
gInput.add_argument( "-x", "--excludeDirectory", dest = "excludedDirectories", help = "Directory to be excluded from scanning. Path must be relative to --directory. Option may be multiple defined. Default: \"\"", action = "append", default = None )
gInput.add_argument( "-e", "--extensions", help = "List of supported extensions as comma-separated string which will be part of the output list. Set to \"\" to add all files. Default: Default extensions of output type", default = None )
gInput.add_argument( "-i", "--ignore", help = "List of extensions to be ignored while scanning. All other extensions will raise a warning to STDOUT. Set to \"\" to skip this feature. Default: Default ignores of output type", default = None )
gInput.add_argument( "-N", "--noSubDirs", action = "store_true", help = "Do not scan sub directories." )

gOutput = parser.add_argument_group( "Output options" )
gOutput.add_argument( "-t", "--type", dest = "outputType", help = "Type of output lists. Valid options are: fileList, pictures, movies, m3u, m3uExt. Default: None", default = None )
gOutput.add_argument( "-m", "--mode", dest = "outputMode", help = "Output Mode of directory separators. Options are: None: Native separator, UNIX: Output list with \"/\" separator, Windows: Output list with \"\\\" separator. Default: Default output mode of output type", default = None )
gOutput.add_argument( "-l", "--listsFolder", help = "A folder any list shall also be written to. All path and drive separators shall be converted to \"_\". Default: Disabled", default = None )
gOutput.add_argument( "-s", "--filterSnippet", help = "Python snippet (type eval) to be customized while scanning to check, if an entry should be included or not. The following globals are defined: os, re, sys, glob, math, shutil, fnmatch, traceback. The following locals are defined: filePath, curDir. Default: Disabled", default = None )
gOutput.add_argument( "-p", "--prefix", help = "A prefix which shall be added to any element in the lists written to the lists folder (--listsFolder). This can be used to replace e.g. \"..\" to a place holder, e.g. $MYMUSIC. Default: Auto detected relative path from lists folder (--listsFolder) to folder to be scanned (see option --directory).", default = None )
gOutput.add_argument( "-E", "--encoding", help = "The encoding to be used in output lists. Default: {}".format( locale.getencoding() ), default = None )
gOutput.add_argument( "-W", "--writeEmptyLists", action = "store_true", help = "Do write empty lists. Default: Overwrite any list and write even empty content." )
gOutput.add_argument( "-D", "--dryMode", action = "store_true", help = "Dry mode. No changes will be done to disc. Default: False.", default = False )
gOutput.add_argument( "-o", "--output", help = "Output final list to specified file. Set to \"-\" to print to STDOUT. Set to \"\" to prevent printing to STDOUT. Default: STDOUT if outputType and --fmt* are not specified. Otherwise: None", default = None )
gOutput.add_argument( "-a", "--absPath", dest = "absPath", action = "store_true", help = "Create absolute path of entries in final outputs. Option has no effect to fmt lists. Default: False.", default = False )
gOutput.add_argument( "--os", "--outputSnippet", dest = "outputSnippet", help = "Python snippet (type: exec) executed for any final entry of output list in any case and independently on other options for any final line. The following globals are defined: os, re, sys, glob, math, shutil, fnmatch, traceback. The following locals are defined: filePath, curDir, dryMode. Default: Undefined.", default = None )
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
			raise Exception( "Specifiy either --fmtTemplate or --fmt!" )
		fmt			= open( fmtTemplate ).read()

	makeList	= MakeList( args.listsFolder, args.extensions if args.extensions is not None else None,
							args.ignore if args.ignore is not None else None, args.excludedDirectories,
							args.outputMode, args.fmtOnlyEntries, args.fmtAllSubEntries, args.fmtLists,
							fmt, fmtEntry, args.filterSnippet, args.writeEmptyLists, args.outputType,
							args.dryMode, args.encoding, verbose or verboseVerbose, verboseVerbose )
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

	for directory in args.directories if args.directories is not None else ( "", ):
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
	if results:
		if args.outputSnippet:
			try:
				outputSnippet	= compile( args.outputSnippet, "outputSnippet", "exec" )
				l				= {	"filePath"	: None,
									"curDir"	: os.getcwd(),
									"dryMode"	: args.dryMode,
								  }
				g				= MakeList.getGlobals()
				for f in results:
					l[ "filePath"]	= f
					try:
						if verboseVerbose:
							print( "Executing python snippet for file \"{}\".".format( f ) )
						exec( outputSnippet, g, l )
					except:
						if not ignorePythonErrors:
							raise
						traceback.print_tb( exc.__traceback__, None, None )
						sys.stderr.write( "Entry \"{}\" ignored.\n".format( f ) )
			except:
				if not ignorePythonErrors:
					raise
				traceback.print_tb( exc.__traceback__, None, None )
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
