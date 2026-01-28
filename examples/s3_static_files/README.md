# AWS S3 Static Files

This example shows how you can configure Nautobot to host static files on AWS S3.

## Installation

Nautobot can use [`django-storages`](https://django-storages.readthedocs.io/en/stable/) to publish files to S3 -- see the [docs](https://docs.nautobot.com/projects/core/en/stable/installation/nautobot/#remote-file-storage) for more information.

TLDR:

```shell
echo "nautobot[remote_storage]" >> $NAUTOBOT_ROOT/local_requirements.txt
pip3 install "nautobot[remote_storage]" boto3
```

## Configuration

The [`django-storages`](https://django-storages.readthedocs.io/en/stable/) library is quite powerful, please refer to their documentation for a more detailed explanation of the individual settings or for more information.

In `nautobot_config.py` define the following configuration:

```python
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "access_key": "...",
            "secret_key": "...",
            "bucket_name": "my-bucket-name",
            "region_name": "us-west-1",
            "default_acl": "public-read",
            "querystring_auth": False,
            "location": "subfolder/name/",
            # ... additional options as needed
        },
    },
    "staticfiles": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            # base options as above...
            "location": "other_subfolder/name/",
            # ... additional options as needed
        },
    },
    "nautobotjobfiles": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            # base options as above...
            "location": "some_jobs_subfolder/",
            # ... additional options as needed
        },
    },
}
```

If `access_key` and/or `secret_key` are not set, `boto3` [internally looks up IAM credentials](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html). Using an [IAM Role for EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html?icmpid=docs_ec2_console) is highly recommended.

## Bucket Creation

The AWS S3 bucket will be hosting Nautobot static files and needs some specific configuration to allow anonymous HTTP access. The following is an example of Terraform configuration to create the S3 bucket appropriately, the same values can be configured manually:

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
