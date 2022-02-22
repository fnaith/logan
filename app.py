import os.path
import yaml
import glob
import tailer
import grin
import re
import uuid
from flask import Flask, render_template
from flask import request, session
from flask import make_response

"""
    Logan log file viewer

    Simple log service agent to provide tailing (tailer) and
    grep (grin) services over REST

    FIXME: No results found for expression

    :copyright: (c) 2012 by Jonathan Holloway.
    :license: BSD-2, see LICENSE_FILE for more details.
"""
app = Flask(__name__)
app.secret_key = str(uuid.uuid1())

configurationfile = 'logagentconfig.yaml'

def init():
  """Init configuration"""
  configfile = open(configurationfile, 'r', encoding='utf-8', errors='ignore')
  config = {}
  try:
    config = yaml.full_load(configfile)
    for item in config:
      print('%s: %s' % (item, str(config[item])))
  finally:
    configfile.close()
  return config

config = init()

def link(href, text):
  """Generate a link"""
  return '<a href="%s">%s</a>' % (href, text)

def process_path(validfiles, path):
  """Process a given filesystem path and add the valid files to list"""
  hindex = path.rfind('/')
  filename = path[hindex + 1:]

  # Generate URLs
  if os.path.getsize(path) > 0:
    size = str(os.path.getsize(path))
    uniquefilename = '%s_%s' % (filename, str(uuid.uuid1()))
    validfiles[uniquefilename] = [path, size]

def process_file(fn, filename, numlines):
  """Process a file using a given function and a set of arguments"""
  validfiles = session.get('validfiles')
  if filename in validfiles:
    logpath = validfiles[filename][0]

    try:
      logfile = open(logpath, 'r', encoding='utf-8', errors='ignore')
      # pass generic function name
      lines = fn(logfile, numlines)
      content = '<br>'.join(lines)
      return render_template('content.html', content=content)
    finally:
      logfile.close()
  else:
    resp = make_response(render_template('content.html'), 200)
    session['content'] = 'Refusing to process file'
    return resp

def has_config(conf, field):
  return field in conf and conf[field]

def cast_int(v, default):
  try:
    return int(v)
  except ValueError:
    return default

def search_for_expression(output, filepaths, validfiles, expression, grepbefore, grepafter):
  """Carry out search for expression (using grep context) on validfiles returning matching files as output"""
  options = grin.Options()
  options['before_context'] = cast_int(grepbefore, config['searchbeforecontext'])
  options['after_context'] = cast_int(grepafter, config['searchaftercontext'])
  options['use_color'] = False
  options['show_filename'] = False
  options['show_match'] = True
  options['show_emacs'] = False
  options['show_line_numbers'] = True

  anchorcount = 1

  searchregexp = re.compile(expression)
  grindef = grin.GrepText(searchregexp, options)

  for file in validfiles:
    filepath = validfiles.get(file)[0]
    report = grindef.grep_a_file(filepath)
    if report:
      output += '<a name="filename%d"></a><h2>%s</h2>' % (anchorcount, filepath)

      filepaths.append(filepath)
      reporttext = report.split("\n")
      for text in reporttext:
        if text:
          output += 'line%s<br>' % (text)
      anchorcount += 1

  return output

@app.route('/')
def index():
  """Route: index page"""
  return list_files()

@app.route('/list/')
def list_files():
  """Route: List all files based on directory and extension"""
  # Only allow tail/grep on files in the directory
  validfiles = {}

  # Filter log files for dirs specified in the config
  if has_config(config, 'directories'):
    for dir_path in config['directories']:
      if has_config(config, 'extensions'):
        for ext in config['extensions']:
          # Glob for all files matching the ones specified in the conig
          paths = glob.glob('%s/*.%s' % (dir_path, ext))
          for path in paths:
            path = path.replace("\\","/")
            process_path(validfiles, path)

  # Filter log files for files explicitly specified in the config
  if has_config(config, 'logfiles'):
    for file in config['logfiles']:
      process_path(validfiles, file)

  # Filter log files for globs specified in the config
  if has_config(config, 'logfile_glob'):
    for item in config['logfile_glob']:
      filelist = glob.glob(item)
      for file in filelist:
        process_path(validfiles, file)

  session['grepnumlines'] = str(config['grepnumlines'])
  session['searchbeforecontext'] = str(config['searchbeforecontext'])
  session['searchaftercontext'] = str(config['searchaftercontext'])
  session['validfiles'] = validfiles
  return render_template('list.html')

@app.route('/tail/<filename>/<numlines>/')
def tail(filename, numlines=config['tailnumlines']):
  """Route: tail the contents of a file given the numlines"""
  return process_file(tailer.tail, filename, cast_int(numlines, config['tailnumlines']))

@app.route('/head/<filename>/<numlines>/')
def head(filename, numlines=config['headnumlines']):
  """Route: head the contents of a file given the numlines"""
  return process_file(tailer.head, filename, cast_int(numlines, config['headnumlines']))

# TODO: Fix bad GET request
@app.route('/grep/', methods=['GET', 'POST'])
def grep():
  """Search through a file looking for a matching phrase"""

  # Validate the form inputs
  if not request or not request.form:
    return render_template('list.html', error='no search expression specified')

  if 'expression' not in request.form or len(request.form['expression']) == 0:
    return render_template('list.html', error='no search expression specified')

  expression = request.form['expression'].strip()
  output = ''
  filepaths = []

  output += search_for_expression(output, filepaths, session.get('validfiles'), expression, request.form['grepbefore'], request.form['grepafter'])

  if not output:
    return render_template('list.html', error='No results found for search expression')

  highlight = r'<span class="highlightmatch">\g<0></span>'
  searchregexp = re.compile(expression)
  highlightedoutput = searchregexp.sub(highlight, output)

  return render_template('results.html', output=highlightedoutput, filepaths=filepaths, expression=expression)

if __name__ == '__main__':
  app.run()
