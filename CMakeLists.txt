
project(bb_alembic)

CMAKE_MINIMUM_REQUIRED(VERSION 2.8.11)

MESSAGE(STATUS "CMAKE SYSTEM NAME: ${CMAKE_SYSTEM_NAME}")

IF (NOT DEFINED QUIET)
    SET(CMAKE_VERBOSE_MAKEFILE TRUE)
ENDIF()

set(BBA_MAJOR_VERSION 1)
set(BBA_MINOR_VERSION 1)
set(BBA_PATCH_VERSION 1)
set(BBA_VERSION "${BBA_MAJOR_VERSION}.${BBA_MINOR_VERSION}.${BBA_PATCH_VERSION}")
set(VERSION ${BBA_VERSION})

OPTION(USE_ARNOLD "Include Arnold stuff" ON)
OPTION(USE_MTOA "Include MtoA stuff" ON)
OPTION(USE_MAYA "Include Maya stuff" ON)
OPTION(USE_HDF5 "Include HDF5 stuff" OFF)
OPTION(USE_STATIC_BOOST "Build with static Boost libs" ON)
OPTION(USE_ILMBASE_STATIC_LIBS "Build with static ilmBase libs" ON)
OPTION(USE_STATIC_HDF5 "Build with static HDF5 libs" OFF)
OPTION(ALEMBIC_SHARED_LIBS "Build shared libraries" ON)

IF(NOT MTOA_VERSION AND NOT $ENV{MTOA_VERSION} STREQUAL "")
  SET(MTOA_VERSION $ENV{MTOA_VERSION})
ENDIF()

# set(CMAKE_BUILD_TYPE RELEASE)
# set(CMAKE_VERBOSE_MAKEFILE FALSE)
# set(CMAKE_SKIP_RPATH TRUE)
# CMAKE_POLICY(SET CMP0012 OLD)

# Fix to stop crash on OSX < 10.9
set(CMAKE_OSX_DEPLOYMENT_TARGET 10.8)

#variable helpers
# Cmake system specific flags
SET(WINDOWS FALSE)
IF ("${CMAKE_SYSTEM_NAME}" MATCHES "Windows")
    SET(WINDOWS TRUE)
ENDIF()

SET(DARWIN FALSE)
IF ("${CMAKE_SYSTEM_NAME}" MATCHES "Darwin")
    SET(DARWIN TRUE)
    # suppress rpath warning
    IF (POLICY CMP0042)
        CMAKE_POLICY(SET CMP0042 OLD)
    ENDIF()
ENDIF()

SET(LINUX FALSE)
IF ("${CMAKE_SYSTEM_NAME}" MATCHES "Linux")
    SET(LINUX TRUE)
ENDIF()

IF (LINUX OR DARWIN)
	INCLUDE(CheckCXXCompilerFlag)
	CHECK_CXX_COMPILER_FLAG("-std=c++11" COMPILER_SUPPORTS_CXX11)
	CHECK_CXX_COMPILER_FLAG("-std=c++0x" COMPILER_SUPPORTS_CXX0X)
	IF (COMPILER_SUPPORTS_CXX11)
		SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11")
	ELSEIF (COMPILER_SUPPORTS_CXX0X)
		SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++0x")
	ENDIF()
ENDIF()

# Compiler flags
if (WINDOWS)
    # Disable some of the bullshit warnings MSVC wants to barf
    add_definitions( "-W3 -MP -D_CRT_SECURE_NO_WARNINGS -wd4005 -wd4996 -wd4305 -wd4244 -nologo" )
	set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /MP")
ELSEIF (DARWIN)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -stdlib=libc++")
ENDIF()


