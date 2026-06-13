# AI-hint: Configures environment variables and provides the mingw64-env alias to initialize the MinGW-w64 cross-compilation toolchain environment for Windows development.
# Environment variables for cross compilers.

alias mingw64-env='eval `rpm --eval %{mingw64_env}`'
