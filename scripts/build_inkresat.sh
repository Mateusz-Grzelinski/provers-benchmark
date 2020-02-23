#!/bin/bash

# bash 'strict' mode
set -euo pipefail

INKRESAT_LINK="https://www.ps.uni-saarland.de/~kaminski/inkresat/inkresat-1.0.tar.bz2"

INKRESAT=$(basename ${INKRESAT_LINK})

BUILD_DIR="provers"
INKRESAT_BUILD_TAR_GZ=$BUILD_DIR/${INKRESAT}
INKRESAT_BUILD_DIR=$BUILD_DIR/inkresat

install_inkresat() {
  mkdir -p "$INKRESAT_BUILD_DIR"
  if [ ! -f "$INKRESAT_BUILD_TAR_GZ" ]; then
    wget -q --show-progress -O "$INKRESAT_BUILD_TAR_GZ" "$INKRESAT_LINK"
  fi
  tar -xf "$INKRESAT_BUILD_TAR_GZ" -C "$BUILD_DIR"
  (cd "$INKRESAT_BUILD_DIR" && make inkresat)
}

# remember to install dependencies: ocaml, omcaml-find, libextlib-ocaml-dev (on aur:ocaml-extlib), make, gcc, g++
echo "Building Inkresat. Read $0 to fix compilation issues"
install_inkresat
echo "Inkresat build finished"

# this is diff with working (compiled) inkresat. Probably newer program versions caused build to fail
# diff --recursive inkresat inkresat-ok  # clean inkresat diffed with working inkresat (after performing make clean)
# diff --recursive inkresat/minisat-2.2.0/mtl/template.mk inkresat-ok/minisat-2.2.0/mtl/template.mk
# 27c27
# < CFLAGS    += -I$(MROOT) -D __STDC_LIMIT_MACROS -D __STDC_FORMAT_MACROS
# ---
# > CFLAGS    += -I$(MROOT) -D __STDC_LIMIT_MACROS -D __STDC_FORMAT_MACROS -fpermissive -fPIC
# diff --recursive inkresat/src/Makefile inkresat-ok/src/Makefile
# 67c67
# < 	g++ -c -I$(MINISATSRC) -I`ocamlc -where` -D __STDC_LIMIT_MACROS -D __STDC_FORMAT_MACROS minisat_if.cc -o minisat_if.o -fPIC
# ---
# > 	g++ -c -I$(MINISATSRC) -I`ocamlc -where` -D __STDC_LIMIT_MACROS -D __STDC_FORMAT_MACROS minisat_if.cc -o minisat_if.o -fPIC -fpermissive
