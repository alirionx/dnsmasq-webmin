#!/usr/bin/env bash
# Builds dist/dnsmasq-webmin_<version>_amd64.deb (amd64 only)
#
#   PY=3.12            python3 version of the target distro (Ubuntu 24.04: 3.12, Debian 13: 3.13)
#   REVISION=1         Debian revision (the python version is appended: 1+py313)
#   MAINTAINER="Name <mail>"
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HERE="$ROOT/packaging/deb"
ARCH=amd64
WHEEL_ARCH=x86_64
PY="${PY:-3.12}"
REVISION="${REVISION:-1}"
MAINTAINER="${MAINTAINER:-$(git -C "$ROOT" config user.name 2>/dev/null || echo dnsmasq-webmin) <$(git -C "$ROOT" config user.email 2>/dev/null || echo root@localhost)>}"

VERSION="$(python3 -c "import tomllib; print(tomllib.load(open('$ROOT/pyproject.toml', 'rb'))['project']['version'])")-$REVISION+py${PY/./}"
PY_NEXT="${PY%.*}.$(( ${PY#*.} + 1 ))"
CPTAG="cp${PY/./}"

BUILD="$ROOT/build/deb/dnsmasq-webmin_${VERSION}_${ARCH}"
OUT="$ROOT/dist"
rm -rf "$BUILD"
mkdir -p "$BUILD/DEBIAN" "$OUT"

echo ">> frontend"
(cd "$ROOT/frontend" && npm ci --no-audit --no-fund --silent && npm run build --silent)

echo ">> application"
OPT="$BUILD/opt/dnsmasq-webmin"
mkdir -p "$OPT/frontend"
cp -r "$ROOT/app" "$OPT/app"
cp -r "$ROOT/frontend/dist" "$OPT/frontend/dist"
find "$OPT" -name __pycache__ -type d -prune -exec rm -rf {} +

echo ">> python dependencies for $CPTAG / $ARCH"
python3 -c "import tomllib; print('\n'.join(tomllib.load(open('$ROOT/pyproject.toml', 'rb'))['project']['dependencies']))" \
  > "$BUILD/requirements.txt"
python3 -m pip install --quiet --disable-pip-version-check --no-compile \
  --target "$OPT/lib" --only-binary=:all: \
  --implementation cp --python-version "$PY" --abi "$CPTAG" \
  --platform "manylinux_2_28_$WHEEL_ARCH" --platform "manylinux_2_17_$WHEEL_ARCH" \
  --platform "manylinux2014_$WHEEL_ARCH" --platform "linux_$WHEEL_ARCH" \
  -r "$BUILD/requirements.txt"
rm -rf "$OPT/lib/bin" "$BUILD/requirements.txt"

echo ">> system integration"
install -Dm644 "$HERE/dnsmasq-webmin.service" "$BUILD/usr/lib/systemd/system/dnsmasq-webmin.service"
install -Dm644 "$HERE/dnsmasq-webmin.env" "$BUILD/etc/dnsmasq-webmin/dnsmasq-webmin.env"
install -Dm644 "$ROOT/README.md" "$BUILD/usr/share/doc/dnsmasq-webmin/README.md"
for script in postinst prerm postrm; do
  install -m755 "$HERE/$script" "$BUILD/DEBIAN/$script"
done
echo "/etc/dnsmasq-webmin/dnsmasq-webmin.env" > "$BUILD/DEBIAN/conffiles"

SIZE="$(du -sk --exclude=DEBIAN "$BUILD" | cut -f1)"
sed -e "s|@VERSION@|$VERSION|" -e "s|@ARCH@|$ARCH|" -e "s|@MAINTAINER@|$MAINTAINER|" \
    -e "s|@SIZE@|$SIZE|" -e "s|@PY@|$PY|" -e "s|@PY_NEXT@|$PY_NEXT|" \
    "$HERE/control.in" > "$BUILD/DEBIAN/control"

dpkg-deb --root-owner-group -Zxz --build "$BUILD" "$OUT/" >/dev/null
echo ">> $OUT/dnsmasq-webmin_${VERSION}_${ARCH}.deb"
