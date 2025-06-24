# S3 Ransomware Batch Deletion Attack

## Introduction

This blog post details the S3 ransomware batch deletion attack, a technique used to simulate ransomware activity in AWS S3 buckets. We'll explore how this attack works and discuss mitigation strategies to protect your data.

## The Attack

The S3 ransomware batch deletion attack simulates a ransomware scenario targeting an S3 bucket. It involves emptying an S3 bucket through batch deletion and then uploading a ransom note. This attack leverages the `DeleteObjects` API to remove multiple objects at once, making it efficient for large-scale deletion.

### Detailed Steps

1.  **Listing Objects:** The attack starts by listing all objects and their versions in the target S3 bucket using the `ListObjectVersions` API.
2.  **Batch Deletion:** It then deletes all these objects in a single request using the S3 `DeleteObjects` API. This API can delete up to 1000 objects at a time.
3.  **Ransom Note:** Finally, the attack uploads a ransom note to the bucket, typically named `FILES-DELETED.txt`, informing the victim that their data has been "backed up" and providing contact information for negotiating its recovery. The content of the ransom note might look like this:

    ```text
    Your data is backed up in a safe location. To negotiate with us for recovery, get in touch with rick@astley.io. In 7 days, if we don't hear from you, that data will either be sold or published, and might no longer be recoverable.'
    ```

## Mitigation Strategies
*   **Monitoring and Alerting:** Set up monitoring and alerting to detect unusual deletion patterns.

To protect against this type of ransomware attack, consider the following mitigation strategies:

*   **Versioning:** Enable S3 versioning to keep a history of all object versions.
*   **MFA Delete:** Require multi-factor authentication for deleting object versions.
*   **Bucket Policies:** Implement strict bucket policies to control access and restrict deletion permissions.
