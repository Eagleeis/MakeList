###########################################################################################################################
# Brief : Scan specified folders and their sub folders for files and write
#         the list line-by-line to a file (.m3u). Existing files will be overwritten.
# Author: Jan Blumenthal (eagleeis@gmx.de)
# Usage :	cmd.exe
#			c:\Tools\Python\PythonShell.bat
#			py evalGlobList.py -h
###########################################################################################################################
import collections
import traceback
import argparse
import codecs
import fnmatch
import locale
import os
import ast
import re
import glob
import copy
import math
import cmath
import errno
import time
import sys


###########################################################################################################################
reSplit	= re.compile( r'(\d+)' )
def humanSortIgnoreKey( s ):
	return [ int( t ) if i & 1 else t.lower() for i, t in enumerate( reSplit.split( s ) ) ]

###########################################################################################################################
class EvalGlobList:

	#######################################################################################################################
	def __init__( self, refListsDefs, outputEncoding, dryMode, verbose ):
		self.__outputEncoding	= outputEncoding
		self.__dryMode			= dryMode
		self.__writeEmptyLists	= False
		self.__verbose			= verbose
		self.__verboseVerbose	= False
		if verbose:
			print( "\nThe following lists holding the references to be parsed will be processed:" )
		self.__refLists	= self.__readInputs( refListsDefs )[ 0 ]

	#######################################################################################################################
	# Read /inputs/ (may contain glob file pattern). Each resolved definition file may contain
	# regular expressions of type fnmatch.
	# Return:	[0]	All applicable regular expressions (fnmatch) read from applicable definition files
	#			[1] Name of last definition file (used for fmtOutput)
	#			[2]	Options (may be read from listFiles, last option wins)
	# The following options may be defined in a definition file
	#	#@sortMethod=humanSortIgnoreKey
	def __readInputs( self, inputs ):
		results 	= []
		options		= {}
		listFile	= None

		def checkComment( line ):
			# Return:	True	Line should be ignored since it is a comment
			if line.startswith( "#" ):
				if line.startswith( "#@sortMethod=" ):
					method	= line[ 13 : ].strip()
					if method == "humanSortIgnoreKey":
						options[ "sortMethod" ] = humanSortIgnoreKey
					else:
						raise Exception( "Invalid sort method \"{}\" specified!".format( method ) )
				#elif line.startswith( "#@excludePrefix=" ):
				#	excludePrefix = line[ 16 : ]
				#	options[ "excludePrefix" ] = excludePrefix
				elif line.startswith( "#@" ):
					raise Exception( "Unsupported option \"{}\" specified!".format( line ) )
				return False
			return True

		for inputPath in inputs:
			if os.path.exists:
				for listFile in ( inputPath, ) if os.path.isfile( inputPath ) else [ _ for _ in glob.glob( inputPath ) if os.path.isfile( _ ) ]:
					if self.__verbose:
						print( listFile )
					with open( listFile ) as fh:
						results.extend( [ ( _, listFile, lNum ) for lNum, _ in enumerate( fh.read().split( "\n" ) ) if not not _.strip() and checkComment( _ ) ] )

			else:
				raise Exception( "Input path \"{}\" does not exist!".format( inputPath ) )

		# Make iterable dict of entries and store source (path and line number)
		results	= { _1 : ( _2, _3 ) for _1, _2, _3 in results }
		return results, listFile, options

	#######################################################################################################################
	def __getOutput( self, fmt, lines ):
		#if self.__outputType == "m3u":
		#	return "\n".join( lines )
		#elif self.__outputType == "m3uExt":
		#	return "file:///" + "\nfile:///".join( lines )
		#else:
		#	raise Exception( "Unsupported output type \"{}\" found!".format( self.__outputType ) )
		if fmt is None:
			return "\n".join( lines )
		return fmt.format( "\n".join( lines ) )
	#######################################################################################################################
	def __writeList( self, listPath, fmt, lines ):
		listPath	= os.path.abspath( listPath )
		dirName		= os.path.dirname( listPath )

		if lines or self.__writeEmptyLists:
			if not os.path.exists( dirName ):
				if self.__verbose:
					print( "Creating new directory \"{}\".".format( dirName ) )
				if not self.__dryMode:
					os.mkdir( dirName )
			if self.__verbose:
				print( "Writing \"{}\" ({} {}).".format( listPath, len( lines ), ( "line" if len( lines ) == 1 else "lines" ) ) )
				if self.__verboseVerbose:
					print( self.__getOutput( fmt, lines ) )
		if os.path.exists( listPath ):
			try:
				if self.__verboseVerbose:
					print( "Removing existing file \"{}\".".format( listPath ) )
				if not self.__dryMode:
					os.remove( listPath )
			except:
				sys.stderr.write( "Cannot remove existing path \"{}\"! Ignored.\n".format( listPath ) )
		try:
			if not self.__dryMode and ( lines or self.__writeEmptyLists ):
				f = codecs.open( listPath, "w", self.__outputEncoding )
				try:
					f.write( self.__getOutput( fmt, lines ) )
				except UnicodeEncodeError as e:
					if fmt is None:
						# Most probably an encoding problem. Write line-by-line to ignore problematic line
						for numLine, line in enumerate( lines ):
							try:
								f.write( line + "\n" )
							except:
								sys.stderr.write( "Skipped file \"{}\". Reason: {}\n".format( line.encode( "ascii", "ignore" ), str( e ) ) )
					else:
						raise Exception( "Handling unicode errors is not supported, if fmt is not None" )
			elif self.__verbose:
				sys.stderr.write( "Skipping writing empty file \"{}\".\n".format( listPath ) )
		except:
			sys.stderr.write( traceback.format_exc() )
			sys.stderr.write( "Cannot write list to file \"{}\"!\n".format( listPath ) )

	#######################################################################################################################
	def __snippet( self, snippet, lines ):
		if self.__verbose:
			print( "Applying Python snippet \"{}\" to any pre-selected lines.\n".format( snippet ) )
		nLines	= []
		g		= {	"sys"			: sys,
					"ast"			: ast,
					"os"			: os,
					"re"			: re,
					"copy"			: copy,
					"math"			: math,
					"cmath"			: cmath,
					"errno"			: errno,
					"time"			: time,
					"glob"			: glob,
					"fnmatch"		: fnmatch,
					"collections"	: collections,
					"user"			: {}
				  }
		l		= {	"num"			: 0,
					"line"			: None,
					"len"			: len( lines ),
				  }
		for num, line in enumerate( lines ):
			l[ "num" ]	= num
			l[ "line" ]	= line
			r	= eval( snippet, g, l )
			if r != None:
				nLines.append( r )
		return nLines

	#######################################################################################################################

		
	#######################################################################################################################
	def parseGlobList( self, globListsDefs, snippet, outputPath, fmtOutputPath, fmt, fmtEntry ):
		if self.__verbose:
			print( "\nThe following lists with regular expressions will be processed:" )
		regExFNMatches, lastListFile, options	= self.__readInputs( globListsDefs )
		refLists		= self.__refLists
		lines			= []

