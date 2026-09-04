cmake_minimum_required(VERSION 3.20)

project(CharacterDynamicsReference LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_executable(character_dynamics_reference
    Src/main.cpp
    Src/action.cpp
    Src/world.cpp
    Src/observation.cpp
    Src/appraisal.cpp
    Src/state.cpp
    Src/decision.cpp
    Src/simulation.cpp
)

target_include_directories(character_dynamics_reference PRIVATE Inc)

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
