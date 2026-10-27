CXX      ?= g++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -Wpedantic -O2

.PHONY: test clean

test: build/tests
	./build/tests

build/tests: tests.cpp hash_ring.hpp lru_cache.hpp
	mkdir -p build
	$(CXX) $(CXXFLAGS) -o $@ tests.cpp

clean:
	rm -rf build
