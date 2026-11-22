"""Container entry point; reuse the existing API and static web application."""
import sys

from web_app import main


if __name__ == '__main__':
    main(['--host', '0.0.0.0', '--no-browser', *sys.argv[1:]])
