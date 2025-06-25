---
title: Defending S3 - Anatomy and Countermeasures for Encryption and Deletion Attacks
date: 2025-06-25
author: Sergio Jimenez
tags:
  - aws
  - security
  - ransomware
---


# Defending S3: Anatomy and Countermeasures for Encryption and Deletion Attacks

Lately, we're seeing an attack pattern against Amazon S3 that is brutally simple and effective. Attackers don't need a zero-day exploit in AWS. They just need one thing: a set of compromised AWS credentials. With that, they can either delete or hijack all your data.

In this post, we're going to break down the anatomy of two specific tactics gaining popularity and, more importantly, walk through the defense playbook to make sure it doesn't happen to you. Because under the shared responsibility model, whether your data in S3 is still there tomorrow depends on the defenses you implement today.

## The Anatomy of the Attacks

Both attacks start the same way: the attacker gets their hands on valid credentials with permissions over your buckets. From there, the path forks.

### Tactic 1: Ransomware via Batch Deletion

This is a scorched-earth attack. The goal is simple: wipe everything and leave a ransom note. It's fast and destructive.

1.  **Inventory:** First, the attacker needs to know what to delete. They make a `ListObjectVersions` API call to get a complete list of every object and every version within the target bucket.
2.  **Annihilation:** With the list in hand, they use the `DeleteObjects` API. This operation is terrifyingly efficient for malicious purposes, as it can delete up to 1,000 objects (and their versions) in a single request. A simple loop in a script can empty a bucket with millions of objects in a very short time.
3.  **The Note:** Once the bucket is empty, the attacker uploads a file, typically named `FILES-DELETED.txt` or similar, containing the ransom message and payment instructions.

### Tactic 2: Parasitic Encryption with SSE-C

This technique is more subtle and insidious. The data isn't deleted; it's hijacked right under your nose, without a single byte ever leaving your AWS account.

1.  **Access:** Again, the attacker has credentials with read and write permissions (`s3:GetObject`, `s3:PutObject`).
2.  **The Hijack:** The attacker reads an object, but instead of downloading it, they re-write it in place using `PutObject`, adding a key HTTP header: `x-amz-server-side-encryption-customer-key`. The value for this header is an AES-256 encryption key that **the attacker generates and keeps**.
3.  **The Trick:** AWS receives the request, sees the SSE-C (Server-Side Encryption with Customer-Provided Keys) header, and dutifully encrypts the object with the attacker's key. AWS **never sees or stores this key**. All it records in CloudTrail is an HMAC of the key, which can verify future requests but cannot be used to reconstruct it. The original object is overwritten by an encrypted version that only the attacker can access.
4.  **The Pressure:** To finish the job, actors like the "Codefinger" group add a lifecycle policy that marks these encrypted objects for deletion in 7 days. The clock starts ticking.

This attack is especially sneaky because many threat detection systems are configured to look for data exfiltration. There is none here; everything happens inside your perimeter.

## The Defense Playbook: Containment Strategies

Protecting yourself requires a defense-in-depth approach. There's no single silver bullet, but rather a set of barriers that makes a successful attack exponentially more difficult.

### 1. Immutability: Your Primary Line of Defense

If an attacker can't delete or overwrite your data, their attack fails. This is non-negotiable.

* **Enable S3 Versioning:** This is the prerequisite for everything else. It lets you preserve, retrieve, and restore every version of every object.
* **Implement S3 Object Lock in Compliance Mode:** Versioning alone isn't enough if the attacker has permissions to delete versions. Object Lock in `Compliance` mode creates a WORM (Write-Once-Read-Many) safeguard. No one, not even the root user, can delete or modify a protected object version before its retention period expires. Set this on your critical buckets. `Governance` mode is useful for testing, but it can be disabled by privileged users.
* **Require MFA Delete:** This is the final protective layer for versioning. It requires any attempt to delete an object version or change the bucket's versioning state to be authenticated with an MFA device. Without it, an attacker with the right credentials could simply disable versioning or delete the versions one by one.

### 2. Abandon Long-Lived Credentials

The root cause of these attacks is almost always a compromised static access key. Stop using them.

* **Use IAM Roles:** For any workload inside AWS (EC2, Lambda, etc.), use IAM Roles. They provide temporary credentials automatically, eliminating the risk of leaked static keys.
* **IAM Identity Center (SSO):** For human access, centralize it with IAM Identity Center. It allows your developers and admins to fetch short-lived credentials for the CLI/SDK, protected by your identity provider and MFA.
* **IAM Roles Anywhere:** If you have on-premises systems that need AWS access, this is the way. It lets your own servers obtain temporary AWS credentials using their existing identities (like X.509 certificates) without storing an IAM key on them.

### 3. Block Unnecessary Attack Vectors

If you don't use a feature, disable it.

* **Block SSE-C with Policies:** If your organization has no legitimate use case for Server-Side Encryption with Customer-Provided Keys (and most don't), forbid it. You can do this with a bucket policy or, more forcefully, with a Service Control Policy (SCP) in AWS Organizations that denies any API call containing the `x-amz-server-side-encryption-customer-algorithm` parameter.

```json title="S3 Bucket Policy to Deny SSE-C"
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenySSEC",
      "Effect": "Deny",
      "Action": "s3:PutObject",
      "Resource": "arn:aws:s3:::*/*",
      "Condition": {
        "Null": {
          "s3:x-amz-server-side-encryption-customer-algorithm": "false"
        }
      }
    }
  ]
}
```
