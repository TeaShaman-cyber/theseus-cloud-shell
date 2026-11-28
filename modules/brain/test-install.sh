#!/bin/sh
# Real release archive, isolated HOME. No network, no live inference.
set -eu
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
archive=$(realpath "${1:?path to pinned release archive required}")
home=$(mktemp -d)
trap 'rm -rf -- "$home"' EXIT
export HOME="$home"
"$here/install.sh" "$archive"
bin="$HOME/.local/bin/brain"
cfg="$HOME/.config/theseus/brain-nous.yaml"
test "$("$bin" --version)" = 'brain 0.13.2 (commit 377cc5e3ea87a5fcd3abeece18ac8a24a5c6ddea)'
for provider in nous openrouter bothub nim; do
    profile="$HOME/.config/theseus/brain-$provider.yaml"
    cmp "$here/$provider.yaml" "$profile"
    test "$(stat -c %a "$profile")" = 600
done
test "$(stat -c %a "$cfg")" = 600
test "$(stat -c %a "$bin")" = 755
"$here/install.sh" "$archive"
# Bad archive must not replace an existing good installation.
printf bad > "$home/bad.tar.gz"
if "$here/install.sh" "$home/bad.tar.gz"; then exit 1; fi
test "$("$bin" --version)" = 'brain 0.13.2 (commit 377cc5e3ea87a5fcd3abeece18ac8a24a5c6ddea)'
# Do not silently replace locally changed settings.
printf '\n# local change\n' >> "$cfg"
if "$here/install.sh" "$archive"; then exit 1; fi
grep -q '^# local change$' "$cfg"
# All profiles are preflighted, so one conflict cannot install another.
cp "$here/nous.yaml" "$cfg"
other="$HOME/.config/theseus/brain-nim.yaml"
rm "$HOME/.config/theseus/brain-openrouter.yaml"
printf '\n# local change\n' >> "$other"
if "$here/install.sh" "$archive"; then exit 1; fi
test ! -e "$HOME/.config/theseus/brain-openrouter.yaml"
grep -q '^# local change$' "$other"
cp "$here/nim.yaml" "$other"
"$here/install.sh" "$archive"
# Existing unrelated executable is never clobbered.
printf unrelated > "$bin"
if "$here/install.sh" "$archive"; then exit 1; fi
test "$(cat "$bin")" = unrelated
# A fresh install with an invalid archive leaves no binary/config.
rm -f "$bin" "$cfg" "$HOME/.config/theseus/brain-openrouter.yaml" "$HOME/.config/theseus/brain-bothub.yaml" "$HOME/.config/theseus/brain-nim.yaml"
if "$here/install.sh" "$home/bad.tar.gz"; then exit 1; fi
test ! -e "$bin"; test ! -e "$cfg"
test ! -e "$HOME/.config/theseus/brain-openrouter.yaml"; test ! -e "$HOME/.config/theseus/brain-bothub.yaml"
test ! -e "$HOME/.config/theseus/brain-nim.yaml"
echo BRAIN_INSTALL_CONTRACT_PASS
