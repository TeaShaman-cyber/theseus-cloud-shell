#!/bin/sh
# Pin the tested release. Optional local archive allows offline reproduction.
set -eu
umask 077
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
test "$(uname -s)/$(uname -m)" = Linux/x86_64 || { echo 'Supported target: Linux x86_64' >&2; exit 1; }
asset=brain_0.13.2_linux_amd64.tar.gz
archive_sha=e7b4c3b3166b67fa4b3f1d52615d8fdc29e5d38f1f370df13890fe6208131ce1
binary_sha=8fecef7384ce66e2486f5562a38344f1cb7cbd1a736df6a7d57acd18f8d641cd
bin="$HOME/.local/bin/brain"
cfg="$HOME/.config/theseus/brain-nous.yaml"
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
test "$#" -le 1
if [ "$#" -eq 1 ]; then
    archive=$(realpath "$1")
else
    gh release download v0.13.2 -R icheer/brain-cli -p "$asset" -D "$tmp"
    archive="$tmp/$asset"
fi
printf '%s  %s\n' "$archive_sha" "$archive" | sha256sum -c -
tar -xOf "$archive" brain > "$tmp/brain"
printf '%s  %s\n' "$binary_sha" "$tmp/brain" | sha256sum -c -
chmod 755 "$tmp/brain"
test "$("$tmp/brain" --version)" = 'brain 0.13.2 (commit 377cc5e3ea87a5fcd3abeece18ac8a24a5c6ddea)'
# Preflight both targets before touching either. Never replace a different
# executable, user configuration or symlink.
for path in "$bin" "$cfg"; do
    if [ -L "$path" ] || { [ -e "$path" ] && [ ! -f "$path" ]; }; then
        echo "Refusing non-regular target: $path" >&2; exit 1
    fi
done
if [ -e "$bin" ]; then cmp -s "$bin" "$tmp/brain" || { echo "Existing different binary: $bin" >&2; exit 1; }; fi
if [ -e "$cfg" ]; then cmp -s "$cfg" "$here/nous.yaml" || { echo "Existing different profile: $cfg" >&2; exit 1; }; fi
mkdir -p "$HOME/.local/bin" "$HOME/.config/theseus"
if [ ! -e "$bin" ]; then install -m 755 "$tmp/brain" "$bin"; fi
if [ ! -e "$cfg" ]; then install -m 600 "$here/nous.yaml" "$cfg"; fi
chmod 755 "$bin"
chmod 600 "$cfg"
printf '%s  %s\n' "$binary_sha" "$bin" | sha256sum -c -
cmp "$cfg" "$here/nous.yaml"
"$bin" --version
echo BRAIN_INSTALL_PASS
