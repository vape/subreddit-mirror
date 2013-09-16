import os
import yaml


def initialize_config(file_name='env.yaml'):
    if [k for k in ['S3KEY', 'S3SECRET', 'S3BUCKETNAME', 'IMGURCLIENTID', 'IMGURSECRET', 'DBSERVER', 'DBNAME', 'DBUSER', 'DBPASS', 'DBPORT'] if k in os.environ.keys()]:
        return

    if not os.path.exists('env.yaml'):
        raise Exception('env.yaml required for config initialization')

    with open(file_name, 'r') as config_file:
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