"""
The lambda handler is invoked a Custom Config rule when there are SQS configuration changes.
It remediate non-compliant queues without an AWS KMS key using a given key and sends emails
to the resource owner.
"""
import os
import re
import json
import boto3
import logging
from random import randint
from botocore.config import Config
from botocore.exceptions import ClientError

log_level = {
                "CRITICAL": logging.CRITICAL,
                "ERROR" : logging.ERROR,
                "WARNING" : logging.WARNING,
                "INFO" : logging.INFO,
                "DEBUG" : logging.DEBUG
            }

log = logging.getLogger(__name__)
log.setLevel(log_level[os.environ.get('LOG_LEVEL',"INFO")])

sqs_client = boto3.client('sqs')
ses_client = boto3.client('ses')
config_client = boto3.client('config')
SEND_EMAIL = os.environ.get("SEND_EMAIL", "false").upper()

class EmailNotFound(Exception):
    pass

def evaluate_compliance(queue_url):
    '''Evaluates and returns the compliance type of SQS Queue'''

    try:
        response =  sqs_client.get_queue_attributes(QueueUrl=queue_url,AttributeNames=["KmsMasterKeyId"])
        log.info(f"get_queue_attributes response: {response}")

        if "Attributes" in response and "KmsMasterKeyId" in response.get("Attributes"):
            return "COMPLIANT"

        return "NON_COMPLIANT"
    except ClientError:
        log.exception(f"Could not evaluate compliance of Queue {queue_url}")
        raise

def auto_remediate(queue_url, kms_key_id):
    '''Enables Server side encryption of SQS Queue using KMS Key'''

    try: 
        sqs_client.set_queue_attributes(QueueUrl=queue_url, 
                                        Attributes={'KmsMasterKeyId': kms_key_id}
                                        )
        log.info(f"{queue_url} is now COMPLIANT after remediation")
        return "COMPLIANT","AutoRemediated"
    except ClientError:
        log.exception(f"Failed to enable KMS encryption on Queue {queue_url}")
    
    return "NON_COMPLIANT","RemediationFailed"

def put_evaluation( config_item, result_token, compliance_type, remediation_status):
    '''Delivers Resource Compliance Evaluation Result to Config Rule'''

    resource_type = config_item["resourceType"]
    resource_id = config_item["resourceId"]
    capture_time = config_item.get("configurationItemCaptureTime")

    evaluation = []        
    evaluation.append({'ComplianceResourceType': resource_type,
                        'ComplianceResourceId': resource_id,
                        'ComplianceType': compliance_type,
                        'Annotation': remediation_status,
                        'OrderingTimestamp': capture_time
                    } )

    try:
        config_client.put_evaluations(Evaluations=evaluation,ResultToken=result_token)
        log.info(f"{resource_id} is {compliance_type}")
        log.info(f"Successfully updated config rule for {resource_id}")
    except ClientError:
        log.exception(f"Failed to update config rule for {resource_id}")

def get_fallback_email(regex):
    '''Returns default email address if valid'''

    FALLBACK_EMAIL = os.environ.get("FALLBACK_EMAIL","")
    if (re.fullmatch(regex, FALLBACK_EMAIL)):
        log.info(f"Fallback email will be used")
        return FALLBACK_EMAIL
    
    raise EmailNotFound("No Valid Email found")

def get_contact_email(queue_url):
    '''Gets email address from tags or returns default email address if valid'''

    try:
        response = sqs_client.list_queue_tags(QueueUrl=queue_url)
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

        if response.get("Tags"):
            email_address = response.get("Tags").get("owner_email")

            if(re.fullmatch(regex, email_address)):
                log.info(f"Valid email exists on {queue_url.split('/')[-1]}")
                return email_address
    except ClientError:
        log.exception(f"Failed to get valid email from Queue")

    email_address = get_fallback_email(regex)
    return email_address if ( re.fullmatch(regex, email_address) ) else None

def send_email(email_address, remediation_status, queue_url, kms_key_id=""):
    '''Sends an email when an action is taken on a resource'''

    queue_name = queue_url.split("/")[-1]
    CHARSET = "UTF-8"

    if remediation_status == "RemediationFailed":
        BODY_TEXT = f"""SQS Queue {queue_name} is not in compliance with SampleOrg Security Policy. 
                    \rEnable Server-side encryption using KMS key Id {kms_key_id}."""
    elif remediation_status == "AutoRemediated":
        BODY_TEXT = f"""SQS Queue {queue_name} was not in compliance with SampleOrg Security Policy. 
                    \rServer-side encryption has been enabled using KMS key Id {kms_key_id}."""

    try:
        ses_client.send_email(
            Destination= { 'ToAddresses': [email_address] },
            Message={
                'Body': {
                    'Text': {
                        'Charset': CHARSET,
                        'Data': BODY_TEXT,
                    }
                },
                'Subject': {
                    'Charset': CHARSET,
                    'Data': f"SQS Queue COMPLIANCE NOTIFICATION",
                },
            },
            Source = email_address,
        )
        log.info(f"Email sent successfully to {email_address} ##")
    except ClientError:
        log.exception(f"Failed to send email to {email_address}")

def lambda_handler(event, context):
    """
    It extracts the SQS queue URL from the event and evaluates the queue's encryption status. 
    If the queue is not encrypted with a KMS Key, it will encrypt the queue using the KMS key ID 
    provided in the rule parameters and send an email
    """

    invoking_event = json.loads(event["invokingEvent"])
    message_type = invoking_event.get("messageType")
    compliance_type = "NOT_APPLICABLE"
    result_token = event.get("resultToken", "no token")

    log.info('## RAW EVENT ##')
    log.info(event)
    log.info('## INVOKING EVENT ##')
    log.info(json.dumps(invoking_event, indent=4))

    if message_type == "ConfigurationItemChangeNotification":
        config_item = invoking_event["configurationItem"]
    elif message_type == "OversizedConfigurationItemChangeNotification":
        config_item = invoking_event["configurationItemSummary"]
    else:
        log.info("Only Config Item Change events are evaluated")
        return
    
    if config_item["configurationItemStatus"] == "ResourceDeleted":
        remediation_status = "NotApplicable"
    else:
        
        QUEUE_URL = config_item["resourceId"]
        remediation_status = "No Remediation required"
        compliance_type = evaluate_compliance(queue_url=QUEUE_URL)
        log.info(f"{QUEUE_URL} is {compliance_type}")
        if 'ruleParameters' in event and compliance_type == "NON_COMPLIANT":
            rule_parameters = json.loads(event['ruleParameters'])
            kms_key_id = rule_parameters.get("KmsKeyId")
            compliance_type, remediation_status = auto_remediate(QUEUE_URL, kms_key_id)
        elif compliance_type == "NON_COMPLIANT":
            remediation_status = "RemediationFailed"
    
    put_evaluation(config_item, result_token, compliance_type, remediation_status)

    if (SEND_EMAIL == "TRUE" and
        remediation_status in ["RemediationFailed", "AutoRemediated"]):

        email_address = get_contact_email(QUEUE_URL)
        send_email(email_address,remediation_status,QUEUE_URL, kms_key_id)