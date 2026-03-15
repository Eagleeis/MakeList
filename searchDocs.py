###########################################################################################################################
# fgrep "Handbook of" -i windows.txt > /tmp/searchResults.txt
# /cygdrive/c/Tools/Notepad++/notepad++.exe "C:\cygwin64\tmp\searchResults.txt"
#
# Example:
#	python.exe searchDocs.py "Handbook of"
# Total Commander:
#	Kommando:	e:\work\Programmierung\Python39\python.exe C:\Tools\SearchDocs\searchDocs.py
#	Parameter:	[list]
###########################################################################################################################

import sys
import os
import re
import html
import codecs
import subprocess

# Default settings

# ESUS (cygwin)
#listFile		= "windows.txt"
#searchResults	= "/tmp/searchResults.txt"
#htmlResults	= "/cygdrive/c/Data/temp/searchResults.html"
#grepPath		= "/bin/fgrep"
#docsDir		= os.path.abspath( os.path.dirname( os.path.normpath( sys.argv[ 0 ] ) ) )

# ESUS (Windows native, Python: c:\Tools\Python\3.10\python.exe)
#listFile		= r'c:\Tools\SearchDocs\Docs_Windows.txt'
#searchResults	= r'c:\Tools\SearchDocs\searchResults.txt'
#htmlResults	= r'c:\Tools\SearchDocs\searchResults.html'
#grepPath		= r'"c:\Program Files\Git\usr\bin\grep.exe"'
#docsDir		= r'm:/Movies_2/docs'

# ES (Windows native, Python: e:\work\Programmierung\Python39\python.exe)
defListFile		= r'e:\listen\Docs_Windows.txt'				# if not specified by command line args
defListFilesDir	= r'e:\listen'
defExcludes		= [ "readme.txt" ]
searchResults	= r'c:\Tools\SearchDocs\searchResults.txt'
htmlResults		= r'c:\Tools\SearchDocs\searchResults.html'
grepPath		= r'c:\Tools\git\usr\bin\grep.exe'
docsDir			= r'm:/Movies_2/docs'

encoding		= "utf-8"
#encoding		= "cp1252"
#encoding		= "cp850"
excludeExt		= ( ".~", ".abt", ".class", ".bmp", ".cat", ".cue", ".css", ".dbz", ".dmg", ".fit", ".lib", ".did", ".gif", ".jpg", ".ddd", ".plc", ".pdd", ".mid", ".png", ".primary", ".stp", ".trn", ".exe", ".dll", ".pyc", ".o", ".obj", ".rda", ".a", ".out", ".wld", ".pdx", ".wd3" )


def checkChar( c ):
	if c == "\"":
		return "&quot;"
	elif c == "'":
		return "&amb;"
	elif c == "<":
		return "&lt;"
	elif c == ">":
		return "&gt;"
	else:
		n	= ord( c )
		if n < 128:
			return c
		else:
			return "&#{};".format( ord( c ) )

def convertStr( s ):
	return "".join( [ checkChar( _ ) for _ in s ] )

#mimeTypes	= {
#	".xls"	: "application/msexcel",
#	".xlsX"	: "application/msexcel",
#	".pdf"	: "application/pdf",
##	".m3u"	: "audio/x-mpegurl",
#	".mp3"	: "music/mp3",
#	".mpg"	: "video/mpg",
#	".mpeg"	: "video/mpeg",
#	".avi"	: "video/avi",
#	".mp4"	: "video/mp4",
#	#".mkv"	: "application/x-vlc-plugin",
#	#".mkv"	: "video/x-matroska",
#	".mkv"	: "video/x-mpegurl",
#	".mov"	: "video/quicktime",
#}

# Use Firefox !!!
mimeTypes	= {
	".xls"	: "application/msexcel",
	".xlsx"	: "application/msexcel",
	".pdf"	: "application/pdf",
	".m3u"	: "audio/x-mpegurl",
	".mp3"	: "audio/x-mpegurl",
	".ogg"	: "audio/x-mpegurl",
	".flac"	: "audio/x-mpegurl",
	".wav"	: "audio/x-mpegurl",
	".mpg"	: "video/x-mpegurl",
	".mpeg"	: "video/x-mpegurl",
	".avi"	: "video/x-mpegurl",
	".mp4"	: "video/x-mpegurl",
	".mkv"	: "video/x-mpegurl",
	".mov"	: "video/x-mpegurl",
}



