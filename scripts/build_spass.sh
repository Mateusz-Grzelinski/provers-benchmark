#!/bin/bash

# bash 'strict' mode
set -euo pipefail

SPASS_LINK="http://www.spass-prover.org/download/sources/spass39.tgz"

# name with extension
SPASS=$(basename ${SPASS_LINK})

# paths
BUILD_DIR="provers"
SPASS_BUILD_TGZ=$BUILD_DIR/${SPASS}
SPASS_BUILD_DIR=$BUILD_DIR/${SPASS/.*/}

install_spass() {
  mkdir -p "$SPASS_BUILD_DIR"
  if [ ! -f "$SPASS_BUILD_TGZ" ]; then
    wget -q --show-progress -O $SPASS_BUILD_TGZ $SPASS_LINK
  fi
  tar -xf $SPASS_BUILD_TGZ -C $SPASS_BUILD_DIR
  (cd "$SPASS_BUILD_DIR" && make)
}

echo "Building SPASS"
install_spass
echo "SPASS build finished"
