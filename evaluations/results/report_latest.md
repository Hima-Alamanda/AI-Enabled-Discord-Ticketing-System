# AI Evaluation Report: Gemini vs. Grok (Zoho Ticket)

**Date:** 2026-04-02 14:08:55
**Dataset:** Zoho Ticket (8 test cases)

## 1. Quality Metrics (1-5 Scale)
Each model's response is scored by an independent AI Auditor based on this scale:

| Score | Rating | Description |
|:---:|:---|:---|
| **5** | **Excellent** | Fully correct, clear, and follows all rules. |
| **4** | **Good** | Correct and helpful; minor wording/tone issues. |
| **3** | **Acceptable** | Mostly correct but missing some details. |
| **2** | **Poor** | Contains important mistakes or unclear steps. |
| **1** | **Failure** | Incorrect, misleading, or failed to answer. |

### The 8 Quality Categories
1. **Correctness:** Whether the bot gives the right answer based on past resolved tickets or known support information.
2. **Faithfulness:** Whether the bot stays accurate and does not make up information.
3. **Actionability:** Whether the bot gives clear steps that the user can actually follow.
4. **Format Adherence:** Whether the bot follows the expected response structure or headings.
5. **Ambiguity:** Whether the bot asks for more details when the issue is unclear instead of guessing.
6. **Multimodal:** Whether the bot can correctly use information from attached images or screenshots.
7. **Escalation:** Whether the bot correctly decides to solve the issue itself or hand it over to a human technician.
8. **Empathy:** Whether the bot sounds professional, polite, and helpful.

## 2. Quality Scores Summary

| model               |   Correctness (1-5) |   Faithfulness (1-5) |   Actionability (1-5) |   Format Adherence (1-5) |   Ambiguity Handling (1-5) |   Multimodal (1-5) |   Escalation Logic (1-5) |   Empathy & Tone (1-5) |
|:--------------------|--------------------:|---------------------:|----------------------:|-------------------------:|---------------------------:|-------------------:|-------------------------:|-----------------------:|
| Gemini 2.5 Pro      |                3.38 |                 3.38 |                  3.62 |                     4    |                       4.88 |               4.5  |                     3.88 |                   4.62 |
| Grok 4.20 Reasoning |                2.86 |                 2.86 |                  3.71 |                     4.57 |                       3.86 |               4.43 |                     3    |                   4.29 |

### Performance Metrics
1. **Latency:** The total time (in seconds) the bot took to process and reply.
2. **Token Usage:** The amount of "data" processed by the model (input + output). This directly affects operational cost.
## 2. Performance & Cost Metrics (Avg)

| model               |   Avg Latency (s) |   Input Tokens (1M-2M) |   Output Tokens (30k-65k) |   Total Tokens |
|:--------------------|------------------:|-----------------------:|--------------------------:|---------------:|
| Gemini 2.5 Pro      |             21.1  |                3177.88 |                    418.38 |        6162.75 |
| Grok 4.20 Reasoning |             11.75 |                3187.71 |                    420.43 |        7073.71 |

## 3. Key Insights

### Gemini 2.5 Pro
- **Strength:** Ambiguity Handling (1-5) (4.88)
- **Potential Area for Improvement:** Correctness (1-5) (3.38)
- **Avg Turnaround:** 21.1s
- **Avg Tokens:** 6162 (In: 3177, Out: 418)

### Grok 4.20 Reasoning
- **Strength:** Format Adherence (1-5) (4.57)
- **Potential Area for Improvement:** Correctness (1-5) (2.86)
- **Avg Turnaround:** 11.75s
- **Avg Tokens:** 7073 (In: 3187, Out: 420)

## 4. Case-by-Case Breakdown

### Model: Gemini 2.5 Pro
#### Case ZT-001: I am getting an error message during end of month reporting ...
- **Total Score:** 36/40
- **Latency:** 28.09s | **Tokens:** 6414
- **Judge Reasoning:** *The AI's response is largely correct and follows the ground truth. However, it slightly deviates in the precision of the steps. The ground truth explicitly mentions verifying 'Debits and Credits are equal' and to 'click Repost', which are more specific actions than the AI's 'verify that the Difference Amount for the batch is zero and then attempt to post it again'. While the intent is similar, the ground truth provides clearer, more direct instructions. Additionally, the AI bolded 'Difference Amount' which is not a system element or button, unlike the ground truth's bolding of 'Unposted Entries', 'Debits', 'Credits', and 'Repost'.*

