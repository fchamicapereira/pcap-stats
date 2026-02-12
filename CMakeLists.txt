###############################################################################
# Project version
###############################################################################

cmake_minimum_required(VERSION 3.16)

project(
    pcap-stats
    VERSION 1.0
    LANGUAGES C CXX
)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

###############################################################################
# Configuring C/C++ standard versions
###############################################################################

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED True)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED True)
set(CMAKE_C_EXTENSIONS True)

###############################################################################
# Enable asserts in RelWithDebInfo mode
###############################################################################

string(REPLACE "-DNDEBUG" "" CMAKE_CXX_FLAGS_RELWITHDEBINFO "${CMAKE_CXX_FLAGS_RELWITHDEBINFO}")

###############################################################################
# Setting some complation flags
###############################################################################

set(GLOBAL_COMPILATION_FLAGS
    -Wall
    -Wextra
    -Werror
    -Wfatal-errors
    -Wno-unused-parameter
    -Wnon-virtual-dtor
    -pedantic
    -Wcast-align
    -Wmisleading-indentation
    -Wdouble-promotion
    -fno-omit-frame-pointer
    -Wshadow
    -fdiagnostics-color=always
)

if (ENABLE_ADDRESS_SANITIZER)
    message(STATUS "WARNING: Address sanitizer enabled")
    add_compile_options(-fsanitize=address -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address)
endif()

###############################################################################
# Setting output targets
###############################################################################

set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/lib)
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)

################################################################################
# Sanity check - Disallow building in source.
# Otherwise we would overwrite the Makefiles of the old build system.
################################################################################

if("${CMAKE_SOURCE_DIR}" STREQUAL "${CMAKE_BINARY_DIR}")
    message(FATAL_ERROR "In source builds are not allowed. You should invoke "
            "CMake from a different directory.")
endif()

################################################################################
# Add our CMake module directory to the list of module search directories
################################################################################

list(APPEND CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake/modules")

###############################################################################
# Configure external projects
###############################################################################

include(${CMAKE_SOURCE_DIR}/cmake/find_cli11.cmake)
include(${CMAKE_SOURCE_DIR}/cmake/find_json.cmake)
include(${CMAKE_SOURCE_DIR}/cmake/find_pcap.cmake)
include(${CMAKE_SOURCE_DIR}/cmake/find_zstd.cmake)

###############################################################################
# Build targets
###############################################################################

file(GLOB_RECURSE SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp)
add_executable(pcap-stats ${SOURCES})

set_target_properties(pcap-stats PROPERTIES OUTPUT_NAME pcap-stats)

target_include_directories(pcap-stats SYSTEM PUBLIC ${PCAP_INCLUDE_DIR})
target_include_directories(pcap-stats SYSTEM PUBLIC ${ZSTD_INCLUDE_DIRS})

target_link_libraries(pcap-stats PUBLIC CLI11::CLI11)
target_link_libraries(pcap-stats PRIVATE ZSTD::ZSTD)
target_link_libraries(pcap-stats PUBLIC ${PCAP_LIBRARY})
target_link_libraries(pcap-stats PUBLIC nlohmann_json)