import os
import csv
import datetime
import sqlite3
import webbrowser
import traceback
import dcm_util, dcm_issue

#
# Repository kinds
class ResourceKind:
  DOC = 'doc'
  BOOKMARK = 'url'
  IGNORE = 'ignore'

#
# Repository (DB/directory) Manager
class RepoManager:
  COLS_TYPE = 'kind TEXT, url TEXT, title TEXT, date_start TEXT, author TEXT, lang TEXT, labels TEXT, keywords TEXT, favorite TEXT'
  COLS_WRITE = 'kind, url, title, date_start, author, lang, labels, keywords, favorite'
  COLS_SHOW_ALL = 'kind, substr(url, 1, 30) as url30, substr(title, 1, 30) as title30, date_start, author, lang, labels, favorite, rowid'
  #COLS_DEF_SHOWN = 'kind, substr(title, 1, 30) as title30, date_start, labels, rowid'
  COLS_DEF_SHOWN = 'kind, substr(title, 1, 30) as title30, date_start, labels, substr(url, 1, 20) as url20, rowid'
  INTERNAL_HTML_INDEX_FILENAME = '!!!index.html' #MTB [15/02/2018]

  COL_WRITE_URL = 1
  COL_WRITE_LABELS = 6

  def __init__(self, repo_user, repo_csv_path, repo_dir_path):
    self.repo_user = repo_user                 # user repository
    self.repo_csv_path = repo_csv_path         # csv file path
    self.repo_dir_path = repo_dir_path         # repository directory path 

    self.issues = []                           # scan issues
    self.labels = []                           # repo labels
    self.filtered = []                         # filtered repo entries

    self.where_clause = ''                     # active SQL where clause
    self.set_def_filter()

    self.orderby_clause = ' ORDER BY title30'  # active SQL order by clause
    
    self.active_sql_cols = self.COLS_DEF_SHOWN # sql columns
    self.active_cols = []                      # column names

    # sqlite
    self.db_conn = sqlite3.connect(':memory:') #sqlite3.connect('a.db')

  #
  # open the csv file and convert it to a sqlite db
  def open(self):
    tableCreated = False
    with open(self.repo_csv_path, newline='') as csvfile:
      reader = csv.reader(csvfile, delimiter=';', quotechar='|')
      for row in reader:
        if not tableCreated:
          self.db_conn.execute('CREATE TABLE resource (' + self.COLS_TYPE + ')')
          tableCreated = True
          continue

        # column 'labels' needs to be ordered
        ls = row[self.COL_WRITE_LABELS].split()
        ls.sort()
        row[self.COL_WRITE_LABELS] = ' '.join(ls)

        sql = 'INSERT INTO resource VALUES (%s)' % dcm_util.quote_list_as_str(row)
        self.db_conn.execute(sql)
    self.db_conn.commit()
    
    self.db_conn.execute('PRAGMA case_sensitive_like=ON;') # default case sensitive on!

    self._update_labels()
    self.update_filtered()

  #
  # convert the the sqlite db to csv and close it
  def close(self):
    dcm_util.safe_copy(self.repo_csv_path, self.repo_csv_path + '.last')
    
    self.where_clause = ''
    self.orderby_clause = ''
    self._filter_save_csv(self.repo_csv_path)

    #MTB [15/02/2018]
    #self._save_html(self.repo_html_path)
    self._save_html(os.path.join(self.repo_dir_path, self.INTERNAL_HTML_INDEX_FILENAME))

    self.db_conn.close()

  #
  # Copy issues to filtered
  def copy_issues_to_filtered(self):
    del self.filtered[:]
    self.filtered.extend(self.issues)

  #
  # scan the repository directory for issues (new files, error...)
  def scan(self):
    del self.issues[:]
    db_values = dcm_util.select_db(self.db_conn, 'SELECT url, rowid FROM resource WHERE kind <> ' + dcm_util.quote_str(ResourceKind.BOOKMARK))
    db_fnames = [value[0] for value in db_values]
    db_rowids = [value[1] for value in db_values]
    for filename in dcm_util.find_all_files(self.repo_dir_path):
      if filename == self.INTERNAL_HTML_INDEX_FILENAME: # MTB [15/02/2018]: spostato il file di index internamente
        continue
      
      if not (filename in db_fnames):
        #filepath = os.path.join(self.repo_dir_path, filename)
        issue = dcm_issue.RepoIssue(dcm_issue.RepoIssueKind.NEW, filename, -1)
        self.issues.append(issue)
      else:
        i = db_fnames.index(filename)
        db_fnames.pop(i)
        db_rowids.pop(i)

    for i,filename in enumerate(db_fnames):
      issue = dcm_issue.RepoIssue(dcm_issue.RepoIssueKind.MISSING, filename, db_rowids[i])
      self.issues.append(issue)

  #
  # export elements to csv/html
  def export_to_csv_html(self, rowids, filepath, csvFlag):
    old_where_clause = self.where_clause

    self.set_def_filter()
    self.where_clause = self.where_clause + ' AND (1 = 0'
    for r in rowids:
      self.where_clause = self.where_clause + ' OR rowid = ' + str(r)
    self.where_clause = self.where_clause + ')'

    if csvFlag:
      self._filter_save_csv(filepath)
    else:
      self._save_html(filepath)
    
    self.where_clause = old_where_clause
    self.update_filtered(self.active_sql_cols)

  #
  # Add document to DB
  def add_doc_db(self, repo_issue, title, lang, labels, keywords):
    if repo_issue.kind != dcm_issue.RepoIssueKind.NEW: return False
    self._add_entry_db(ResourceKind.DOC, repo_issue.url, title, lang, labels, keywords, '')
    self.update_filtered()
    return True

  #
  # Add bookmark to DB
  def add_bookmark_db(self, url, title, lang, labels, keywords):
    rows = dcm_util.select1c_db(self.db_conn, 'SELECT rowid FROM resource WHERE kind = ' + dcm_util.quote_str(ResourceKind.BOOKMARK) + ' AND url = ' + dcm_util.quote_str(url))
    if len(rows) != 0:
      return False

    self._add_entry_db(ResourceKind.BOOKMARK, url, title, lang, labels, keywords, '')
    self.update_filtered()
    return True

  #
  # Ignore document
  def ignore_doc_db(self, repo_issue):
    if repo_issue.kind != dcm_issue.RepoIssueKind.NEW: return False
    self._add_entry_db(ResourceKind.IGNORE, repo_issue.url, '', '', '', '', '')
    return True

  #
  # Remove missing entry from DB
  def fix_missing_db(self, issue1, issue2):
    issue_new = None
    issue_missing = None
    if issue1.kind == dcm_issue.RepoIssueKind.NEW: issue_new = issue1
    if issue2.kind == dcm_issue.RepoIssueKind.NEW: issue_new = issue2
    if issue1.kind == dcm_issue.RepoIssueKind.MISSING: issue_missing = issue1
    if issue2.kind == dcm_issue.RepoIssueKind.MISSING: issue_missing = issue2
    
    if not issue_missing or not issue_new:
      return False

    self.db_conn.execute('UPDATE resource SET url = ' + dcm_util.quote_str(issue_new.url) + ' WHERE rowid = ' + str(issue_missing.rowid))
    self.db_conn.commit()
    self.update_filtered()
    return True

  #
  # Remove missing entry from DB
  def remove_missing_entry_db(self, repo_issue):
    if repo_issue.kind != dcm_issue.RepoIssueKind.MISSING: return False
    self.db_conn.execute('DELETE FROM resource WHERE url = ' + dcm_util.quote_str(repo_issue.url))
    self.db_conn.commit()
    self.update_filtered()
    return True

  #
  # Remove entry from DB and eventually delete the file
  def remove_entry_db_file(self, rowid):
    rows = dcm_util.select_db(self.db_conn, 'SELECT kind, url FROM resource WHERE rowid = ' + str(rowid))
    row = rows[0]
    if row[0] == ResourceKind.DOC:
      os.remove(os.path.join(self.repo_dir_path, row[1]))

    self.db_conn.execute('DELETE FROM resource WHERE rowid = ' + str(rowid))
    self.db_conn.commit()
    self.update_filtered()
    return True

  #
  # Remove label from DB
  def remove_label_db(self, label):
    self._fix_label_db(label, lambda ls: [l for l in ls if l != label])
    self._update_labels()
    self.update_filtered()
    return True

  #
  # Remove label from DB
  def rename_label_db(self, label, new_name):
    self._fix_label_db(label, lambda ls: [new_name if l == label else l for l in ls])
    self._update_labels()
    self.update_filtered()
    return True

  #
  # set default filter where clause
  def set_def_filter(self):
    self.where_clause = ' WHERE (kind <> ' + dcm_util.quote_str(ResourceKind.IGNORE) + ') '

  #
  # set AND|OR filter where clause
  def set_andor_filter(self, reset_filter, case_sensitive, kind, url, title, lang, labels, keywords, andFlag):
    if reset_filter:
      self.set_def_filter()

    if not andFlag:
      self.where_clause = self.where_clause + ' AND (1 = 0 ' # the 'and' is just there to fix the 'OR' sql syntax
    
    if andFlag or kind != '':
      self.where_clause = self.where_clause + dcm_util.get_sql_andor_quoted(case_sensitive, 'kind', kind, andFlag)
    
    if andFlag or url != '':
      self.where_clause = self.where_clause + dcm_util.get_sql_andor_quoted(case_sensitive, 'url', url, andFlag)

    if andFlag or title != '':
      self.where_clause = self.where_clause + dcm_util.get_sql_andor_quoted(case_sensitive, 'title', title, andFlag)

    if andFlag or lang != '':
      self.where_clause = self.where_clause + dcm_util.get_sql_andor_quoted(case_sensitive, 'lang', lang, andFlag)
    
    if andFlag or labels != '':
      self.where_clause = self.where_clause + dcm_util.get_sql_andor_quoted(case_sensitive, 'labels', labels, andFlag)
    
    if andFlag or keywords != '':
      self.where_clause = self.where_clause + dcm_util.get_sql_andor_quoted(case_sensitive, 'keywords', keywords, andFlag)
      
    if not andFlag:
      self.where_clause = self.where_clause + ')'

    self.update_filtered()

  #
  # set filter where clause
  def set_filter_favorite(self):
    self.set_def_filter()
    self.where_clause = self.where_clause + dcm_util.get_sql_andor_quoted(False, 'favorite', '*', True)
    self.update_filtered()

  #
  # update filtered
  def update_filtered(self, cols = ''):
    cur = self.db_conn.cursor()
    if cols == '':
      cols = self.active_sql_cols
    sql = 'SELECT ' + cols + ' FROM resource' + self.where_clause + self.orderby_clause
    cur.execute(sql)

    # sqlite column names
    del self.active_cols[:]
    self.active_cols.extend(list(map(lambda x: x[0], cur.description)))
    
    del self.filtered[:]
    self.filtered.extend(cur.fetchall())

  #
  # toggle label on repo entry (return True if the label is now present)
  def toggle_label(self, rowid, label):
    rows = dcm_util.select1c_db(self.db_conn, 'SELECT labels FROM resource WHERE rowid = ' + str(rowid))
    row_labels = rows[0]
    ls = row_labels.split()
    res = False
    if label in ls:
      ls = [l.strip() for l in ls if l != label]
    else:
      ls.append(label.strip())
      res = True
    self.db_conn.execute('UPDATE resource SET labels = ' + dcm_util.quote_str(' '.join(ls)) + ' WHERE rowid = ' + str(rowid))
    self.db_conn.commit()

    self._update_labels()
    self.update_filtered()
    return res

  #
  # toggle favorite on repo entry (return True if favorite is now on)
  def toggle_favorite(self, rowid):
    rows = dcm_util.select1c_db(self.db_conn, 'SELECT favorite FROM resource WHERE rowid = ' + str(rowid))
    row_favorite = rows[0]
    res = False
    if row_favorite == '':
      row_favorite = '*'
      res = True
    else:
      row_favorite = ''

    self.db_conn.execute('UPDATE resource SET favorite = ' + dcm_util.quote_str(row_favorite) + ' WHERE rowid = ' + str(rowid))
    self.db_conn.commit()

    self.update_filtered()
    return res

  #
  # get the rowid from a tuple element
  def get_rowid(self, t):
    return t[len(t) - 1] #rowid has to stay at the end

  #
  # open item with external viewer
  def open_item(self, rowid):
    rows = dcm_util.select_db(self.db_conn, 'SELECT kind, url FROM resource WHERE rowid = ' + str(rowid))
    row = rows[0]
    if row[0] == ResourceKind.BOOKMARK:
      webbrowser.open(row[1])
    else:
      os.startfile(os.path.join(self.repo_dir_path, row[1]))

  #
  # get item url
  def get_url(self, rowid):
    rows = dcm_util.select_db(self.db_conn, 'SELECT kind, url FROM resource WHERE rowid = ' + str(rowid))
    row = rows[0]
    return self._convert_url(row[0], row[1], True, True, False)

  #
  # get kind
  def get_kind(self, rowid):
    rows = dcm_util.select1c_db(self.db_conn, 'SELECT kind FROM resource WHERE rowid = ' + str(rowid))
    return rows[0]

  #
  # get title
  def get_title(self, rowid):
    rows = dcm_util.select1c_db(self.db_conn, 'SELECT title FROM resource WHERE rowid = ' + str(rowid))
    return rows[0]

  #
  # get item url
  def change_title(self, rowid, title):
    self.db_conn.execute('UPDATE resource SET title = ' + dcm_util.quote_str(title) + ' WHERE rowid = ' + str(rowid))
    self.db_conn.commit()

    self.update_filtered()

  #
  # print extra info on item
  def print_extra_info(self, rowid):
    cur = self.db_conn.cursor()
    cur.execute('SELECT ' + self.COLS_WRITE + ' FROM resource WHERE rowid = ' + str(rowid))

    fields = list(map(lambda x: x[0], cur.description))
    values = cur.fetchone()
    fvs = zip(fields, values)
    for fv in fvs:
      print(fv[0] + ': ' + fv[1])

    myurl = self.get_url(rowid)
    mykind = self.get_kind(rowid)
    if mykind == ResourceKind.DOC:
      try:
        st = os.stat(os.path.join(self.repo_dir_path, myurl))
        print('filepath: ' + myurl)
        print('size: ' + "{:,}".format(st.st_size))
      except Exception as ex:
        traceback.print_exc()
    print()

  #
  # search a string (s) inside the currently filtered documents
  def search_string(self, s, case_insesitve):
    to_be_removed = []
    for row in self.filtered:
      rowid = self.get_rowid(row)
      url = self.get_url(rowid)
      kind = self.get_kind(rowid)

      to_be_removed.append(row)
      if self.get_kind(rowid) == ResourceKind.DOC and dcm_util.search_string_in_file(url, s, case_insesitve):
        to_be_removed.remove(row)
    
    for row in to_be_removed:
      self.filtered.remove(row)

  #
  # -------------  PRIVATE
  #

  #
  # convert a url to relative or absolute path if needed
  def _convert_url(self, kind, url, joinRepoDir, absFlag, forHTML):
    if kind == ResourceKind.BOOKMARK:
      return url
    else:
      if joinRepoDir: res = os.path.join(self.repo_dir_path, url)
      else: res = '.\\' + url
      if absFlag: res = os.path.abspath(res)
      #if forHTML: res = 'file://' + res.replace('\\', '/')
      if forHTML: res = res.replace('\\', '/')
      return res

  #
  # save filtered data to csv
  def _filter_save_csv(self, filepath):
    self.update_filtered(self.COLS_WRITE)
    with open(filepath, 'w', newline='') as csvfile:
      spamwriter = csv.writer(csvfile, delimiter=';', quotechar='|', quoting=csv.QUOTE_MINIMAL)
      spamwriter.writerow(self.COLS_WRITE.split(', '))
      for row in self.filtered:
        spamwriter.writerow(row)

  #
  # update labels list
  def _update_labels(self):
    rows = dcm_util.select1c_db(self.db_conn, 'SELECT DISTINCT(labels) FROM resource')
    del self.labels[:] #destroys the list not its pointer! ---> self.labels = []
    for ls in rows:
      for l in ls.split():
        if l in self.labels: continue
        self.labels.append(l)
    self.labels.sort()

  #
  # Add entry in DB
  def _add_entry_db(self, kind, url, title, lang, labels, keywords, favorite):
    date = datetime.date.today().strftime('%d/%m/%Y')
    row = [kind, url, title, date, self.repo_user, lang, labels, keywords, favorite]
    sql = 'INSERT INTO resource VALUES (%s)' % dcm_util.quote_list_as_str(row)
    self.db_conn.execute(sql)
    self.db_conn.commit()

  #
  # Search labels and fix them with a function (f :: [labels] -> [labels])
  def _fix_label_db(self, label, f):
    rows = dcm_util.select_db(self.db_conn, 'SELECT rowid, labels FROM resource WHERE labels LIKE ' + dcm_util.quote_str('%' + label + '%'))
    for row in rows:
      ls = row[1].split()
      ls = f(ls)
      self.db_conn.execute('UPDATE resource SET labels = ' + dcm_util.quote_str(' '.join(ls)) + ' WHERE rowid = ' + str(row[0]))
      self.db_conn.commit()
    self._update_labels()

  #
  # export elements to html
  def _save_html(self, filepath):
    html_template = '''
<html>
  <head>
    <style>
      <!--
#myInput {
    //background-image: url('/css/searchicon.png'); /* Add a search icon to input */
    background-position: 10px 12px; /* Position the search icon */
    background-repeat: no-repeat; /* Do not repeat the icon image */
    width: 100%; /* Full-width */
    font-size: 16px; /* Increase font-size */
    padding: 12px 20px 12px 40px; /* Add some padding */
    border: 1px solid #ddd; /* Add a grey border */
    margin-bottom: 12px; /* Add some space below the input */
}

#myTable {
    border-collapse: collapse; /* Collapse borders */
    width: 100%; /* Full-width */
    border: 1px solid #ddd; /* Add a grey border */
    font-size: 14px; /* Increase font-size */
}

#myTable th, #myTable td {
    text-align: left; /* Left-align text */
    padding: 12px; /* Add padding */
}

#myTable tr {
    /* Add a bottom border to all table rows */
    border-bottom: 1px solid #ddd;
}

#myTable tr.header, #myTable tr:hover {
    /* Add a grey background color to the table header and on hover */
    background-color: #f1f1f1;
}
      -->
    </style>

    <script>
      <!--
function myFunction() {
  var input, filter, table, tr, td, i;
  input = document.getElementById("myInput");
  filter = input.value.toUpperCase();
  table = document.getElementById("myTable");
  tr = table.getElementsByTagName("tr");

  // Loop through all table rows, and hide those who don't match the search query
  for (i = 0; i < tr.length; i++) 
  {
    // Loop through all table columns
    found = false;

    tds = tr[i].getElementsByTagName("td");
    for (j = 0; j < tds.length; j++) 
    {
      td = tds[j]; 
      if (!td) continue;
      
      if (td.innerHTML.toUpperCase().indexOf(filter) > -1)
      {
        found = true;
        break;
      }
    }

    if (found) tr[i].style.display = "";
    else tr[i].style.display = "none";
  }
}
      -->
    </script>
  </head>
  <body>
    <input type="text" id="myInput" onkeyup="myFunction()" placeholder="Search for names..">

%table%

  </body>
</html>
    '''
    
    # headers
    headers = '''
          <tr class="header">
            <th>kind</th>
            <th>title</th>
            <th>date_start</th>
            <th>author</th>
            <th>lang</th>
            <th>labels</th>
            <th>favorite</th>
          </tr>
    '''

    #--- routine to converte a DB row to HTML table row
    def _row_to_html(row):
      res = '        <tr>\n'
      res = res + '          <td>' + row[0] + '</td>\n'
      #res = res + '          <td><a href="' + self._convert_url(row[0], row[1], True, True) + '">' + row[2] + '</a></td>\n'
      res = res + '          <td><a href="' + self._convert_url(row[0], row[1], False, False, True) + '">' + row[2] + '</a></td>\n'
      res = res + '          <td>' + row[3] + '</td>\n'
      res = res + '          <td>' + row[4] + '</td>\n'
      res = res + '          <td>' + row[5] + '</td>\n'
      res = res + '          <td>' + row[6] + '</td>\n'
      # keywords: res = res + '          <td>' + row[7] + '</td>\n'
      res = res + '          <td>' + row[8] + '</td>\n'
      res = res + '        </tr>\n'
      return res
    #---

    # filter rows
    self.update_filtered(self.COLS_WRITE)
    
    # convert DB rows to HTML rows
    html_rows = list(map(lambda row: _row_to_html(row), self.filtered))

    # build html table
    table = '      <table id="myTable">\n' + headers
    for row in html_rows:
      table = table + row
    table = table + '      </table>\n'

    # write html file
    file_content = html_template.replace('%table%', table)
    with open(filepath, 'w') as f:
      f.write(file_content)
    f.close()