# Find search results
def scanOneFile( oh, listFile, searchPattern, baseDir ):
	global grepPath
	cmd				= "{} \"{}\" -i \"{}\" > {}".format( grepPath, searchPattern, listFile, searchResults )
	print( "Looking for \"{}\" in file \"{}\".".format( searchPattern, os.path.abspath( listFile ) ) )
	print( "Executing: {}".format( cmd ) )
	subprocess.call( cmd, shell = True )

	# Prepare writing of html list
	if baseDir and baseDir.startswith( "/cygdrive/" ):
		drive, remain	= baseDir[ 10: ].split( "/", 1 )
		baseDir			= drive + ":/" + remain

	# Traverse through search results
	for numLine, line in enumerate( codecs.open( searchResults, encoding = encoding ) ):
		line	= line.rstrip()
		_, ext	= os.path.splitext( line )
		ext		= ext.lower()
		if ext in excludeExt:
			sys.stderr.write( "Ignoring {}\n".format( line ) )
		else:
			eLine	= convertStr( line )
			if ext in mimeTypes:
				mimeType	= " type=\"{}\"".format( mimeTypes[ ext ] )
			else:
				mimeType	= ""
			if baseDir:
				oh.write( "<a href=\"file:///{0}/{1}\"{2}>{1}</a></br>\n".format( baseDir, eLine, mimeType ) )
			else:
				oh.write( "<a href=\"file:///{0}\"{1}>{0}</a></br>\n".format( eLine, mimeType ) )


############################################## Main ############################################
#listFiles		= [ r'e:\listen\Docs_Windows.txt', r'e:\listen\MY006_Fritzbox_movies2.txt' ]
#searchPattern	= 'choll'
#baseDir			= None

if len( sys.argv ) > 1:
	listFiles	= [ sys.argv[ 1 ] ]
	baseDir		= docsDir
else:
	#def sortkey( value ):
	#	return [ lower( value ) ]
	def keyHumanSortIgnoreCase( value ):
		return [ ( int( v ) if v.isdigit() else v.lower() ) for v in re.split( "([0-9]+)", value ) ]

	availFiles	= [ os.path.join( defListFilesDir, _ ) for _ in sorted( os.listdir( defListFilesDir ), key = keyHumanSortIgnoreCase ) if os.path.isfile( os.path.join( defListFilesDir, _ ) ) and _ not in defExcludes ]
	numAvail	= len( availFiles )
	width		= 2 if numAvail > 9 else 1
	fmt			= "{{0:-{}d}} : {{1}}".format( width )
	baseDir		= None
	while True:
		print( "Please select lists(s) by space- or comma-separated numbers" )
		print( "\n".join( [ fmt.format( _, availFiles[ _ ] ) for _ in range( 0, len( availFiles ) ) ] ) )
		l			= input( "Please enter number of list or just enter for all lists: " ).replace( ",", " " )
		if not l.strip():
			listFiles	= availFiles
			print( "Searching in all lists selected." )
			break
		selLists	= [ _.strip() for _ in l.split( " " ) if _.strip() != "" ]
		listFiles	= []
		for selList in selLists:
			try:
				num		= int( selList )
			except:
				sys.stderr.write( "Please specified a valid number instead \"{}\"!\n\n".format( selList ) )
				break
			if num < 0 and num > numAvail:
				sys.stderr.write( "Invalid number \"{}\" specified!\n\n".format( num ) )
				break
			elif availFiles[ num ] not in listFiles:
				listFiles.append( availFiles[ num ] )
		else:
			break

while True:
	searchPattern	= input( "Please enter grep search pattern: " )
	if searchPattern.strip():
		break
	sys.stderr.write( "Please specify a valid search pattern!\n\n" )



oh	= codecs.open( htmlResults, "w", encoding = encoding )
if baseDir:
	oh.write( """<?xml version=\"1.0\" encoding=\"utf-8\">
	<body>
	<p>Browse <a href="file:///{0}">docs</a> by directory.</p>
	<p>Search results of &quot;{1}&quot;</p>

	""".format( baseDir, searchPattern ) )
else:
	oh.write( """<?xml version=\"1.0\" encoding=\"utf-8\">
	<body>
	<p>Search results of &quot;{0}&quot;</p>

	""".format( searchPattern ) )


for listFile in listFiles:
	scanOneFile( oh, listFile, searchPattern, baseDir if listFile != defListFile else docsDir )

oh.write( "</body>\n" )
oh.close()

# Open browser with search results
if htmlResults.startswith( "/cygdrive/" ):
	drive, remain	= htmlResults[ 10: ].split( "/", 1 )
	htmlResultsWin	= "{}:\{}".format( drive, remain.replace( "/", "\\" ) )
else:
	htmlResultsWin	= htmlResults
print( "HTML Results written to \"{}\" or \"{}\".".format( htmlResults, htmlResultsWin ) )
cmd	= "cmd.exe /C \"{}\"".format( htmlResultsWin )
subprocess.call( cmd, shell = True )
