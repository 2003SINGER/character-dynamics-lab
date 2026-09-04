cmake_minimum_required(VERSION 3.20)

project(CharacterDynamicsReference LANGUAGES CXX)

find_package(Git QUIET)
if(GIT_FOUND)
    execute_process(
        COMMAND "${GIT_EXECUTABLE}" -C "${CMAKE_CURRENT_SOURCE_DIR}" rev-parse --short HEAD
        OUTPUT_VARIABLE CHARACTER_DYNAMICS_GIT_REVISION
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET)
endif()
if(NOT CHARACTER_DYNAMICS_GIT_REVISION)
    set(CHARACTER_DYNAMICS_GIT_REVISION "unknown")
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_executable(character_dynamics_reference
    Src/main.cpp
    Src/action.cpp
    Src/simulation_time.cpp
    Src/object.cpp
    Src/scene.cpp
    Src/world_primitive.cpp
    Src/world.cpp
    Src/observation.cpp
    Src/appraisal.cpp
    Src/state.cpp
    Src/decision.cpp
    Src/simulation.cpp
)

target_include_directories(character_dynamics_reference PRIVATE Inc)
target_compile_definitions(character_dynamics_reference PRIVATE
    CHARACTER_DYNAMICS_GIT_REVISION="${CHARACTER_DYNAMICS_GIT_REVISION}")

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(character_dynamics_reference PRIVATE -Wall -Wextra -Wpedantic)
elseif(MSVC)
    target_compile_options(character_dynamics_reference PRIVATE /W4)
endif()

# Keep the reference executable runnable from CTest or Explorer without
# requiring every parent process to inherit MinGW's DLL directory.
if(MINGW)
    target_link_options(character_dynamics_reference PRIVATE
        -static
        -static-libgcc
        -static-libstdc++)
endif()

enable_testing()
add_test(NAME character_dynamics_reference_smoke
         COMMAND character_dynamics_reference --verify)
