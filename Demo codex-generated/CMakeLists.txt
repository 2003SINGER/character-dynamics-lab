cmake_minimum_required(VERSION 3.20)

project(CharacterDynamicsReference LANGUAGES CXX)

set(CHARACTER_DYNAMICS_GIT_REVISION "" CACHE STRING "Revision recorded in generated experiment provenance")
find_package(Git QUIET)
if(NOT CHARACTER_DYNAMICS_GIT_REVISION AND GIT_FOUND)
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

set(CHARACTER_DYNAMICS_RUNTIME_SOURCES
    Src/action.cpp
    Src/simulation_time.cpp
    Src/object.cpp
    Src/scene.cpp
    Src/scene_snapshot.cpp
    Src/world_primitive.cpp
    Src/world.cpp
    Src/world_runtime_adapter.cpp
    Src/continuous_runtime.cpp
    Src/observation.cpp
    Src/appraisal.cpp
    Src/state.cpp
    Src/parameter_config.cpp
    Src/candidate_scoring.cpp
    Src/decision.cpp
    Src/simulation.cpp
    Src/runtime_scheduler.cpp
)

add_library(character_dynamics_runtime STATIC ${CHARACTER_DYNAMICS_RUNTIME_SOURCES})
target_include_directories(character_dynamics_runtime PUBLIC Inc)
target_compile_definitions(character_dynamics_runtime PUBLIC
    CHARACTER_DYNAMICS_GIT_REVISION="${CHARACTER_DYNAMICS_GIT_REVISION}")
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(character_dynamics_runtime PRIVATE -Wall -Wextra -Wpedantic)
elseif(MSVC)
    target_compile_options(character_dynamics_runtime PRIVATE /W4)
endif()

add_executable(character_dynamics_reference Src/main.cpp)
target_link_libraries(character_dynamics_reference PRIVATE character_dynamics_runtime)

target_compile_definitions(character_dynamics_reference PRIVATE
    CHARACTER_DYNAMICS_GIT_REVISION="${CHARACTER_DYNAMICS_GIT_REVISION}")

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(character_dynamics_reference PRIVATE -Wall -Wextra -Wpedantic)
elseif(MSVC)
    target_compile_options(character_dynamics_reference PRIVATE /W4)
endif()

if(MINGW)
    target_link_options(character_dynamics_reference PRIVATE
        -static
        -static-libgcc
        -static-libstdc++)
endif()

enable_testing()
add_test(NAME character_dynamics_reference_smoke
         COMMAND character_dynamics_reference --verify)

add_executable(character_dynamics_core_smoke tests/core_experiment_smoke.cpp)
target_link_libraries(character_dynamics_core_smoke PRIVATE character_dynamics_runtime)
if(MINGW)
    target_link_options(character_dynamics_core_smoke PRIVATE
        -static -static-libgcc -static-libstdc++)
endif()
add_test(NAME character_dynamics_core_experiment_smoke
         COMMAND character_dynamics_core_smoke)

add_executable(character_dynamics_runtime_scheduler_smoke tests/runtime_scheduler_smoke.cpp)
target_link_libraries(character_dynamics_runtime_scheduler_smoke PRIVATE character_dynamics_runtime)
add_test(NAME character_dynamics_runtime_scheduler_smoke
         COMMAND character_dynamics_runtime_scheduler_smoke)

add_executable(character_dynamics_runtime_vertical_slice_smoke tests/runtime_vertical_slice_smoke.cpp)
target_link_libraries(character_dynamics_runtime_vertical_slice_smoke PRIVATE character_dynamics_runtime)
add_test(NAME character_dynamics_runtime_vertical_slice_smoke
         COMMAND character_dynamics_runtime_vertical_slice_smoke)

add_executable(character_dynamics_replay_core
    Src/replay_core_cli.cpp
    Src/state.cpp
    Src/parameter_config.cpp
    Src/candidate_scoring.cpp
)
target_include_directories(character_dynamics_replay_core PRIVATE Inc)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(character_dynamics_replay_core PRIVATE -Wall -Wextra -Wpedantic)
elseif(MSVC)
    target_compile_options(character_dynamics_replay_core PRIVATE /W4)
endif()
if(MINGW)
    target_link_options(character_dynamics_replay_core PRIVATE
        -static -static-libgcc -static-libstdc++)
endif()
add_test(NAME character_dynamics_replay_core_version
         COMMAND character_dynamics_replay_core --version)
