import os.path
import re
from collections import deque
from glob import glob
from io import StringIO
from uuid import uuid1
from yaml import full_load

import tailer
from flask import Flask, render_template
from flask import request, session
from flask import make_response

"""
    Logan log file viewer

    Simple log service agent to provide tailing (tailer) and

    FIXME: No results found for expression

    :copyright: (c) 2012 by Jonathan Holloway.
    :license: BSD-2, see LICENSE_FILE for more details.
"""
app = Flask(__name__)
app.secret_key = str(uuid1())

configurationfile = 'logagentconfig.yaml'

def init():
  """Init configuration"""
  configfile = open(configurationfile, 'r', encoding='utf-8', errors='ignore')
  config = {}
  try:
    config = full_load(configfile)
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
    uniquefilename = '%s_%s' % (filename, str(uuid1()))
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

def get_config(conf, field, default):
  return default if not (field in conf and conf[field]) else conf[field]

def cast_int(v, default):
  try:
    return int(v)
  except ValueError:
    return default

def search_for_expression(filepaths, validfiles, expression, grepbefore, grepafter, logfileexpression):
  """Carry out search for expression (using grep context) on validfiles returning matching files as output"""
  before_context = cast_int(grepbefore, config['searchbeforecontext'])
  after_context = cast_int(grepafter, config['searchaftercontext'])

  anchorcount = 1
  searchregexp = re.compile(expression)
  logfileregexp = re.compile(logfileexpression)
  highlight = r'<span class="highlightmatch">\g<0></span>'
  sb = StringIO()

  for file in validfiles:
    filepath = validfiles.get(file)[0]
    if logfileexpression and not re.search(logfileregexp, filepath):
      continue
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
      q = deque(maxlen=max(before_context, after_context))
      lines = []
      line_no = 0
      last_matched_line_no = 0
      for line in f:
        line_no += 1
        if line and '\n' == line[-1]:
          line = line[:-1]
        if re.search(searchregexp, line):
          if 0 < last_matched_line_no and line_no - 1 <= last_matched_line_no + after_context:
            size = line_no - 1 - last_matched_line_no
            for i in range(size):
              lines.append('line %d + %s<br>' % (last_matched_line_no + i + 1, q[-(size - i)]))
            q.clear()
          else:
            size = min(before_context, len(q))
            for i in range(size):
              lines.append('line %d - %s<br>' % (line_no - size + i, q[-(size - i)]))
            q.clear()
          lines.append('line %d : %s<br>' % (line_no, searchregexp.sub(highlight, line)))
          last_matched_line_no = line_no
        else:
          q.append(line)
          if 0 < last_matched_line_no and last_matched_line_no + after_context == line_no:
            for i in range(after_context):
              lines.append('line %d + %s<br>' % (last_matched_line_no + i + 1, q[-(after_context - i)]))
            q.clear()
      if 0 < last_matched_line_no and q and line_no - 1 <= last_matched_line_no + after_context:
        for i in range(len(q)):
          lines.append('line %d + %s<br>' % (last_matched_line_no + i + 1, q[i]))
        q.clear()
      if lines:
        sb.write('<a name="filename%d"></a><h2>%s</h2>' % (anchorcount, filepath))
        filepaths.append(filepath)
        for line in lines:
          sb.write(line)
    anchorcount += 1

  return sb.getvalue()

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
  for dir_path in get_config(config, 'directories', []):
    for ext in get_config(config, 'extensions', []):
      # Glob for all files matching the ones specified in the conig
      paths = glob('%s/*.%s' % (dir_path, ext))
      for path in paths:
        path = path.replace('\\', '/')
        process_path(validfiles, path)

  # Filter log files for files explicitly specified in the config
  for file in get_config(config, 'logfiles', []):
    process_path(validfiles, file)

  # Filter log files for globs specified in the config
  for item in get_config(config, 'logfile_glob', []):
    filelist = glob(item)
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
  logfileexpression = request.form['logfileexpression'].strip()
  filepaths = []

  output = search_for_expression(filepaths, session.get('validfiles'), expression, request.form['grepbefore'], request.form['grepafter'], logfileexpression)

  if not output:
    return render_template('list.html', error='No results found for search expression')

  return render_template('results.html', output=output, filepaths=filepaths, expression=expression)

if __name__ == '__main__':
  app.run()
