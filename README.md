Logan Log Viewer
================

![Logan Screenshot](https://raw.githubusercontent.com/jph98/logan/master/logan.png)

Logan is a web based interface real-time log viewer/searcher.

Built upon:
* Python 3.6
* Flask (Provides a simple web interface) - http://flask.pocoo.org/
* Pytailer (tail comamnd wrapper) - http://code.google.com/p/pytailer/
* Grin (grep command wrapper) - http://pypi.python.org/pypi/grin

Installation
------------

Install dependencies with:

    sudo pip install -r .\requirements.txt

Then run:

    sh ./start.sh

Then run:

    sh ./stop.sh

Configuration
-------------

Look at logagentconfig.yaml:

Specifies the number of lines to display maximum:

    grepnumlines: 300

Specifies the number of lines before/after the match to display:

    searchbeforecontext: 5
    searchaftercontext: 5

Specifies the number of lines for tail/head on files:

    tailnumlines: 200
    headnumlines: 200

Specifies the valid extensions for files found in 'directories':

    extensions:
     - log
     - out

To configure the directories to view/search within:

    directories:
     - /var/log
     - /Users/jonathan/temp

TODO
----

* fix no results found for expression
* fix bad GET /grep request
* replace grin to display utf-8 file
* only search matched files
