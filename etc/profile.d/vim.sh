# AI-hint: Configures the shell environment by aliasing vi to vim and ensuring consistent editor behavior across bash, ksh, and zsh shells when the binaries are located in standard system paths.
if [ -n "${BASH_VERSION-}" -o -n "${KSH_VERSION-}" -o -n "${ZSH_VERSION-}" ]; then
  case "$(command -v vim)-$(command -v vi)" in
    /usr/bin/vim-/usr/bin/vi)
        alias vi=vim
        ;;
  esac
fi
