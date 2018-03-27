#!/bin/bash

export MAYA_VERSION=2018
export MAYA_LOCATION=/usr/autodesk/maya${MAYA_VERSION}
export ALEMBIC_VERSION=1.7.4
# export MTOA_VERSION=1.4.0
# export ARNOLD_VERSION=4.2.15.1

# export MTOA_VERSION=2.1.0.1
# export ARNOLD_VERSION=5.0.2.1

export MTOA_VERSION=2.1.0.2
export ARNOLD_VERSION=5.0.1.2

CLANG_VERSION=3.6.0
CLANG_ROOT=/opt/clang/${CLANG_VERSION}
# GCC_ROOT=/opt/gcc/4.8.4
GCC_ROOT=/usr
# LD_LIBRARY_PATH=${CLANG_ROOT}/lib
# LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${GCC_ROOT}/lib64

# PYTHON_HOME=/sw/python/2.7.11
# export PYTHON=${PYTHON_HOME}
# export PYTHON_VERSION=2.7
# LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${PYTHON_HOME}/lib

export LD_LIBRARY_PATH

HDF5_ROOT=/usr

CMAKE=cmake

SUDO=sudo

# CXX=${CLANG_ROOT}/bin/clang++
# CC=${CLANG_ROOT}/bin/clang
CXX=${GCC_ROOT}/bin/g++
CC=${GCC_ROOT}/bin/gcc

INSTALL_PREFIX=/home/software/bb_alembic
SW=/home/software

${CMAKE} \
-DCMAKE_CXX_COMPILER:FILEPATH=${CXX} \
-DCMAKE_C_COMPILER:FILEPATH=${CC} \
-DALEMBIC_DIR=$SW/alembic/$ALEMBIC_VERSION \
-DALEMBIC_LIBRARY=$SW/alembic/$ALEMBIC_VERSION/lib/libAlembic.a \
-DUSE_ARNOLD=ON \
-DARNOLD_ROOT=$SW/solidangle/arnold/${ARNOLD_VERSION} \
-DILMBASE_ROOT=$SW/openexr/2.2.0 \
-DUSE_MAYA=ON \
-DMAYA_ROOT=${MAYA_LOCATION} \
-DALEMBIC_MAYA_INC_ROOT=$HOME/Dev/maya${MAYA_VERION}_devkit/devkitBase/include \
-DUSE_HDF5=ON \
-DUSE_STATIC_HDF5=ON \
-DHDF5_ROOT=${HDF5_ROOT} \
-DBOOST_ROOT=$SW/boost/1.59.0 \
-DUSE_STATIC_BOOST=OFF \
-DUSE_MTOA=ON \
-DMTOA_ROOT=$SW/solidangle/mtoa/${MTOA_VERSION}/${MAYA_VERSION} \
..

make -j 20

make install

rsync -avzh --progress dist/bb_alembic-2.0.0/ /software/bb_alembic/2.0.0/
