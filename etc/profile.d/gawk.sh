# AI-hint: Provides shell functions to initialize, prepend, or append paths to AWK environment variables (AWKPATH and AWKLIBPATH) to ensure correct script execution and library linking.
# AI-functions: gawkpath_default, gawkpath_prepend, gawkpath_append, gawklibpath_default, gawklibpath_prepend, gawklibpath_append
gawkpath_default () {
	unset AWKPATH
	export AWKPATH=`gawk 'BEGIN {print ENVIRON["AWKPATH"]}'`
}

gawkpath_prepend () {
	[ -z "$AWKPATH" ] && AWKPATH=`gawk 'BEGIN {print ENVIRON["AWKPATH"]}'`
	export AWKPATH="$*:$AWKPATH"
}

gawkpath_append () {
	[ -z "$AWKPATH" ] && AWKPATH=`gawk 'BEGIN {print ENVIRON["AWKPATH"]}'`
	export AWKPATH="$AWKPATH:$*"
}

gawklibpath_default () {
	unset AWKLIBPATH
	export AWKLIBPATH=`gawk 'BEGIN {print ENVIRON["AWKLIBPATH"]}'`
}

gawklibpath_prepend () {
	[ -z "$AWKLIBPATH" ] && \
		AWKLIBPATH=`gawk 'BEGIN {print ENVIRON["AWKLIBPATH"]}'`
	export AWKLIBPATH="$*:$AWKLIBPATH"
}

gawklibpath_append () {
	[ -z "$AWKLIBPATH" ] && \
		AWKLIBPATH=`gawk 'BEGIN {print ENVIRON["AWKLIBPATH"]}'`
	export AWKLIBPATH="$AWKLIBPATH:$*"
}
