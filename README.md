<h2 align="center">AWS Auto Remediation Solution with Notification</h2>

![Solution](https://github.com/yemisprojects/aws-resource-compliance/blob/main/images/soln_architecture.png)
<h4 align="center">Architecture diagram</h4>

<h2 align="center">Technical overview</h2>

The solution consists of three services; AWS Config, Lambda, and SES. A custom config rule is used to track compliance of SQS queues. When there are configuration changes the config rule will trigger resource evaluations using a Lambda function which delivers evaluation results back to the rule and remediates non-compliant queues using a given KMS key. Lambda uses SES to send emails when a resource is remediated. The solution will be deployed using Terraform.

## Pre-requisites
- Terraform CLI (1.0+) installed
- An AWS account and user account with admin permissions
- AWS CLI (2.0+) installed

## Deployment Steps

Replace `<email_address>` with your email address before running in the commands below.
```bash
git clone https://github.com/yemisprojects/aws-resource-compliance.git && cd aws-resource-compliance
terraform init
terraform plan -var="default_email_id=<email_address>"
terraform apply -var="default_email_id=<email_address>" --auto-approve 
```