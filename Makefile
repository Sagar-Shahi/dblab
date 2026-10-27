.PHONY: test python java cpp clean shell

test: python java cpp

python:
	cd python && python3 -m unittest discover -s tests -t . -v

java:
	$(MAKE) -C java test

cpp:
	$(MAKE) -C cpp test

shell:
	cd python && python3 -m dblab

clean:
	$(MAKE) -C java clean
	$(MAKE) -C cpp clean
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
