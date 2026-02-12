###############################################################################
# Find nlohmann_json
###############################################################################

include(FetchContent)

FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json
    GIT_TAG        v3.11.3
)

FetchContent_MakeAvailable(json)