#		excludePrefix	= options[ "excludePrefix" ] if options and "excludePrefix" in options else None
#		def checkIncludeExclude( f, regEx ):
#			return False
#			#return fnmatch.fnmatch( f, regEx )
#		def checkInclude( f, regEx ):
#			return fnmatch.fnmatch( f, regEx )
#		checkInclude	= checkIncludeExclude if excludePrefix is not None else checkInclude

		for regEx in regExFNMatches:						# traverse through all regular expressions (fnmatch)
			#lines += [ f for f in refLists if checkInclude( f, regEx ) ]
			lines += [ f for f in refLists if fnmatch.fnmatch( f, regEx ) ]
		if snippet:
			lines	= self.__snippet( snippet, lines )

		# sort entries
		if options and "sortMethod" in options:
			lines	= [ _ for _ in sorted( lines, key = options[ "sortMethod" ] ) ]

		if fmtEntry is not None:
			lines	= [ fmtEntry.format( _ ) for _ in lines ]
	
		baseName	= ""
		if outputPath is None:
			if lastListFile:
				listName		= os.path.basename( lastListFile )
				lastListDir		= os.path.normpath( os.path.join( lastListFile, ".." ) )
				baseName, ext	= os.path.splitext( listName )
				outputPath		= os.path.normpath( fmtOutputPath.format( listName, baseName, ext, lastListDir ) )
			else:
				raise Exception( "Invalid last list file determined!" )

		if self.__verbose:
			print( "" )
		print( "Writing output file \"{}\" with {} entries.".format( outputPath, len( lines ) ) )
		self.__writeList( outputPath, fmt, lines )

