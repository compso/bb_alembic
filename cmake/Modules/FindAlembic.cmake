#=============================================================================
# Copyright 2011, Ivan Busquets.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of Ivan Busquets nor the names of any
#       other contributors to this software may be used to endorse or
#       promote products derived from this software without specific prior
#       written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#=============================================================================
#
# The module defines the following variables:
#	ALEMBIC_INCLUDE_DIR - path to Alembic headers
#	ALEMBIC_LIBRARY_DIR - path to Alembic static libs
#       ALEMBIC_FOUND 	    - true if the Alembic was found
#
# Example usage:
#   find_package(ALEMBIC)
#   if(ALEMBIC_FOUND)
#     message("ALEMBIC found: ${ALEMBIC_LIBRARY_DIR}")
#   endif()
#
#=============================================================================

message("-- Searching Alembic libraries.......")

IF(NOT ALEMBIC_DIR AND NOT $ENV{ALEMBIC_DIR} STREQUAL "")
  SET(ALEMBIC_DIR $ENV{ALEMBIC_DIR})
ENDIF()

macro(ALEMBIC_SET_PROPERTIES target)
	
	if(ALEMBIC_SHARED_LIBS)
		set(_alembic_DEFINES  "${_maya_DEFINES}" ALEMBIC_DLL)
	endif()
	target_include_directories(${target} PUBLIC ${ALEMBIC_INCLUDE_DIR} ${ALEMBIC_ILMBASE_INCLUDE_DIRECTORY})
	target_link_libraries(${target} ${ALEMBIC_LIBRARY} ${ALEMBIC_ILMBASE_HALF_LIB} ${ALEMBIC_ILMBASE_IEXMATH_LIB} ${ALEMBIC_ILMBASE_IEX_LIB} ${ALEMBIC_ILMBASE_ILMTHREAD_LIB} ${ALEMBIC_ILMBASE_IMATH_LIB})
	
	if(USE_HDF5)
		target_link_libraries(${target} ${ALEMBIC_HDF5_LIBS} ${ZLIB_LIBRARIES} ${SZIP_LIBRARIES})
	endif()
	
	target_compile_definitions(${target} PUBLIC ${_alembic_DEFINES})

		
endmacro(ALEMBIC_SET_PROPERTIES)


set(LIBRARY_PATHS 
	/usr/lib
	/usr/local/lib
	/sw/lib
	/opt/local/lib
	${ALEMBIC_DIR}/lib/
	${ALEMBIC_DIR}/lib/static)

# Find Alembic libs

find_library(ALEMBIC_LIBRARY
	NAMES Alembic
	PATHS ${LIBRARY_PATHS})

get_filename_component( ALEMBIC_LIBRARY_DIR ${ALEMBIC_LIBRARY} PATH )

# Find Alembic include dir
find_path ( ALEMBIC_INCLUDE_DIR Alembic/Abc/All.h
           ${ALEMBIC_DIR}/include
          )

include( FindPackageHandleStandardArgs )

find_package_handle_standard_args( "Alembic" DEFAULT_MSG
				  ALEMBIC_LIBRARY
                                  ALEMBIC_LIBRARY_DIR
				  ALEMBIC_INCLUDE_DIR								  
				  )

IF( ALEMBIC_FOUND )
  #  SET( MAYA_FOUND 1 CACHE STRING "Set to 1 if Maya is found, 0 otherwise" )
  MESSAGE( STATUS "Found Alembic!" )
ENDIF(  )

if(NOT ALEMBIC_FOUND)
    message(FATAL_ERROR "Try using -D ALEMBIC_DIR=/path/to/alembic")
endif()								
	