**AI Response:**
```
Hi Tester,

I understand you're encountering an error when posting your Journal Entry batches. This issue typically arises when a batch contains unposted or unbalanced entries, which prevents the system from posting it successfully and results in the "Error" status with a difference amount.

To resolve this, you will need to clear the erroneous lines from the batch:

1.  Navigate to the **Batch Review** screen in the application.
2.  Locate the specific batch that is showing the **Error** status.
3.  Within the batch, identify and **Delete** any unposted or erroneous entries.
4.  Once the lines are removed, verify that the **Difference Amount** for the batch is zero and then attempt to post it again.

If the batch still fails to post after these steps, please let me know and I can investigate for any underlying record locks.
```
---

#### Case ZT-002: I cannot access any tickets for DC33 or JFK in Zoho with my ...
- **Total Score:** 29/40
- **Latency:** 26.64s | **Tokens:** 6228
- **Judge Reasoning:** *The AI correctly identifies the problem and the root cause based on the ground truth. However, it deviates significantly in actionability and faithfulness. The ground truth provides clear, numbered steps for the user and states 'I have initiated a request', implying proactive action. The AI, instead, asks 'Would you like me to proceed with creating this access request for you?' and completely omits the user-facing steps (log out, clear cache, log back in). This makes the response less actionable and less faithful to the proactive solution provided in the ground truth. The formatting is mostly good, but the ground truth bolds 'System Administrator' which the AI does not, and the AI bolds 'Department-Level visibility' which the ground truth does not.*

**AI Response:**
```
Hi Tester,

I understand you're receiving an "Access Denied" error when trying to view tickets in **Zoho Desk**. This issue typically occurs because your user profile lacks the specific **Department-Level visibility** required to access tickets within restricted service queues like **DC33** and **JFK**.

To resolve this, I will need to submit a request to our System Administration team to update your account permissions. They will grant your profile the necessary visibility for both the **DC33** and **JFK** departments. You will be notified once the access has been granted.

Would you like me to proceed with creating this access request for you?
```
---

#### Case ZT-003: Retirees who are under the HMO plan are still showing as act...
- **Total Score:** 39/40
- **Latency:** 18.84s | **Tokens:** 6009
- **Judge Reasoning:** *The AI's response is highly accurate, providing the correct explanation for the issue and clear, actionable steps to resolve it, mirroring the ground truth closely. The escalation path is also correctly handled. The only minor deviation is the bolding of 'Active' and 'Retired' which are statuses, not strictly 'buttons/systems' as per the format adherence rule, although the ground truth itself bolds plan names, making the AI's choice consistent with the ground truth's style for key terms.*

**AI Response:**
```
Hi Tester,

I understand you're seeing retirees on the HMO plan incorrectly listed as active in the eligibility file. This issue typically occurs due to backend synchronization delays or when retirement termination dates are missing from the employee's record.

To correct this, you can manually update the retiree's status by following these steps:

1.  Open the **Benefit Administration** system.
2.  Locate the specific retiree's record.
3.  Adjust the status field from **Active** to **Retired**.
4.  Confirm the **HMO Plan** line includes the correct retirement effective date.
5.  Generate a new **Eligibility File** to reflect the updated status.

If the eligibility file still shows the incorrect status after these changes, please let me know and I can investigate further.
```
---

#### Case ZT-004: The address book is not letting me add a blank value to a fi...
- **Total Score:** 40/40
- **Latency:** 23.7s | **Tokens:** 6911
- **Judge Reasoning:** *The AI correctly identifies the problem and provides a solution with clear, numbered steps that are directly derived from the ground truth. The formatting is correct, and the tone is empathetic. The escalation logic is also appropriate, offering further investigation if the initial steps don't resolve the issue or if the user lacks access.*

**AI Response:**
```
Hi Tester,

I understand you're having trouble adding a blank value to a field in the address book. This typically happens when a **UDC (User Defined Code)** rule or a field validation constraint is set up to mark that field as mandatory, which prevents the system from accepting an empty value.

To resolve this, you will need to adjust the validation settings for that field. Please follow these steps:

1.  Navigate to the **UDC Maintenance** screen for the specific field you are trying to edit.
2.  Check the validation table to confirm if a **Blank** row is permitted.
3.  If it is not, apply the system fix to disable the mandatory field requirement for that module.
4.  Refresh the **Address Book** and you should now be able to save the record with the blank value.

If you do not have access to the **UDC Maintenance** screen or if the issue persists, please let me know and I can investigate further.
```
---

