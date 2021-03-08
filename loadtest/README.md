# Loadtesting

This is a simple tool that can be used to test the site locally or otherwise.

Run `poetry install` to install, and then call `main.py --help` for usage
instructions

You probably want to run the server via gunicorn when using this

# Locust

A better load testing tool is locust, which can be run with

```
locust -f locustfile.py
```
