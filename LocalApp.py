import os
import boto3
import sys
from boto import sqs
import time
from botocore.exceptions import ClientError
import boto
import boto.s3.connection
import math
import uuid


class Local_application:
    def __init__(self, output_file_name):
        self.outputName = output_file_name
        self.name = str(uuid.uuid4().hex)
        self.bucket_name = 'ass1-bucket-gn'
        self.sqs_names = ['Local-Manager-queue', 'Manager-local-queue']
        self.should_terminate = False
        self.sqs = boto3.resource(service_name='sqs')
        self.queue = boto.sqs.connect_to_region('us-east-1')
        self.ec2 = boto3.resource(service_name='ec2')
        self.conn = boto.connect_ec2()
        self.s3 = boto3.client(service_name='s3')
        self.s3_resource = boto3.resource(service_name='s3')

    '''
    if there is no S3 bucket the function creates one and uploads the scripts
    '''
    def create_bucket(self):
        try:
            self.s3.create_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            print (e)
            exit(1)

    '''
    uploads to s3 a file called filename
    '''
    def upload_to_s3(self, filename):
        self.s3.upload_file(filename, self.bucket_name, filename)

    '''
    if there is no sqs the function creates one
    '''
    def connect_to_sqs(self):
        for sqs_name in self.sqs_names:
            try:
                self.sqs.get_queue_by_name(QueueName=sqs_name)
            except:
                self.sqs.create_queue(QueueName=sqs_name)

    '''
    sends a message with attributes
    '''
    def send_message_with_attributes(self, msg):
        queue = self.sqs.get_queue_by_name(QueueName=self.sqs_names[0])
        attributes = {
            "LocalName": {
                "DataType": "String",
                "StringValue": self.name
            },
            "OutputFileName": {
                "DataType": "String",
                "StringValue": self.outputName
            }
        }
        queue.send_message(MessageAttributes=attributes, MessageBody=msg)

    '''
    waits for a message from the manager
    '''
    def listen(self):
        try:
            queue = self.sqs.get_queue_by_name(QueueName=self.sqs_names[1])
            for i in range(10):
                for message in queue.receive_messages(VisibilityTimeout=30, MessageAttributeNames=['All']):
                    if message.message_attributes.get('LocalName').get('StringValue') == self.name:
                        self.process(message)
                        try:
                            message.delete()
                        except:
                            pass
        except Exception as e:
            if self.should_terminate:
                print 'Unable to complete the job the manager was terminated'
                print e
                exit(1)

    '''
    sends a terminate message to the manager
    '''
    def terminate(self):
        self.send_message_with_attributes('terminate')

    '''
    creates if needed an instance of ec2 and tags it as manager
    '''
    def connect_to_ec2(self):
        # type: () -> object
        instances = self.conn.get_all_instance_status()
        if len(instances) == 0:
            user_data = '''#!/bin/bash
                     apt-get update
                     git clone  https://github.com/marina90/ass-1
                     pip install boto3
                     pip install botocore
                     pip install pdfminer
                     pip install wand
                     pip install -r ass-1/requirements.txt
                     python ass-1/Manager.py'''
            self.ec2.create_instances(ImageId='ami-bb6801ad', MinCount=int(1), MaxCount=int(1), InstanceType='t1.micro',
                                      KeyName='KeyPair', SecurityGroups=['default'], UserData=user_data)
            time.sleep(20)
            if self.ec2.meta.client.describe_instance_status()['InstanceStatuses'] not in ([], None):
                for status in self.ec2.meta.client.describe_instance_status()['InstanceStatuses']:
                    if status['InstanceState']['Name'] in 'running':
                        instances = self.ec2.instances.filter(
                            Filters=[
                                {'Name': 'instance-state-name', 'Values': ['running', 'pending', 'initializing']}])
                        for instance in instances:
                            instance.create_tags(Tags=[{'Key': 'Role', 'Value': 'Manager'}])
                            return instance
            else:
                time.sleep(10)
                return self.connect_to_ec2()
        elif len(instances) == 1:
            tests = self.ec2.instances.filter(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running', 'initializing', 'pending']}])
            for test in tests:
                if test.tags is None:
                    test.create_tags(Tags=[{'Key': 'Role', 'Value': 'Manager'}])
                    return test
                else:
                    return None

    '''
    after the manager terminated the workers this function termintes the instance of the manager 
    '''
    def terminate_manager(self):
        instances = self.ec2.instances.filter(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running', 'initializing', 'pending']}])
        for instance in instances:
            if instance.tags[0]['Value'] == 'Manager':
                self.conn.terminate_instances(instance_ids=[instance.id])

    '''
    receives a message and determines how to process it
    '''
    def process(self, msg):
        print 'Processing: ' + msg.body
        if msg.body == 'manager terminated':
            print 'Shutting down sqs and manager'
            self.terminate_manager()
            self.terminate_sqs()
        else:
            input_file = self.name + ".html"
            self.s3_resource.meta.client.download_file(self.bucket_name, input_file, input_file)
            os.rename(input_file, self.outputName)
        self.should_terminate = not self.should_terminate

    '''
    terminates the sqs instances
    '''
    def terminate_sqs(self):
        for queue in self.sqs.queues.all():
            queue.delete()


def main(*args):
    #parse args
    input_file_name = args[0]
    output_file_name = args[1]
    n = float(args[2])
    if n == 0:
        n = 1.0
    if len(args) == 4 and str(args[3]).lower() in ['terminate']:
        terminate = True
    else:
        terminate = False

    # count number of lines in inputFile
    with open(input_file_name) as inputFile:
        numOfLines = sum(1 for _ in inputFile)
    n = math.ceil(numOfLines/n)

    #connect / create manager
    local = Local_application(output_file_name)
    print 'Connecting to s3'
    local.create_bucket()
    print 'Connecting to ec2'
    local.connect_to_ec2()
    print 'Connecting to sqs'
    local.connect_to_sqs()
    print 'uploading'
    local.upload_to_s3(input_file_name)
    msg = "job" + '\t' + input_file_name + '\t' + str(n)
    local.send_message_with_attributes(msg)
    print 'waiting for result'
    while not local.should_terminate:
        local.listen()
    if terminate:
        print 'terminating...'
        local.terminate()
        while local.should_terminate:
            local.listen()


if __name__ == "__main__":
    if len(sys.argv) == 5:
        main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    elif len(sys.argv) == 4:
        main(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print "Number of arguments isn't right"
