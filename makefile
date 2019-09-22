.PHONY: clean test publish package

inc-build:
	zlx inc-build ebfe/__init__.py

test:
	PYTHONPATH=. python3 ebfe/cmd_line.py -t

clean:
	-rm -rf build dist ebfe.egg-info

package: clean
	python3 setup.py sdist bdist_wheel


publish: package
	twine upload dist/*
