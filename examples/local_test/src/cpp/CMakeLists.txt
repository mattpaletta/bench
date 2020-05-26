project(merge)
cmake_minimum_required(VERSION 3.5)

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(merge merge.cpp)
if (NOT APPLE)
    target_link_libraries(merge -static -pthread -Wl,--whole-archive -lpthread -Wl,--no-whole-archive)
    target_link_libraries(merge pthread)
endif()
