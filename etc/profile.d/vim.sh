# AI-hint: Configures the shell environment by aliasing vi to vim and ensuring consistent editor behavior across bash, ksh, and zsh shells when the binaries are located in standard system paths.
if [ -n "${BASH_VERSION-}" -o -n "${KSH_VERSION-}" -o -n "${ZSH_VERSION-}" ]; then
  # This will avoid user defined aliases and possibly stuff defined earlier in the PATH.
  case "$(command -v vim)-$(command -v vi)" in
    /usr/bin/vim-/usr/bin/vi)
        # apply only when founded vim and vi are in expected dirs from distro
        alias vi=vim
        ;;
  esac
fi
