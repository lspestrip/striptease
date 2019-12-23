#!/bin/bash

git stash && \
	git checkout master && \
	(cd docs && make html) && \
	rm -rf *.html *.inv *.js _static/ _modules/ _images/ _sources/ && \
	cp -prf ./docs/_build/html/* . && \
	git commit -a -m "Update the documentation" && \
	git push origin gh-pages && \
	git stash pop

