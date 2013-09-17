from flask import Flask, render_template, g
from config import initialize_config
import psycopg2
import os
import re

app = Flask(__name__)


def init_app():
    initialize_config()
    connect_db()


def connect_db():
    """


    :return: Connection
    """
    conn = psycopg2.connect(host=os.environ['DBSERVER'], database=os.environ['DBNAME'], user=os.environ['DBUSER'], password=os.environ['DBPASS'], port=os.environ['DBPORT'])
    return conn

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db_conn'):
        g.db_conn.close()


def get_db():
    """


    :return: Connection
    """
    if not hasattr(g, 'db_conn'):
        g.db_conn = connect_db()
    return g.db_conn


@app.route('/')
def index():
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("select image_id, display_order from images order by display_order")
    rows = cur.fetchall()
    cur.execute("select max(created_date) from images")
    update_date = cur.fetchone()[0]
    cur.close()
    image_extension_regex = re.compile("\.(jpe?g|gif|png)$", re.IGNORECASE)
    images = [{'thumb': re.sub(image_extension_regex, r't.\1', r[0]), 'img': r[0]} for r in rows]
    template_params = {
        'images': images,
        'update_date': update_date,
        'image_root': "https://s3.amazonaws.com/{0}/".format(os.environ["S3BUCKETNAME"])
        }
    return render_template('index.html', **template_params)

if __name__ == '__main__':
    init_app()
    app.run(debug = True)