#### Case ZT-005: We need to close the Daiwa fiscal year end. What is the proc...
- **Total Score:** 24/40
- **Latency:** 19.81s | **Tokens:** 6210
- **Judge Reasoning:** *The AI's response incorrectly escalates the issue by offering to create a ticket instead of providing the solution steps available in the ground truth. The ground truth explicitly provides a multi-step process for the fiscal year-end close. While the AI correctly identifies it as a critical process handled by a specialized team (which is mentioned in the ground truth), it completely omits the actionable steps, making the response unhelpful and not faithful to the provided solution. The expected action was to provide a solution, not to escalate immediately.*

**AI Response:**
```
Hi Tester,

I understand you're looking for the procedure for the Daiwa fiscal year-end closing. This is a critical and sensitive financial process that is typically handled by a specialized team to ensure data integrity and compliance. Due to the specific permissions and coordination required, this is not a standard self-service procedure.

The available information indicates this is a high-priority event managed directly by our senior technical teams in coordination with the Finance department. To initiate this, a formal service request must be logged and assigned to the appropriate group.

I can create a ticket on your behalf and route it to the Finance Systems team to begin the process. Would you like me to proceed?
```
---

#### Case ZT-006: I need to remove a member from the eligibility file. How do ...
- **Total Score:** 27/40
- **Latency:** 20.07s | **Tokens:** 6216
- **Judge Reasoning:** *The AI correctly identifies the need to contact the data management team. However, it hallucinates specific names (Ashok Chinthala and Debiprasad Mohanty) as the recipients, which are not present in the provided KB context or ground truth. The ground truth specifies sending the request to the 'Data Management team' generally. Additionally, the AI's steps are less detailed than the ground truth, omitting the 'unique Member ID' and 'Effective Removal Date' as specific requirements for the request.*

**AI Response:**
```
Hi Tester,

I understand you need to remove a member from an eligibility file. To ensure data integrity and proper tracking, these modifications are handled directly by our data management team. This process ensures that all changes are accurately reflected in the system.

To process this request, please follow these steps:

1.  Compose an email detailing the removal request. Be sure to include the member's full name and any other relevant identifiers.
2.  Send this email to **Ashok Chinthala** and **Debiprasad Mohanty**, who will process the removal from the eligibility file.

Please let me know if you need their contact details or have any further questions.
```
---

#### Case ZT-007: Something is broken in the system....
- **Total Score:** 37/40
- **Latency:** 19.96s | **Tokens:** 6054
- **Judge Reasoning:** *The AI correctly identified the need for clarification given the vague user query. It provided clear, numbered questions and maintained an empathetic and professional tone. However, it missed one detail requested in the ground truth ('when the issue started') and added another ('What specific task were you trying to perform?'). Additionally, it did not follow the ground truth's specific bolding style for keywords like 'Application' or 'Error Message', which impacts format adherence.*

**AI Response:**
```
Hi Tester,

I'm sorry to hear you're running into a system issue. I understand how frustrating that can be, and I'm here to help you get it resolved. To properly diagnose what's happening, I'll need a little more information about the problem.

Could you please provide me with the following details?

1.  Which application or system were you using when the issue occurred?
2.  What specific task were you trying to perform?
3.  If you received an error message, could you please provide the exact text or a screenshot?

Once I have these details, I can investigate further and provide a targeted solution.
```
---

#### Case ZT-008: I am getting this error when opening Outlook. I have attache...
- **Total Score:** 26/40
- **Latency:** 11.71s | **Tokens:** 5260
- **Judge Reasoning:** *The AI completely ignored the ground truth's identification of the specific error code (0x80040115) and its typical cause (corrupted OST file). Instead, it provided a generic solution for Outlook connection issues (clearing credentials) which is not directly aligned with the specific error mentioned in the ground truth. This is a major faithfulness and correctness issue. While the steps are actionable and the format/tone are good, the core solution is incorrect for the identified problem.*

**AI Response:**
```
Hi Tester,

I understand you're encountering an error when opening Outlook. This type of issue often occurs when your stored login credentials in the Windows Credential Manager have become stale or are conflicting with a recent update, which can disrupt the connection to the server.

To resolve this, please follow these steps to clear the cached credentials:

1.  Close **Outlook** and all other **Office** applications completely.
2.  Open the Windows **Control Panel** and navigate to **Credential Manager**.
3.  Select **Windows Credentials** and remove all entries that begin with **MicrosoftOffice16**.
4.  Restart **Outlook** and sign in when prompted to re-establish the connection.

If the error message continues to appear after these steps, please let me know, and we can investigate further.
```
---


