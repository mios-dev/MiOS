# tools/lib/install-env.ps1 -- shared helper for the 'MiOS' Windows installers.
# Writes /etc/mios/install.env into a freshly-imported WSL2 distro so that
# /usr/libexec/mios/wsl-firstboot can pick up the operator-supplied hostname
# and password hash on first boot, instead of falling back to the literal
# default password "mios".
#
# Resolution chain documented in /usr/share/mios/env.defaults:
#   ~/.config/mios/env -> /etc/mios/install.env -> /etc/mios/env.d/*.env -> /usr/share/mios/env.defaults
# This file produces the third layer.

function Write-MiosInstallEnv {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$WslDistro,
        [Parameter(Mandatory)][string]$User,
        [Parameter(Mandatory)][string]$PasswordHash,
        [Parameter(Mandatory)][string]$Hostname,
        [string]$ForgeAdminUser  = "",
        [string]$ForgeAdminEmail = ""
    )

    # The hash MUST be sha512crypt ($6$salt$digest). Anything else is a bug
    # upstream in the build script -- refuse rather than ship a broken
    # install.env that wsl-firstboot would silently reject.
    if ($PasswordHash -notmatch '^\$6\$') {
        $preview = if ($PasswordHash.Length -ge 8) { $PasswordHash.Substring(0,8) } else { $PasswordHash }
        Write-Warning "Refusing to write install.env: PasswordHash is not sha512crypt (got prefix '$preview...')"
        return $false
    }

    # Default the forge admin to the linux user identity if not supplied.
    if (-not $ForgeAdminUser)  { $ForgeAdminUser  = $User }
    if (-not $ForgeAdminEmail) { $ForgeAdminEmail = "$User@$Hostname.local" }

    # Single-quote the hash because $6$... contains literal $-sigils that
    # bash would otherwise treat as parameter expansion when the env file
    # is sourced. sha512crypt charset is [A-Za-z0-9./$] -- no single quotes
    # ever appear in the hash, so the wrap is safe.
    $lines = @(
        "# /etc/mios/install.env -- written by the 'MiOS' Windows installer.",
        "# Read by /usr/libexec/mios/wsl-firstboot, /usr/libexec/mios/mios-dashboard.sh,",
        "# and /usr/libexec/mios/forge-firstboot.sh.",
        "# Vendor defaults: /usr/share/mios/env.defaults",
        "MIOS_USER=$User",
        "MIOS_USER_PASSWORD_HASH='$PasswordHash'",
        "MIOS_HOSTNAME=$Hostname",
        "MIOS_FORGE_ADMIN_USER=$ForgeAdminUser",
        "MIOS_FORGE_ADMIN_EMAIL=$ForgeAdminEmail",
        "MIOS_FORGE_ADMIN_PASSWORD="
    )
    $body = ($lines -join "`n") + "`n"

    # Pipe to root sh inside the new distro. umask 077 keeps the file 0600
    # from the moment it lands on disk -- the hash is a credential.
    $body | & wsl.exe -d $WslDistro -u root sh -c 'umask 077 && mkdir -p /etc/mios && cat > /etc/mios/install.env'
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Failed to write /etc/mios/install.env into '$WslDistro' (wsl exit $LASTEXITCODE)"
        return $false
    }

    # Also clear the firstboot sentinel so wsl-firstboot.service runs against
    # the env we just wrote, even if the image was previously seeded.
    & wsl.exe -d $WslDistro -u root sh -c 'rm -f /var/lib/mios/.wsl-firstboot-done' | Out-Null

    return $true
}