###########################################################################################################################
examples = r"""Here are some examples, how to use this script:

Function: Read list containing fnmatch regular expression (fnmatch) and write to specified output path.
evalGlobList.py -g=e:\gfx\_lists\_definitions_\Konzerte.txt -r=e:\gfx\_lists\movies\.m3u8 -o=movies_Konzerte.m3u8

Function: Same as before but change each line.
evalGlobList.py -g=e:\gfx\_lists\_definitions_\Konzerte.txt -r=e:\gfx\_lists\movies\.m3u8 -o=movies_Konzerte.m3u8 -s="line.replace(\"../../\",\"..\")"

Function: Evaluate each list in folder \"definitions\" and write one combined list to the output.
evalGlobList.py -g=e:\gfx\_lists\_definitions_\*.txt -r=e:\gfx\_lists\movies\.m3u8 -o=movies_HT_and_Konzerte.m3u8

"""

###########################################################################################################################
# Main
parser = argparse.ArgumentParser( prog = "Make a file list", description = "Scan specified folders and their sub folders for files and write the list line-by-line to a file (.m3u). Existing files will be overwritten." )
parser.add_argument( "-v", "--verbose", action = "store_true", help = "Enable verbose mode." )
parser.add_argument( "--ex", "--examples", dest = "examples", action = "store_true", help = "Show some examples how to use this script." )

gInput = parser.add_argument_group( "Input options" )
gInput.add_argument( "-g", "--globList", dest = "globLists", help = "File or directory containing the list of regular expressions (type fnmatch inside) to find matches. Glob regular expression can be used to select the definition files. Default: \"\"", action = "append", default = [] )
gInput.add_argument( "-r", "--refLists", dest = "refLists", help = "File or directory containing the lists to be checked against the inputs. Python regular expressions (fnmatch) are supported. Default: \"\"", action = "append", default = [] )
gInput.add_argument( "-p", "--processSeparately", action = "store_true", help = "Process input lists separately. Default: Write matchings to one output file." )


gEval = parser.add_argument_group( "Evaluation options" )
gEval.add_argument( "-s", "--snippet", help = "Python snippet processed for any entry after processing regular expression. Needs to return the final output of the entry. If None is returned, the entry shall be skipped. The following globals will be available: sys, ast, os, re, copy, math, cmath, errno, time, glob, fnmatch, collections. Further a global dictionary \"user\" will be provided to store data from one call to another. The following locals will be provided: num, line, len. Default: None", default = None )

gOutput = parser.add_argument_group( "Output options" )
gOutput.add_argument( "-o", "--output", help = "Path to output path. Default: Disabled", default = None )
gOutput.add_argument( "-f", "--fmtOutput", help = "Format template of the output paths ({0}: base name of last glob list, {1}:file name without extension, {2}:extension, {3}:directory of last glob list). Default: Disabled", default = None )
gOutput.add_argument( "--fmtTemplate", dest = "fmtTemplate", help = "Format template of main content read from specified file. ({0}: Formatted elements (see option --fmtEntry). Option cannot be specified together with --fmt! Default: \"{0}\"", default = None )
gOutput.add_argument( "--fmt", help = "Format template of main content ({0}: Formatted elements (see option --fmtEntry). Default: \"{0}\"", default = None )
gOutput.add_argument( "--fmtEntry", help = "Format template of a single entry ({0}: Path as read from source). Default: \"{0}\"", default = None )
gOutput.add_argument( "-E", "--outputEncoding", help = "The encoding to be used in output lists. Default: {}".format( locale.getencoding() ), default = None )
gOutput.add_argument( "-D", "--dryMode", action = "store_true", help = "Dry mode. No changes will be done to disc. Default: False.", default = False )

args	= parser.parse_args()
verbose	= args.verbose
if args.examples:
	print( examples.strip() )
else:
	globLists		= args.globLists
	snippet			= args.snippet
	fmt				= args.fmt
	fmtEntry		= args.fmtEntry
	fmtOutput		= args.fmtOutput
	fmtTemplate		= args.fmtTemplate
	output			= args.output
	evalGlobList	= EvalGlobList( args.refLists, args.outputEncoding, args.dryMode, verbose )
	if fmtTemplate:
		if fmt:
			raise Exception( "Specifiy either --fmtTemplate or --fmt!" )
		fmt			= open( fmtTemplate ).read()

	# False: All regExLists will be evaluated against all refLists at once and will be written to one final file.
	if args.processSeparately:
		for rGlobList in globLists:
			for globList in glob.glob( rGlobList ):
				evalGlobList.parseGlobList( [ globList ], snippet, output, fmtOutput, fmt, fmtEntry )
	else:
		evalGlobList.parseGlobList( globLists, snippet, output, fmtOutput, fmt, fmtEntry )

sys.exit( 0 )