### Model: Grok 4.20 Reasoning
#### Case ZT-001: I am getting an error message during end of month reporting ...
- **Total Score:** 37/40
- **Latency:** 11.17s | **Tokens:** 7038
- **Judge Reasoning:** *The AI's response is largely correct and provides actionable steps. However, it introduces 'JDE' which is not explicitly mentioned in the provided context, slightly impacting faithfulness. The ground truth's steps 3 and 4 are also slightly more precise ('Debits and Credits are equal' and 'click Repost') compared to the AI's 'Verify the Difference Amount is now zero, then post the batch again', making the GT marginally more actionable. Despite these minor points, the response is very helpful and well-formatted.*

**AI Response:**
```
Hi Tester,

This JE batch error during end-of-month reporting is common in JDE and typically occurs when the batch contains unbalanced entries, unposted lines, or record locks, resulting in a non-zero difference amount and an Error status.

To resolve this, please follow these steps:

1. Navigate to the **Batch Review** screen.
2. Locate the specific batch showing the **Error** status.
3. Identify and **Delete** any unposted entries or erroneous lines within that batch.
4. Verify the **Difference Amount** is now zero, then post the batch again.

If the batch still fails to post after these steps, please share the exact error details from the Work Center and I'll escalate it for you.
```
---

#### Case ZT-002: I cannot access any tickets for DC33 or JFK in Zoho with my ...
- **Total Score:** 27/40
- **Latency:** 10.75s | **Tokens:** 7289
- **Judge Reasoning:** *The AI correctly identifies the cause of the 'access denied' error. However, its proposed solution deviates significantly from the ground truth. The ground truth immediately initiates a request to the System Administrator, which is the correct and most effective action for a permission-based access issue. The AI, instead, suggests user-side troubleshooting (logging out, clearing cache, logging back in) as primary steps, and only *then* offers to initiate an admin request if those steps fail. These initial troubleshooting steps are unlikely to resolve a core permission problem and unnecessarily delay the actual resolution. This makes the solution less correct and less actionable than the ground truth's approach.*

**AI Response:**
```
Hi Tester,

This "Access Denied" error for DC33 and JFK tickets in **Zoho Desk** occurs because your current role profile is missing the specialized department-level visibility permissions required for these restricted service queues.

To resolve this, please follow these steps:

1. Log out of **Zoho Desk** completely.
2. Clear your browser cache and cookies (in Chrome: **Settings** > **Privacy and security** > **Clear browsing data**).
3. Log back into **Zoho Desk** and test access to the DC33 and JFK departments.

If the tickets are still unavailable after these steps, this requires a System Administrator to update your account permissions. I'll initiate that request on your behalf right away.

Let me know if you run into any other issues in the meantime.
```
---

#### Case ZT-003: Retirees who are under the HMO plan are still showing as act...
- **Total Score:** 40/40
- **Latency:** 9.63s | **Tokens:** 6290
- **Judge Reasoning:** *The AI's response is perfectly correct, providing accurate steps to resolve the issue, which align almost identically with the ground truth. It maintains a natural conversational flow, uses correct bolding for systems and statuses, and offers appropriate follow-up if the initial steps don't resolve the problem. The tone is professional and helpful.*

**AI Response:**
```
Hi Tester,

This issue with HMO retirees appearing as **Active** on the eligibility file usually stems from missing retirement termination dates or a synchronization delay between the HR records and the insurance export files.

To correct this, please follow these steps:

1. Open the **Benefit Administration** system.
2. Locate the specific retiree record in question.
3. Manually adjust the status field from **Active** to **Retired**.
4. Confirm the **HMO Plan** line includes the correct retirement effective date.
5. Generate a new **Eligibility File** and verify the updated export.

If the retirees continue to show incorrectly after this, please let me know so we can review the backend sync.
```
---

#### Case ZT-004: The address book is not letting me add a blank value to a fi...
- **Total Score:** 40/40
- **Latency:** 14.95s | **Tokens:** 7224
- **Judge Reasoning:** *The AI's response is perfectly correct, clearly explains the issue, and provides actionable, numbered steps. It adheres to all formatting rules, including bolding for system names and specific values. The escalation logic is sound, asking for more details if the initial solution doesn't work. The tone is professional and empathetic. It fully aligns with the ground truth and context.*

