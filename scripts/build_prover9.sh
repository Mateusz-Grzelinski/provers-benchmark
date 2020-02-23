#!/bin/bash

# bash 'strict' mode
set -euo pipefail

PROVER9_LINK="https://www.cs.unm.edu/~mccune/prover9/download/LADR-2009-11A.tar.gz"

# name with extension
PROVER9=$(basename ${PROVER9_LINK})

# paths
BUILD_DIR="provers"
PROVER9_BUILD_TAR_GZ=$BUILD_DIR/${PROVER9}
PROVER9_BUILD_DIR=$BUILD_DIR/${PROVER9/.*/}

install_prover9() {
  mkdir -p "$PROVER9_BUILD_DIR"
  if [ ! -f "$PROVER9_BUILD_TAR_GZ" ]; then
    wget -q --show-progress -O $PROVER9_BUILD_TAR_GZ $PROVER9_LINK
  fi
  # prover9 unpacks to new directory, thats why unpack it to BUILD_DIR, not PROVER9_BUILD_DIR
  tar -xf $PROVER9_BUILD_TAR_GZ -C $BUILD_DIR
  (cd "$PROVER9_BUILD_DIR" && make all)
}

echo "Building Prover9"
install_prover9
echo "Prover9 build finished"
