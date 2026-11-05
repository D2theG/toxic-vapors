#!/usr/bin/env bash
# Run manually as ubuntu ON THE NEW SENSOR after bootstrap. Downloads only;
# does not run an installer, configure authentication, start services or forward logs.
set -euo pipefail
umask 077
release=26.10.0
archive="malcolm-$release-docker_install.zip"
workdir="$HOME/malcolm-installer-$release"
if [ -e "$workdir" ]; then echo "Refusing to overwrite $workdir" >&2; exit 1; fi
mkdir -m 0700 "$workdir"
cd "$workdir"
curl --fail --location --proto '=https' --tlsv1.2 --output "$archive" \
  "https://github.com/cisagov/Malcolm/releases/download/v$release/$archive"
printf '%s  %s\n' '59d951838209d17c1b5c60abbb39d581fdf6a6215bb32fdc006ff7ba5a429cb7' "$archive" | sha256sum --check -
unzip "$archive"
echo "Verified installer extracted to $workdir. Follow README operator configuration steps."
