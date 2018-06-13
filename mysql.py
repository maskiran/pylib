#! /usr/bin/python

import MySQLdb


class Db(object):
    """Basic Mysql class to operate with the mysql database"""

    def __init__(self, host="", user="", passwd="", db=""):
        self._host = host
        self._user = user
        self._passwd = passwd
        self._db = db
        self._connection = None
        self._cursor = None

    def _connect(self):
        """Connect to the database. This method is called automatically
        if no connection is made to the database."""

        if not self._host:
            raise Exception('Server host not defined')
        self._connection = MySQLdb.connect(
            host=self._host,
            user=self._user,
            passwd=self._passwd,
            db=self._db)
        self._cursor = self._connection.cursor(MySQLdb.cursors.DictCursor)
        # backward compatibility
        self.enable_auto_commit()

    def query(self, string):
        """Execute the given string as query on the database"""

        # if the connection to database is not done, connect now
        if not self._connection:
            self._connect()

        try:
            self._cursor.execute(string)
        except MySQLdb.OperationalError:
            self._connect()
            self._cursor.execute(string)

        return self._cursor.rowcount

    def get_row(self):
        """Returns one row from a previous query. The row
        returned is a dict with column names as the keys"""
        return self._cursor.fetchone()

    def get_all_rows(self):
        """Returns all the rows from a previous query as list of dicts.
        The keys in the dict are the column names"""
        return list(self._cursor.fetchall())

    def get_insert_id(self):
        """Returns the auto_increment id of the last query, if any"""
        return self._cursor.lastrowid

    def close(self):
        """Close the database connection"""
        self._connection.close()

    def commit(self):
        self._connection.commit()

    def rollback(self):
        self._connection.rollback()

    def enable_auto_commit(self):
        self.query("set autocommit=1")

    def disable_auto_commit(self):
        self.query("set autocommit=0")
