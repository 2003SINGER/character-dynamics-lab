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

set(CHARACTER_DYNAMICS_ENGINE_SOURCES
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
    Src/runtime_scheduler.cpp
    Src/local_model_policy_v0.cpp
)

add_library(character_dynamics_engine STATIC ${CHARACTER_DYNAMICS_ENGINE_SOURCES})
target_include_directories(character_dynamics_engine PUBLIC Inc)
target_compile_definitions(character_dynamics_engine PUBLIC
    CHARACTER_DYNAMICS_GIT_REVISION="${CHARACTER_DYNAMICS_GIT_REVISION}")
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(character_dynamics_engine PRIVATE -Wall -Wextra -Wpedantic)
elseif(MSVC)
    target_compile_options(character_dynamics_engine PRIVATE /W4)
endif()

add_library(character_dynamics_reference_dynamics_v0 STATIC
    Src/reference_appraisal.cpp Src/reference_state.cpp Src/parameter_config.cpp
    Src/candidate_scoring.cpp Src/reference_decision.cpp Src/reference_rule_dynamics_v0.cpp
    Src/simulation.cpp)
target_link_libraries(character_dynamics_reference_dynamics_v0 PUBLIC character_dynamics_engine)
target_include_directories(character_dynamics_reference_dynamics_v0 PUBLIC Inc)

# Historical replay compatibility is an explicit legacy model adapter.  Keep
# it out of the generic replay target's source list so new replay consumers do
# not silently inherit ReferenceRuleDynamicsV0 semantics.
add_library(character_dynamics_legacy_replay_v0 STATIC Src/reference_state.cpp)
target_link_libraries(character_dynamics_legacy_replay_v0 PUBLIC character_dynamics_engine)
target_include_directories(character_dynamics_legacy_replay_v0 PUBLIC Inc)
add_library(character_dynamics_demo_living_v0 STATIC
    Src/appraisal.cpp Src/state.cpp Src/decision.cpp
    Src/living_dynamics.cpp Src/demo_living_dynamics_v0.cpp)
target_link_libraries(character_dynamics_demo_living_v0 PUBLIC character_dynamics_reference_dynamics_v0)
target_include_directories(character_dynamics_demo_living_v0 PUBLIC Inc)
add_library(character_dynamics_demo_living_v1 STATIC
    Src/appraisal_v1.cpp Src/state_v1.cpp Src/decision_v1.cpp Src/living_dynamics_v1.cpp
    Src/demo_living_dynamics_v1.cpp Src/laya_augmented_dynamics_v1.cpp)
target_link_libraries(character_dynamics_demo_living_v1 PUBLIC character_dynamics_engine character_dynamics_reference_dynamics_v0)
target_include_directories(character_dynamics_demo_living_v1 PUBLIC Inc)
target_compile_definitions(character_dynamics_demo_living_v1 PRIVATE DemoLivingV0=DemoLivingV1)
add_library(character_dynamics_runtime INTERFACE)
target_link_libraries(character_dynamics_runtime INTERFACE character_dynamics_engine character_dynamics_reference_dynamics_v0)

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
target_link_libraries(character_dynamics_living_dynamics_smoke PRIVATE character_dynamics_engine character_dynamics_demo_living_v0)
add_test(NAME character_dynamics_living_dynamics_smoke COMMAND character_dynamics_living_dynamics_smoke)
add_executable(character_dynamics_living_dynamics_v1_coupling_smoke tests/living_dynamics_v1_coupling_smoke.cpp)
target_link_libraries(character_dynamics_living_dynamics_v1_coupling_smoke PRIVATE character_dynamics_engine character_dynamics_demo_living_v1)
add_test(NAME character_dynamics_living_dynamics_v1_coupling_smoke COMMAND character_dynamics_living_dynamics_v1_coupling_smoke)
add_executable(character_dynamics_living_dynamics_v1_reconsideration_smoke tests/living_dynamics_v1_reconsideration_smoke.cpp)
target_link_libraries(character_dynamics_living_dynamics_v1_reconsideration_smoke PRIVATE character_dynamics_engine character_dynamics_demo_living_v1)
add_test(NAME character_dynamics_living_dynamics_v1_reconsideration_smoke COMMAND character_dynamics_living_dynamics_v1_reconsideration_smoke)
add_executable(character_dynamics_laya_soft_gate_smoke tests/laya_soft_gate_smoke.cpp)
target_link_libraries(character_dynamics_laya_soft_gate_smoke PRIVATE character_dynamics_engine character_dynamics_reference_dynamics_v0)
add_test(NAME character_dynamics_laya_soft_gate_smoke COMMAND character_dynamics_laya_soft_gate_smoke)
add_executable(character_dynamics_laya_semantic_contract_smoke tests/laya_semantic_contract_smoke.cpp)
target_link_libraries(character_dynamics_laya_semantic_contract_smoke PRIVATE character_dynamics_demo_living_v1)
add_test(NAME character_dynamics_laya_semantic_contract_smoke
         COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tools/laya_semantic_contract_smoke.py"
         "$<TARGET_FILE:character_dynamics_laya_semantic_contract_smoke>")
