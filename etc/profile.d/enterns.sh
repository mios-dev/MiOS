# AI-hint: Shell script that detects the systemd PID to determine if running in a native environment versus WSL, executing the /enterns utility and displaying the motd if a non-standard systemd PID is detected.
SYSDPID=`ps -eo cmd,pid | grep -m 1 ^/lib/systemd/systemd | awk '{print $2}'`
if [ ! -z "$SYSDPID" ] && [ "$SYSDPID" != "1" ]; then
    cat /etc/wslmotd
	/usr/local/bin/enterns
fi