IF (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -fPIC")
ENDIF()

# Set some debug vs opt flags
IF ("${CMAKE_BUILD_TYPE}" MATCHES "Debug")
    ADD_DEFINITIONS(-DDEBUG=1 -UNDEBUG)
    IF (NOT WINDOWS)
        ADD_DEFINITIONS(-Wall -Werror -Wextra -Wno-unused-parameter)
    ENDIF()
ELSEIF ("${CMAKE_BUILD_TYPE}" MATCHES "Release")
    ADD_DEFINITIONS(-DNDEBUG=1 -UDEBUG)
    IF (NOT WINDOWS)
        ADD_DEFINITIONS(-O3)
    ENDIF()
ENDIF()

IF (NOT WINDOWS)
    SET(EXTERNAL_MATH_LIBS "-lm")
ELSE()
    SET(EXTERNAL_MATH_LIBS "")
ENDIF()

IF (WINDOWS)
    ADD_DEFINITIONS(-DPLATFORM_WINDOWS -DPLATFORM=WINDOWS)
ELSEIF (DARWIN)
    ADD_DEFINITIONS(-DPLATFORM_DARWIN -DPLATFORM=DARWIN)
ELSE()
    ADD_DEFINITIONS(-DPLATFORM_LINUX -DPLATFORM=LINUX -D_LINUX)
ENDIF()

# check if we have a local cmake include file and include it if we do
# this is useful for setting our arnold location as an alternative to
# environment variables
if(EXISTS ${CMAKE_SOURCE_DIR}/local.cmake)
    message(STATUS "Using local.cmake")
    include(${CMAKE_SOURCE_DIR}/local.cmake)
endif()

IF (DEFINED ENV{INSTALL_PREFIX})
    SET( CMAKE_INSTALL_PREFIX
        $ENV{INSTALL_PREFIX}/${BBA_VERSION})
ENDIF()

if (NOT DEFINED INSTALL_DIR)
    if (DEFINED INSTALL_ROOT)
        set(INSTALL_DIR "${INSTALL_ROOT}/bb_alembic-${BBA_VERSION}")
        message("INSTALL_ROOT defined. Adding versions automatically:\n\t${INSTALL_DIR}")
    else()
        set(INSTALL_ROOT "${CMAKE_BINARY_DIR}/dist")
        set(INSTALL_DIR "${INSTALL_ROOT}/bb_alembic-${BBA_VERSION}")
    
        message("INSTALL_DIR not defined. Defaulting to:\n\t${INSTALL_DIR}")
    endif()
else()
    message("Installing to:\n\t${INSTALL_DIR}")
endif()

# Set up installation paths
set(DSO_INSTALL_DIR ${INSTALL_DIR}/procedurals)
set(TRANSLATOR_INSTALL_DIR ${INSTALL_DIR}/extensions)
set(SHADERS_INSTALL_DIR ${INSTALL_DIR}/shaders)
set(PLUGINS_INSTALL_DIR ${INSTALL_DIR}/plug-ins)
set(PYSIDE_INSTALL_DIR ${INSTALL_DIR}/pyside)
set(CMAKE_INSTALL_PREFIX ${INSTALL_DIR})
# Tell me what my install location would be
MESSAGE(STATUS "The install dir is ${CMAKE_INSTALL_PREFIX}")

# check in the source directory
SET(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} ${PROJECT_SOURCE_DIR}/cmake/Modules)

######
# Base libs
######


# IlmBase
INCLUDE("./cmake/AlembicIlmBase.cmake")
INCLUDE_DIRECTORIES(${ALEMBIC_ILMBASE_INCLUDE_DIRECTORY})

# INCLUDE("./cmake/AlembicBoost.cmake")

SET(Boost_USE_STATIC_LIBS ${USE_STATIC_BOOST})
find_package(Boost REQUIRED COMPONENTS regex system program_options filesystem thread)
INCLUDE_DIRECTORIES(${Boost_INCLUDE_DIRS})
# Find alembic
find_package(Alembic REQUIRED)

# Find HDF5
IF (USE_HDF5)
    find_package(AlembicHDF5 REQUIRED)
    find_package(AlembicZLIB REQUIRED)
    SET(CORE_LIBS        
        ${HDF5_LIBRARIES}
        ${ALEMBIC_ILMBASE_LIBS}
        ${CMAKE_THREAD_LIBS_INIT}
        ${ZLIB_LIBRARIES}
        ${EXTERNAL_MATH_LIBS}
    )
ELSE()
    SET(CORE_LIBS        
        ${ALEMBIC_ILMBASE_LIBS}
        ${CMAKE_THREAD_LIBS_INIT}
        ${EXTERNAL_MATH_LIBS}
    )
ENDIF()



# Maya
IF (USE_MAYA)
    INCLUDE("./cmake/AlembicMaya.cmake")
    IF (${MAYA_FOUND})
        MESSAGE(STATUS "Building Maya plugins")
        ADD_SUBDIRECTORY(maya)
    ELSE()
        MESSAGE(STATUS "Maya not found")
    ENDIF()
ENDIF()

# Arnold
IF (USE_ARNOLD)
    INCLUDE("./cmake/AlembicArnold.cmake")
    IF (ALEMBIC_ARNOLD_FOUND)
        MESSAGE(STATUS "Building Arnold plugins")
        ADD_SUBDIRECTORY( arnold )
    ELSE()
        MESSAGE(STATUS "Arnold Not found")
    ENDIF()
ENDIF()

IF (USE_MTOA)
    INCLUDE("./cmake/AlembicMtoA.cmake")
    IF (ALEMBIC_MTOA_FOUND)
        MESSAGE(STATUS "Building MtoA plugins")
        ADD_SUBDIRECTORY( mtoa )
    ELSE()
        MESSAGE(STATUS "MtoA not found")
    ENDIF()
ENDIF()

#-******************************************************************************

SET(_config_msg "\n   * Alembic Configuration          ===")
MACRO(info_cfg_option
    _setting)
    SET(_msg "   * ${_setting}")
    STRING(LENGTH "${_msg}" _len)
    WHILE("36" GREATER "${_len}")
        SET(_msg "${_msg} ")
        MATH(EXPR _len "${_len} + 1")
    ENDWHILE()
    SET(_config_msg "${_config_msg}\n${_msg}${${_setting}}")
ENDMACRO()

info_cfg_option(USE_ARNOLD)
info_cfg_option(USE_MAYA)
info_cfg_option(USE_MTOA)
info_cfg_option(ALEMBIC_SHARED_LIBS)
MESSAGE("${_config_msg}")
