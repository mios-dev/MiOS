# AI-hint: Defines the mingw32-env alias and environment variables for cross-compiling for the MinGW32 architecture, used by agents to configure the build environment for Windows-targeted binaries.
# Environment variables for cross compilers.

alias mingw32-env='eval `rpm --eval %{mingw32_env}`'