add_executable(character_dynamics_dynamics_model_isolation_smoke tests/dynamics_model_isolation_smoke.cpp)
target_link_libraries(character_dynamics_dynamics_model_isolation_smoke PRIVATE character_dynamics_engine character_dynamics_reference_dynamics_v0 character_dynamics_demo_living_v0)
add_test(NAME character_dynamics_dynamics_model_isolation_smoke COMMAND character_dynamics_dynamics_model_isolation_smoke)
add_executable(character_dynamics_free_run Src/free_run.cpp)
target_link_libraries(character_dynamics_free_run PRIVATE character_dynamics_engine character_dynamics_demo_living_v1)
add_test(NAME character_dynamics_personality_wiring_smoke
         COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tools/personality_wiring_smoke.py"
         "$<TARGET_FILE:character_dynamics_free_run>")
add_test(NAME character_dynamics_qwen_action_loopback_smoke
         COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tools/qwen_action_loopback_smoke.py"
         "$<TARGET_FILE:character_dynamics_free_run>")
add_test(NAME character_dynamics_laya_typed_policy_loopback_smoke
         COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tools/laya_typed_policy_loopback_smoke.py"
         "$<TARGET_FILE:character_dynamics_free_run>")
add_executable(character_dynamics_life_tape_smoke tests/life_tape_smoke.cpp)
target_link_libraries(character_dynamics_life_tape_smoke PRIVATE character_dynamics_engine character_dynamics_demo_living_v1)
add_test(NAME character_dynamics_life_tape_smoke COMMAND character_dynamics_life_tape_smoke)
add_executable(character_dynamics_room_control_feedback_smoke tests/room_control_feedback_smoke.cpp)
target_link_libraries(character_dynamics_room_control_feedback_smoke PRIVATE character_dynamics_engine character_dynamics_demo_living_v1)
add_test(NAME character_dynamics_room_control_feedback_smoke COMMAND character_dynamics_room_control_feedback_smoke)
add_executable(character_dynamics_long_horizon Src/long_horizon.cpp)
target_link_libraries(character_dynamics_long_horizon PRIVATE character_dynamics_engine character_dynamics_demo_living_v1)
add_test(NAME character_dynamics_long_horizon_pipeline_smoke
         COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tools/long_horizon_pipeline_smoke.py"
         "$<TARGET_FILE:character_dynamics_long_horizon>")
add_test(NAME character_dynamics_laya_long_horizon_pipeline_smoke
         COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tools/laya_long_horizon_pipeline_smoke.py"
         "$<TARGET_FILE:character_dynamics_long_horizon>")
add_test(NAME character_dynamics_free_run_report
         COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tools/free_run_report.py"
         "${CMAKE_CURRENT_SOURCE_DIR}/demo/living_dynamics_v1"
         "$<TARGET_FILE:character_dynamics_free_run>")
add_test(NAME character_dynamics_architecture_dependency_guard
         COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tools/architecture_dependency_guard.py"
         "${CMAKE_CURRENT_SOURCE_DIR}")
add_test(NAME character_dynamics_reference_rule_dynamics_v0_parity
         COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tools/reference_parity.py"
         "${CMAKE_CURRENT_SOURCE_DIR}")
add_test(NAME character_dynamics_demo_living_v0_artifact_guard
         COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tools/v0_artifact_guard.py"
         "${CMAKE_CURRENT_SOURCE_DIR}/..")
add_test(NAME character_dynamics_demo_living_v1_policy_source_guard
         COMMAND ${Python3_EXECUTABLE} "${CMAKE_CURRENT_SOURCE_DIR}/tools/v1_policy_source_guard.py"
         "${CMAKE_CURRENT_SOURCE_DIR}/Src/decision_v1.cpp")
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
    Src/parameter_config.cpp
    Src/candidate_scoring.cpp
)
target_link_libraries(character_dynamics_replay_core PRIVATE character_dynamics_legacy_replay_v0)
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

add_test(NAME research_dynamics_v1_unit
         COMMAND ${Python3_EXECUTABLE} -m unittest discover
                 -s "${CMAKE_CURRENT_SOURCE_DIR}/../02_实验/ResearchDynamicsV1"
                 -p "test_*.py")
add_test(NAME research_dynamics_v1_intervention_artifacts
         COMMAND ${Python3_EXECUTABLE}
                 "${CMAKE_CURRENT_SOURCE_DIR}/../02_实验/ResearchDynamicsV1/run_interventions.py")
