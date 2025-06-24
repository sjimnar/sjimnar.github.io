---
date:
  created: 2025-06-24
---

# S3 Ransomware Batch Deletion Attack

## Introduction

As an AWS security consultant, I've observed the devastating effects of ransomware on AWS S3 buckets. A particularly effective technique employed by attackers involves leveraging the S3 `DeleteObjects` API for batch deletion. In this post, I'll share my insights on how this attack unfolds and, more importantly, what measures you can implement to safeguard your data.

## The Attack

The S3 ransomware attack targets an S3 bucket by emptying it through batch deletion and then uploading a ransom note. This attack leverages the `DeleteObjects` API to remove multiple objects and their versions at once, making it a highly efficient way to cause significant data loss.

### Detailed Steps

1.  **Listing Objects:** The attack starts by listing all objects and their versions in the target S3 bucket using the `ListObjectVersions` API.
2.  **Batch Deletion:** It then deletes all these objects in a single request using the S3 `DeleteObjects` API. This API can delete up to 1000 objects at a time.
3.  **Ransom Note:** Finally, the attack uploads a ransom note to the bucket, typically named `FILES-DELETED.txt`, informing the victim that their data has been "backed up" and providing contact information for negotiating its recovery. The content of the ransom note might look like this:

    ```text
    Your data is backed up in a safe location. To negotiate with us for recovery, get in touch with rick@astley.io. In 7 days, if we don't hear from you, that data will either be sold or published, and might no longer be recoverable.'
    ```

## Mitigation Strategies

To protect against this type of ransomware attack, consider the following mitigation strategies:

*   **Monitoring and Alerting:** Set up monitoring and alerting to detect unusual deletion patterns.
*   **Versioning:** Enable S3 versioning to keep a history of all object versions. While versioning allows you to recover from accidental or malicious deletions, it doesn't prevent the `DeleteObjects` API from removing all versions if the attacker has sufficient permissions.
*   **MFA Delete:** Require multi-factor authentication (MFA) for deleting object versions. This is a critical control, as it requires an additional layer of authentication to permanently delete objects, even with versioning enabled. Without MFA Delete, an attacker with sufficient permissions can bypass versioning by simply deleting all object versions.
*   **Bucket Policies:** Implement strict bucket policies to control access and restrict deletion permissions.
