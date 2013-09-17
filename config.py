import os
import yaml
import argparse


def initialize_config(config_file_name='env.yaml', argv=None):
    if [k for k in ['S3KEY', 'S3SECRET', 'S3BUCKETNAME', 'IMGURCLIENTID', 'IMGURSECRET', 'DBSERVER', 'DBNAME', 'DBUSER', 'DBPASS', 'DBPORT'] if k in os.environ.keys()]:
        return

    config_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_file_name)

    if not os.path.exists(config_file_path):
        raise Exception('env.yaml required for config initialization')

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true', dest='debug_mode')
    arguments = parser.parse_args()

    if arguments.debug_mode:
        os.environ['DEBUG'] = "True"

    with open(config_file_path, 'r') as config_file:
        config = yaml.load(config_file)
        os.environ['S3KEY'] = config['s3config']['key']
        os.environ['S3SECRET'] = config['s3config']['secret']
        os.environ['S3BUCKETNAME'] = config['s3config']['bucketname']

        os.environ['IMGURCLIENTID'] = config['imgurconfig']['clientid']
        os.environ['IMGURSECRET'] = config['imgurconfig']['secret']

        os.environ['DBSERVER'] = config['dbconfig']['dbserver']
        os.environ['DBNAME'] = config['dbconfig']['dbname']
        os.environ['DBUSER'] = config['dbconfig']['username']
        os.environ['DBPASS'] = config['dbconfig']['password']
        os.environ['DBPORT'] = str(config['dbconfig']['port'])