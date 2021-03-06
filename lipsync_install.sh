#!/bin/bash

export MAYA_VERSION=2018
export MAYA_LOCATION=/usr/autodesk/maya${MAYA_VERSION}
export ALEMBIC_VERSION=1.7.0
# export MTOA_VERSION=1.4.0
# export ARNOLD_VERSION=4.2.15.1

export MTOA_VERSION=2.0.1.1
export ARNOLD_VERSION=5.0.1.1

CLANG_VERSION=3.6.0
CLANG_ROOT=/opt/clang/${CLANG_VERSION}
GCC_ROOT=/opt/gcc/4.8.4
LD_LIBRARY_PATH=${CLANG_ROOT}/lib
LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${GCC_ROOT}/lib64

PYTHON_HOME=/sw/python/2.7.11
export PYTHON=${PYTHON_HOME}
export PYTHON_VERSION=2.7
LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${PYTHON_HOME}/lib

export LD_LIBRARY_PATH

HDF5_ROOT=/sw/pkg/hdf5/1.8.7

CMAKE=/opt/cmake-3.6.2/bin/cmake

SUDO=sudo

# CXX=${CLANG_ROOT}/bin/clang++
# CC=${CLANG_ROOT}/bin/clang
CXX=${GCC_ROOT}/bin/g++
CC=${GCC_ROOT}/bin/gcc

INSTALL_PREFIX=/opt/bb_alembic

${CMAKE} \
-DCMAKE_CXX_COMPILER:FILEPATH=${CXX} \
-DCMAKE_C_COMPILER:FILEPATH=${CC} \
-DALEMBIC_DIR=/sw/pkg/alembic/$ALEMBIC_VERSION \
-DUSE_ARNOLD=ON \
-DARNOLD_ROOT=/sw/pkg/solidangle/arnold/${ARNOLD_VERSION} \
-DILMBASE_ROOT=/sw/pkg/openexr/2.2.0 \
-DUSE_MAYA=ON \
-DMAYA_ROOT=${MAYA_LOCATION} \
-DALEMBIC_MAYA_INC_ROOT=/home/ashleyr/Dev/3rdparty/Maya-devkit-${MAYA_VERSION}/include \
-DUSE_HDF5=ON \
-DUSE_STATIC_HDF5=OFF \
-DHDF5_ROOT=${HDF5_ROOT} \
-DBOOST_ROOT=/sw/pkg/boost/1.55.0 \
-DUSE_MTOA=ON \
-DMTOA_ROOT=/sw/pkg/solidangle/mtoa/${MTOA_VERSION}/${MAYA_VERSION} \
..

make -j `nproc`

make install
