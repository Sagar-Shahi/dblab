.PHONY: test clean

test: build/.compiled
	java -cp build dblab.Tests

build/.compiled: $(wildcard src/dblab/*.java)
	mkdir -p build
	javac -Xlint:all -d build src/dblab/*.java
	touch $@

clean:
	rm -rf build
