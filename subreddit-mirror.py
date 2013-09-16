from flask import Flask, render_template, g
from config import initialize_config
import pypyodbc
import os

app = Flask(__name__)


def init_app():
    initialize_config()
    connect_db()


def connect_db():
    """


    :return: Connection
    """
    conn = pypyodbc.connect(driver='{SQL Server}', server=os.environ['DBSERVER'], database=os.environ['DBNAME'], uid=os.environ['DBUSER'], pwd=os.environ['DBPASS'])
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
    rows = cur.execute("select image_id, display_order from images order by display_order").fetchall()
    update_date = cur.execute("select max(created_date) from images").fetchone()[0]
    cur.close()
    images = [r['image_id']  for r in rows]
    print update_date
    template_params = {
        'images': images,
        'update_date': update_date,
        'image_root': "https://s3.amazonaws.com/{0}/".format(os.environ["S3BUCKETNAME"])
        }
    return render_template('index.html', **template_params)

if __name__ == '__main__':
    init_app()
    app.run(debug = True)