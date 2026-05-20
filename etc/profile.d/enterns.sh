SYSDPID=`ps -eo cmd,pid | grep -m 1 ^/lib/systemd/systemd | awk '{print $2}'`
if [ ! -z "$SYSDPID" ] && [ "$SYSDPID" != "1" ]; then
    cat /etc/wslmotd
	/usr/local/bin/enterns
fi
