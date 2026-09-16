cmake_minimum_required(VERSION 3.20)

project(CharacterDynamicsReference LANGUAGES CXX)
find_package(Python3 COMPONENTS Interpreter REQUIRED)

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
    Src/living_dynamics.cpp
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

add_executable(character_dynamics_runtime_closure_acceptance_smoke tests/runtime_closure_acceptance_smoke.cpp)
target_link_libraries(character_dynamics_runtime_closure_acceptance_smoke PRIVATE character_dynamics_runtime)
add_test(NAME character_dynamics_runtime_closure_acceptance_smoke
         COMMAND character_dynamics_runtime_closure_acceptance_smoke)

add_executable(character_dynamics_runtime_trace_smoke tests/runtime_trace_smoke.cpp)
target_link_libraries(character_dynamics_runtime_trace_smoke PRIVATE character_dynamics_runtime)
add_test(NAME character_dynamics_runtime_trace_smoke
         COMMAND character_dynamics_runtime_trace_smoke)

add_executable(character_dynamics_runtime_mechanism_fixtures_smoke tests/runtime_mechanism_fixtures_smoke.cpp)
target_link_libraries(character_dynamics_runtime_mechanism_fixtures_smoke PRIVATE character_dynamics_runtime)
add_test(NAME character_dynamics_runtime_mechanism_fixtures_smoke
         COMMAND character_dynamics_runtime_mechanism_fixtures_smoke)

add_executable(character_dynamics_runtime_channel_coverage_smoke tests/runtime_channel_coverage_smoke.cpp)
target_link_libraries(character_dynamics_runtime_channel_coverage_smoke PRIVATE character_dynamics_runtime)
add_test(NAME character_dynamics_runtime_channel_coverage_smoke
         COMMAND character_dynamics_runtime_channel_coverage_smoke)
add_executable(character_dynamics_runtime_case_smoke tests/runtime_case_smoke.cpp)
target_link_libraries(character_dynamics_runtime_case_smoke PRIVATE character_dynamics_runtime)
add_executable(character_dynamics_single_room_demo Src/single_room_demo.cpp)
target_link_libraries(character_dynamics_single_room_demo PRIVATE character_dynamics_runtime)
add_executable(character_dynamics_living_dynamics_smoke tests/living_dynamics_smoke.cpp)
target_link_libraries(character_dynamics_living_dynamics_smoke PRIVATE character_dynamics_runtime)
add_test(NAME character_dynamics_living_dynamics_smoke COMMAND character_dynamics_living_dynamics_smoke)
add_executable(character_dynamics_free_run Src/free_run.cpp)
target_link_libraries(character_dynamics_free_run PRIVATE character_dynamics_runtime)
add_test(NAME character_dynamics_free_run_report
         COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tools/free_run_report.py"
         "${CMAKE_CURRENT_SOURCE_DIR}/demo/living_dynamics_v0"
         "$<TARGET_FILE:character_dynamics_free_run>")
set(DEMO_TRACE_DIR "${CMAKE_CURRENT_BINARY_DIR}/single-room-traces")
add_test(NAME single_room_demo_generate_deadline
         COMMAND character_dynamics_single_room_demo --scenario deadline --output "${DEMO_TRACE_DIR}/deadline.json")
add_test(NAME single_room_demo_generate_phone
         COMMAND character_dynamics_single_room_demo --scenario phone --output "${DEMO_TRACE_DIR}/phone.json")
add_test(NAME single_room_demo_generate_commitment
         COMMAND character_dynamics_single_room_demo --scenario commitment --output "${DEMO_TRACE_DIR}/commitment.json")
set_tests_properties(single_room_demo_generate_deadline single_room_demo_generate_phone single_room_demo_generate_commitment
    PROPERTIES FIXTURES_SETUP single_room_demo_traces)
add_test(NAME single_room_demo_semantic_validation
         COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tests/single_room_demo_validate.py"
         "${DEMO_TRACE_DIR}/deadline.json" "${DEMO_TRACE_DIR}/phone.json" "${DEMO_TRACE_DIR}/commitment.json")
set_tests_properties(single_room_demo_semantic_validation PROPERTIES FIXTURES_REQUIRED single_room_demo_traces)
# Each matrix entry executes the smallest executable that owns that semantic
# case; labels are no longer aliases for one monolithic smoke binary.
foreach(gate_name IN ITEMS
    runtime_clock_authority_smoke runtime_world_event_boundary_smoke
    runtime_world_event_source_consistency runtime_action_start_validation_smoke
    runtime_action_completion_smoke runtime_action_invalidation_smoke
    runtime_hidden_event_no_leak_smoke runtime_perception_projection_smoke
    runtime_typed_rejection_smoke runtime_weak_event_continue_smoke
    runtime_state_threshold_boundary_smoke)
    add_test(NAME ${gate_name} COMMAND character_dynamics_runtime_case_smoke --case ${gate_name})
endforeach()

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
