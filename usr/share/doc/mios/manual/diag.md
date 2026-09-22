<!-- AI-hint: Manual pages distilled from the source comments of diag, sanitized, each passage anchored to the comment it came from. -->

# diag

### coredump_sanitizer.py — T-751 WS-DIAG Sanitized...

coredump_sanitizer.py — T-751 WS-DIAG
Sanitized systemd-coredump configurator and automated minidump extractor.

Extracts demangled stack minidumps into PostgreSQL bug_tracker, strips MADV_DONTDUMP
secret memory, and immediately purges raw core files.

<!-- mios-src:42ed9e28a76f from usr/libexec/mios/diag/coredump_sanitizer.py:4-10 -->