**AI Response:**
```
Hi Tester,

This issue occurs because a **UDC (User Defined Code)** validation rule is treating the field as mandatory, which blocks blank or empty values even when they're needed in the **Address Book**.

To resolve this, please follow these steps:

1. Navigate to the **UDC Maintenance** screen for the specific field you're updating.
2. Check the validation table to confirm whether a **Blank** row is permitted.
3. Apply the system fix to disable the mandatory requirement for that module.
4. Refresh the **Address Book**, then save the record with the blank value.

If you're still unable to save the blank field after these steps, please let me know the exact field name so I can investigate further.
```
---

#### Case ZT-006: I need to remove a member from the eligibility file. How do ...
- **Total Score:** 23/40
- **Latency:** 15.26s | **Tokens:** 7609
- **Judge Reasoning:** *The AI's response is fundamentally incorrect and unfaithful to the provided KB context. The ground truth explicitly states that member removals must be processed through a formal request to the 'Data Management team'. The AI, however, states 'I will apply the update in MemberPlus' and asks the user to provide details to it, completely bypassing the correct internal process outlined in the KB. This is a critical error in correctness and faithfulness, leading to an incorrect solution and escalation logic. While the tone is empathetic and the format is mostly adhered to, the core information is wrong.*

**AI Response:**
```
Hi Tester,

Removing a member from the eligibility file is a standard update in our benefits system, typically needed when eligibility ends due to termination or other status changes. This adjustment is made directly in **MemberPlus** to ensure the next generated eligibility file reflects the correct status and avoids downstream processing errors.

To process this request, please follow these steps:

1. Collect the **member's full name**, **ID number**, **effective date of removal**, and **reason**.
2. Reply to this message with those exact details.
3. I will apply the update in **MemberPlus** and send you confirmation once the eligibility file is corrected.

Let me know the details so I can complete this for you right away.
```
---

#### Case ZT-007: Something is broken in the system....
- **Total Score:** 21/40
- **Latency:** 11.96s | **Tokens:** 7087
- **Judge Reasoning:** *The user query is extremely vague ('Something is broken in the system'). The AI incorrectly attempts to provide troubleshooting steps based on assumptions (e.g., 'high urgency', 'temporary service disruptions') instead of clarifying the issue. The ground truth correctly identifies the need for more details (application, error message, etc.) before providing a solution. The AI's escalation logic is flawed as it tries to solve rather than clarify first. While the steps are actionable, they are not relevant without more information. The tone is professional, but the assumption of 'high urgency' is not ideal.*

**AI Response:**
```
Hi Tester,

I understand you're reporting that something is broken in the system with high urgency. This is often caused by temporary service disruptions, stale cached credentials, or a recent backend update affecting connectivity.

To troubleshoot this, please follow these steps:

1. Close all active applications and **restart your computer** completely.
2. After reboot, open the **PCBA ITSM Portal** from your desktop shortcut.
3. Navigate to **System Status** and check for any active incidents or outages.
4. If no outages are listed, try accessing the specific application again and note any exact error message that appears.

If the issue continues after these steps, please reply with the specific error or application affected so I can escalate immediately.
```
---

#### Case ZT-008: I am getting this error when opening Outlook. I have attache...
- **Total Score:** 19/40
- **Latency:** 8.5s | **Tokens:** 6979
- **Judge Reasoning:** *The AI's response is fundamentally flawed because it failed to process the attached screenshot (as indicated by `ATTACHMENT INFO: None`). Instead of acknowledging this and asking for the error message, it *guessed* an 'authentication error' and provided a solution for it. The `GROUND TRUTH` explicitly states the screenshot showed 'Error Code: 0x80040115', which typically requires a different solution (OST file recreation) than what the AI provided (Credential Manager). Therefore, the AI's diagnosis and solution are incorrect for the actual error. Its multimodal handling is a failure as it did not correctly handle the missing attachment information. Ambiguity handling is also poor as it made an assumption instead of clarifying.*

**AI Response:**
```
Hi Tester,

It looks like you're encountering an authentication error when launching Outlook, which is typically caused by stale or corrupted credentials cached in Windows Credential Manager after a password change or profile sync issue.

To resolve this, please follow these steps:

1. Completely close **Outlook** and all other **Office** applications.
2. Open the Windows **Control Panel** and navigate to **Credential Manager**.
3. Under **Windows Credentials**, remove all entries starting with **MicrosoftOffice16** or containing your email address.
4. Restart **Outlook** and sign in with your **test@pcbapps.com** credentials when prompted.

If the error continues after these steps, please reply with the exact error text from the screenshot and I'll assist further.
```
---


