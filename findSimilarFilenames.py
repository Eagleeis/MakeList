###########################################################################################################################
# Brief : Find similar files in sub folders and lists by checking the similarity of
#         file namesthe 
# Author: Jan Blumenthal (eagleeis@gmx.de)
# Usage :	cmd.exe
#			c:\Tools\Python\PythonShell.bat
#			py evalGlobList.py -h
# Example:
#  py findSimilarFilenames.py -e=Hans -e=Hansi --listEncoding="utf-16-be=movies1new_utf16be.txt" --id --ie --sc
###########################################################################################################################

import argparse
import difflib
import pathlib
import os
import sys
import codecs


###########################################################################################################################
# Main
parser = argparse.ArgumentParser( prog = "Find similar files", description = "Find similar files based on difflib." )
parser.add_argument( "-v", "--verbose", action = "store_true", help = "Enable verbose mode." )
parser.add_argument( "--ex", "--examples", dest = "examples", action = "store_true", help = "Show some examples how to use this script." )

gInput = parser.add_argument_group( "Collecting entries to be checked" )
gInput.add_argument( "-e", "--entry", dest = "entries", help = "Path to an single entry. Option can be multiple defined.", action = "append", default = [] )
gInput.add_argument( "-g", "--glob", dest = "globs", help = "Glob pattern to be used for scanning (fnmatch.fnmatch). Option can be multiple defined.", action = "append", default = [] )
gInput.add_argument( "-r", "--list", dest = "lists", help = "Path to a list holding files names. Option can be multiple defined.", action = "append", default = [] )
gInput.add_argument( "--re", "--listEncoding", dest = "listsEncoding", help = "Path to a list holding files names. The encoding to be used is defined in a suffix, e.g. \"utf-16-be=myList.txt\". Option can be multiple defined.", action = "append", default = [] )

vOptions = parser.add_argument_group( "Evaluation options" )
#gOutput.add_argument( "-o", "--output", help = "Path to output path. Default: Disabled", default = None )
vOptions.add_argument( "-c", "--cutOff", type = float, help = "Cut off factor. Smaller values result in more similarily matches. Default: %(default)s)", default = 0.8 )
vOptions.add_argument( "--ka", "--keyAction", dest = "keyActions", help = "Specify the key actions separated by \",\". Available options are: ignoreExt (Ignore extensions), baseName (Ignore directories in path of entry), withoutNumber (Ignores all numbers in remaining name). Default: %(default)s)", default = "ignoreExt,baseName,withoutNumbers" )
vOptions.add_argument( "--id", "--ignoreDirectories", dest = "ignoreDirectories", action = "store_true", help = "Ignore directories in entries." )
vOptions.add_argument( "--ie", "--ignoreNoExtension", dest = "ignoreNoExtension", action = "store_true", help = "Ignore all entries without extensions or starting with \".\"." )
vOptions.add_argument( "--sc", "--skipCircularLoops", dest = "skipCircularLoops", action = "store_true", help = "Skip matches which were already raised in opposite direction" )

args	= parser.parse_args()
verbose	= args.verbose

if args.examples:
	print( """Some examples how to use this script:
""" )
else:
	excludes			= []					# TBD
	keyActions			= args.keyActions
	ignoreDirectories	= args.ignoreDirectories
	ignoreNoExtension	= args.ignoreNoExtension
	skipCircularLoops	= args.skipCircularLoops
	entries				= args.entries

	for g in args.globs:
		baseDir		= pathlib.Path( "." )
		entries		+= baseDir.rglob( g )

	for l in args.lists:
		entries		+= [ _ for _ in codecs.open( l, "r" ).read().split( "\r\n" ) if not _.startswith( "#" ) and _.strip() ]

	for l in args.listsEncoding:
		e, p	= l.split( "=", 1 )
		print( e, p )
		entries		+= [ _ for _ in codecs.open( p, "r", e ).read().split( "\r\n" ) if not _.startswith( "#" ) and _.strip() ]

	if ignoreDirectories:
		def noDir( e ):
			return not e.endswith( "\\" ) and not e.endswith( "/" ) and ( not os.path.exists( e ) or os.path.isfile( e ) )
		entries	= [ _ for _ in entries if noDir( _ ) ]

	if ignoreNoExtension:
		def noExtension( e ):
			try:
				bn, ext	= e.split( ".", 1 )
				return not not bn			# exclude ".git" etc. 
			except:
				return False
		entries	= [ _ for _ in entries if noExtension( _ ) ]

	#print( "\n".join( entries ) )


	def processActionBasename( entry ):
		return os.path.basename( entry )
	def processActionIgnoreExt( entry ):
		return os.path.splitext( entry )[ 0 ]
	def processActionWithOutNumbers( entry ):
		return ''.join( i for i in entry if not i.isdigit() )

	def keyActionFunctions( keyActions ):
		actions = []
		for action in keyActions.split( "," ):
			action	= action.strip()
			if "ignoreExt" == action:
				actions.append( processActionIgnoreExt )
			elif "baseName" == action:
				actions.append( processActionBasename )
			elif "withoutNumbers" == action:
				actions.append( processActionWithOutNumbers )
			else:
				raise Exception( "Unsupported action \"{}\".".format( action ) )
		return actions

	def processKeyFunctions( kaf, s ):
		basename	= os.path.basename( s )
		for action in kaf:
			s		= action( s )
		return basename, s

	kaf			= keyActionFunctions( keyActions )
	filePaths	= { str( _ ) : processKeyFunctions( kaf, _ ) for _ in entries }
	fileInfos	= [ ( _, filePaths[ _ ][ 0 ] ) for _ in filePaths ]		# Make list of file names created by functions createKey()
	fileNameKeys= [ filePaths[ _ ][ 1 ] for _ in filePaths ]		# Make list of file name keys created by functions createKey()

	#print( "filePathsfilePaths", filePaths)
	matches		= {}
	numMatches	= 0
	for index, fileInfo in enumerate( fileInfos ):
		filePath, fileName	= fileInfo
		fileNameKey	= fileNameKeys[ index ]
		cm = difflib.get_close_matches( fileNameKey, fileNameKeys, n = 5, cutoff = args.cutOff )
		if cm:
			cmPaths		= [ _ for _ in filePaths if filePaths[ _ ][ 1 ] in cm and fileName != filePaths[ _ ][ 0 ] ]
			if skipCircularLoops and cmPaths:
				retry	= True
				while retry:
					retry = False
					for cm in cmPaths:
						if cm in matches and filePath in matches[ cm ]:
							cmPaths	= [ _ for _ in cmPaths if _ != cm ]
							retry	= True
							break
				matches[ filePath ]	= cmPaths
			if cmPaths:
				numMatches	+= len( cmPaths )
				cmStr	= "\n    ".join( cmPaths )
				print( "{}:\n    {}".format( filePath, cmStr ) )

	print( "{} matches.".format( numMatches ) )
