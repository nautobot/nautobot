# AWS S3 Static Files

This example shows how you can configure Nautobot to host static files on AWS S3.

## Installation

Nautobot can use [`django-storages`](https://django-storages.readthedocs.io/en/stable/) to publish files to S3 -- see the [docs](https://nautobot.readthedocs.io/en/stable/installation/nautobot/#remote-file-storage) for more information.

TLDR:

```shell
$ echo django-storages >> $NAUTOBOT_ROOT/local_requirements.txt
$ pip3 install django-storages
```

## Configuration

The [`django-storages`](https://django-storages.readthedocs.io/en/stable/) library is quite powerful, please refer to their documentation for a more detailed explanation of the individual settings or for more information.

In `nautobot_config.py` define the following configuration:

```python
STORAGE_BACKEND = "storages.backends.s3boto3.S3Boto3Storage"

STORAGE_CONFIG = {
    "AWS_ACCESS_KEY_ID": "...",
    "AWS_SECRET_ACCESS_KEY": "...",
    "AWS_STORAGE_BUCKET_NAME": "my-bucket-name",
    "AWS_S3_REGION_NAME": "us-west-1",
    "AWS_DEFAULT_ACL": "public-read",
    "AWS_QUERYSTRING_AUTH": False,
    "AWS_LOCATION": "subfolder/name/"
}
STATICFILES_STORAGE = STORAGE_BACKEND
```

If `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are not set, `boto3` [internally looks up IAM credentials](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html).  Using an [IAM Role for EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html?icmpid=docs_ec2_console) is highly recommended.

## Bucket Creation

The AWS S3 bucket will be hosting Nautobot static files and needs some specific configuration to allow anonymous HTTP access.  The following is an example of Terraform configuration to create the S3 bucket appropriately, the same values can be configured manually:

```terraform
resource "aws_s3_bucket" "nautobot_static_files" {
  bucket        = "my-bucket-name"
  acl           = "public-read"

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET"]
    allowed_origins = ["http*"]
  }
  cors_rule {
    allowed_methods = ["GET", "HEAD"]
    allowed_origins = ["*"]
  }

  tags = {
    Name = "Nautobot Static Files"
  }
}
```
