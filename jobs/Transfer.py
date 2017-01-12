# pylint: disable=C0103
# pylint: disable=C0111
# pylint: disable=C0301
import os, sys, json
from datetime import datetime, timedelta
from shutil import copy, rmtree
import time
from uuid import uuid4
from globusonline.transfer import api_client
from globusonline.transfer.api_client import Transfer as globus_transfer
from globusonline.transfer.api_client import TransferAPIClient
from globusonline.transfer.api_client import TransferAPIError
from globusonline.transfer.api_client import x509_proxy
from globusonline.transfer.api_client.goauth import get_access_token
from util import print_debug
from util import print_message
from util import filename_to_year_set
from pprint import pformat
from subprocess import Popen, PIPE
import threading


class Transfer(object):
    """
    Uses Globus to transfer files between DTNs
    """
    def __init__(self, config=None):
        self.config = {}
        self.status = 'unvalidated'
        self.type = 'transfer'
        self.outputs = {
            "status": self.status
        }
        self.uuid = uuid4().hex
        self.inputs = {
            'file_list': '',
            'recursive': '',
            'globus_username': '',
            'globus_password': '',
            'source_endpoint': '',
            'destination_endpoint': '',
            'source_username': '',
            'source_password': '',
            'destination_username': '',
            'destination_password': '',
            'source_path': '',
            'destination_path': '',
            'final_destination_path': '',
            'pattern': '',
            'frequency': ''
        }
        self.maximum_transfers = 0
        self.prevalidate(config)
        self.msg = None
        self.thread_list = []
        self.kill_thread_event = threading.Event()

    def save(self, conf_path):
        """
        Saves job configuration to a json file at conf_path
        """
        try:
            with open(conf_path, 'r') as infile:
                config = json.load(infile)
            with open(conf_path, 'w') as outfile:
                config[self.uuid]['inputs'] = self.config
                config[self.uuid]['outputs'] = self.outputs
                config[self.uuid]['type'] = self.type
                json.dump(config, outfile, indent=4)
        except Exception as e:
            print_message('Error saving configuration file')
            print_debug(e)
            raise

    def get_type(self):
        """
        Returns job type
        """
        return self.type

    def get_file_list(self):
        return self.inputs.get('file_list')

    def __str__(self):
        return pformat({
            'config': self.config,
            'status': self.status
        }, indent=4)

    def prevalidate(self, config=None):
        """
        Validates transfer inputs
        """
        if self.status == 'valid':
            return 0
        for i in config:
            if i not in self.inputs:
                print_message("Unexpected arguement: {}, {}".format(i, config[i]))
            else:
                if i == 'recursive':
                    if config.get(i) == 'True':
                        self.config[i] = True
                    else:
                        self.config[i] = False
                else:
                    self.config[i] = config.get(i)

        for i in self.inputs:
            if i not in self.config or self.config[i] == None:
                if i == 'file_list':
                    self.config[i] = ''
                elif i == 'recursive':
                    self.config[i] = False
                else:
                    print_message('Missing transfer argument {}'.format(i))
                    self.status = 'invalid'
                    return -1
        self.status = 'valid'
        # the maximum number of files to transfer at one time, set to a single year_set assuming 12 files per year
        self.maximum_transfers = self.config.get('frequency') * 12
        return 0

    def postvalidate(self):
        print 'transfer postvalidate'

    def activate_endpoint(self, api_client, endpoint, username, password):
        code, reason, result = api_client.endpoint_autoactivate(endpoint, if_expires_in=2880)
        if result["code"] == "AutoActivationFailed":
            reqs = result
            myproxy_hostname = None
            for r in result['DATA']:
                if r['type'] == 'myproxy' and r['name'] == 'hostname':
                    myproxy_hostname = r['value']
            reqs.set_requirement_value("myproxy", "hostname", myproxy_hostname)
            reqs.set_requirement_value("myproxy", "username", username)
            reqs.set_requirement_value("myproxy", "passphrase", password)
            reqs.set_requirement_value("myproxy", "lifetime_in_hours", "168")
            try:
                code, reason, result = api_client.endpoint_activate(endpoint, reqs)
            except:
                raise
            if code != 200:
                msg = "Could not activate the endpoint: %s. Error: %s - %s" % (endpoint, result["code"], result["message"])
                print msg

    def get_destination_path(self, srcpath, dstpath, recursive):
        '''
        If destination path is a directory (ends with '/') adds source file name to the destination path.
        Otherwise, Globus will treat the destination path as a file in spite of the fact that it is a directory.
        '''
        if srcpath:
            if not recursive:
                if dstpath.endswith('/'):
                    basename = os.path.basename(srcpath)
                    return dstpath + basename
        return dstpath

    def move_file_locally(self, file_name):
        """
        After the files have been moved from the remote host, they need to be moved
        out of their temprary directory to their final destination. This should be run from
        its own thread to not stop the rest of the program
        """
        print_message('MOVING FILE {0}'.format(file_name))
        # check that a folder for this year set exists, if not make one
        new_path = self.config.get('final_destination_path')
        if not os.path.exists(new_path):
            os.mkdir(new_path)

        src = os.path.join(self.config.get('destination_path'), file_name)
        # copy the file to the final destination
        try:
            copy(src=src, dst=new_path)
        except Exception as e:
            print_debug(e)
            print_message('Error moving file from {src} to {dst}'.format(src=src, dst=new_path))
        # remove the old files
        try:
            os.remove(src)
        except Exception as e:
            print_debug(e)
            print_message('Error removing file {0}'.format(src))


    def execute(self):
        if self.status != 'valid':
            print_message('--- Transfer job in invalid state ---')
            print_message(str(self))
            return
        print_message('Starting transfer job from {src} to {dst}'.format(
            src=self.config.get('source_endpoint'),
            dst=self.config.get('destination_endpoint')
        ), 'ok')
        # Map legacy endpoint names to UUIDs
        srcendpoint = self.config.get('source_endpoint')
        dstendpoint = self.config.get('destination_endpoint')

        # Get access token (This method of getting an acces token is deprecated and should be replaced by OAuth2 calls).
        globus_username = self.config.get('globus_username')
        globus_password = self.config.get('globus_password')
        auth_result = get_access_token(globus_username, globus_password)

        # Create a transfer submission
        successful_activation = False
        for i in range(5):
            api_client = TransferAPIClient(globus_username, goauth=auth_result.token)
            source_user = self.config.get('source_username')
            source_pass = self.config.get('source_password')
            try:
                self.activate_endpoint(api_client, srcendpoint, source_user, source_pass)
            except Exception as e:
                print_debug(e)
                print_message('Error activating source endpoing')
            else:
                successful_activation = True
                break
        if not successful_activation:
            print_message('Unable to activate source endpoint after five attempts, exiting')
            self.status = 'error'
            return

        successful_activation = False
        for i in range(5):
            dst_user = self.config.get('destination_username')
            dst_pass = self.config.get('destination_password')
            try:
                self.activate_endpoint(api_client, dstendpoint, dst_user, dst_pass)
            except Exception as e:
                print_debug(e)
                print_message('Error activating destination endpoint')
            else:
                successful_activation = True
                break
        if not successful_activation:
            print_message('Unable to activate destination endpoint after five attempts, exiting')
            self.status = 'error'
            return

        try:
            code, message, data = api_client.transfer_submission_id()
            submission_id = data["value"]
            deadline = datetime.utcnow() + timedelta(days=10)
            transfer_task = globus_transfer(submission_id, srcendpoint, dstendpoint, deadline)
        except Exception as e:
            print_debug(e)
            print_message('Error creating transfer task')
            self.status = 'error'
            return

        # only add the first n transfers up to the max
        source_list = self.config.get('file_list')[:self.maximum_transfers]
        if not source_list:
            print_message('Unable to transfer files without a source list')
            self.status = 'error'
            return
        try:
            for path in source_list:
                dst_path = self.get_destination_path(
                    path,
                    self.config.get('destination_path'),
                    self.config.get('recursive'))
                transfer_task.add_item(
                    path,
                    dst_path,
                    recursive=self.config.get('recursive'))
        except IOError as e:
            print_debug(e)
            print_message('Error opening source list')
            self.status = 'error: cannot open source list'
            return

        # Start the transfer
        task_id = None
        try:
            code, reason, data = api_client.transfer(transfer_task)
            task_id = data["task_id"]
            print 'task_id %s' % task_id
        except Exception as e:
            print_message("Could not submit the transfer. Error: %s" % str(e))
            print_debug(e)
            self.status = 'error'
            return

        # Check a status of the transfer every minute (60 secs)
        number_transfered = 0
        files_transferred = []
        while True:
            code, reason, data = api_client.task(task_id)
            print_message('transfer status: {}'.format(data['status']))
            # if the transfer is done, move any files that havent already been 
            # moved to their final destination
            if data['status'] == 'SUCCEEDED':
                print_message('progress %d/%d' % (data['files_transferred'], data['files']), 'ok')
                # if data['files_transferred'] > number_transfered:
                #     directory_contents = os.listdir(self.config.get('destination_path'))
                #     for f in directory_contents:
                #         if f in self.config.get('file_list') and f not in files_transferred:
                #             files_transferred.append(f)
                #             number_transfered = data['files_transferred']
                #             self.move_file_locally(file_name=f)

                self.status = 'complete'
                return ('success', '')
            elif data['status'] == 'FAILED':
                self.status = 'error: ' + data.get('nice_status_details')
                return ('error', data['nice_status_details'])

            elif data['status'] == 'ACTIVE':
                print_message('progress %d/%d' % (data['files_transferred'], data['files']), 'ok')
                # if data['files_transferred'] > number_transfered:
                #     directory_contents = os.listdir(self.config.get('destination_path'))
                #     for f in directory_contents:
                #         if f in self.config.get('file_list') and f not in files_transferred:
                #             files_transferred.append(f)
                #             number_transfered = data['files_transferred']
                #             thread = threading.Thread(target=self.move_file_locally, args=(f))
                #             thread.start()
            time.sleep(10)
