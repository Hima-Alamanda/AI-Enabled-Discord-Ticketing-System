# AI Evaluation Report: Gemini vs. Grok (Zoho Ticket)

**Date:** 2026-03-31 16:20:27
**Dataset:** Zoho Ticket (7 test cases)

## 1. Quality Metrics (0-5 Scale)
Each model's response is scored by an independent AI Auditor based on this scale:

| Score | Rating | Description |
|:---:|:---|:---|
| **5** | **Excellent** | Fully correct, clear, well-structured, and follows all required rules |
| **4** | **Good** | Correct and helpful, with only minor issues in wording, tone, or formatting. |
| **3** | **Acceptable** | Mostly correct, but missing some details or clarity. |
| **1-2** | **Poor** | Contains important mistakes, unclear steps, or does not fully address the user’s issue. |
| **0** | **Failure** | Incorrect, misleading, made up facts, or failed to answer the query. |

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

| model               |   correctness |   faithfulness |   actionability |   format_adherence |   ambiguity |   multimodal |   escalation |   empathy |
|:--------------------|--------------:|---------------:|----------------:|-------------------:|------------:|-------------:|-------------:|----------:|
| Gemini 2.5 Pro      |          3.29 |           2.71 |            3.29 |               1.43 |        4.57 |         4.29 |         3.86 |      4.43 |
| Grok 4.20 Reasoning |          2.71 |           2    |            4    |               0    |        4.43 |         4.29 |         3.71 |      4.57 |

## 2. Performance & Cost Metrics (Avg)

| model               |   Avg Latency (s) |   Input Tokens |   Output Tokens |   Total Tokens |
|:--------------------|------------------:|---------------:|----------------:|---------------:|
| Gemini 2.5 Pro      |             23.75 |        2703.29 |          388.57 |        6126.86 |
| Grok 4.20 Reasoning |             16.46 |        3050.43 |          461.86 |        7500.86 |

## 3. Key Insights

### Gemini 2.5 Pro
- **Strength:** Ambiguity (4.57)
- **Potential Area for Improvement:** Format_adherence (1.43)
- **Avg Turnaround:** 23.75s
- **Avg Tokens:** 6126 (Input: 2703, Output: 388)

### Grok 4.20 Reasoning
- **Strength:** Empathy (4.57)
- **Potential Area for Improvement:** Format_adherence (0.0)
- **Avg Turnaround:** 16.46s
- **Avg Tokens:** 7500 (Input: 3050, Output: 461)

## 4. Case-by-Case Breakdown

### Model: Gemini 2.5 Pro
#### Case ZT-001: I am getting an error message during end of month reporting ...
- **Total Score:** 8/40
- **Latency:** 32.06s | **Tokens:** 5343
- **Judge Reasoning:** *The AI failed to provide a solution despite the ground truth indicating a clear cause and resolution. Instead, it asked a clarifying question ('Which end-of-month process is generating the error?') which deviates from the expected action of 'PROVIDE_SOLUTION'. The question itself is not incorrect but is unnecessary given the ground truth's direct answer. It did not adhere to the required format and provided no actionable steps.*

**AI Response:**
```
Which end-of-month process is generating the error?
```
---

#### Case ZT-002: I cannot access any tickets for DC33 or JFK in Zoho with my ...
- **Total Score:** 33/40
- **Latency:** 25.33s | **Tokens:** 5956
- **Judge Reasoning:** *The AI correctly identified the issue as a permissions problem requiring escalation, which aligns with the ground truth. It also correctly decided to escalate and create a ticket. The tone is empathetic. However, it completely failed to adhere to the required output format, missing all four specified headers. Actionability is rated 3 because while the AI outlines its own next steps, it doesn't provide numbered steps for the user, which is appropriate given the issue but still not 'clear, easy, numbered steps' for the user to perform.*

**AI Response:**
```
Hi Tester,

I understand you're getting an "access denied" error when trying to view tickets for the **DC33** and **JFK** departments in **Zoho**. This issue typically occurs when a user's profile permissions are not correctly configured to grant visibility into those specific ticket groups.

Since this requires an adjustment to your backend permissions, I will need to escalate this to our application administrators. They will review your account and grant you the necessary access to the **DC33** and **JFK** queues.

I will open a ticket to track this request, and you will be notified as soon as your access has been restored.
```
---

#### Case ZT-003: Retirees who are under the HMO plan are still showing as act...
- **Total Score:** 29/40
- **Latency:** 24.34s | **Tokens:** 7354
- **Judge Reasoning:** *The AI correctly identified that the user cannot self-solve this issue and that it requires escalation, which aligns with the KB stating 'Support corrected'. It also correctly asked for necessary information (Member IDs) to facilitate the escalation. However, the AI introduced details about the 'backend processing error' as the cause and 'manual intervention from our data administration team' as the resolution method, which are not present in the retrieved KB context, impacting faithfulness and correctness. The response also failed to adhere to the required output format by not using the specified headers.*

**AI Response:**
```
Hi Tester,

I understand you're seeing retirees under the HMO plan incorrectly listed as active on the eligibility file. This issue typically arises from a backend processing error where the system fails to correctly apply the termination status to the member's record before the eligibility file is generated.

Correcting this requires manual intervention from our data administration team, as they need to access the benefits system directly to force the update. To move forward, I will need to escalate this issue. Could you please provide the specific Member IDs for the retirees who are affected?

Once I have those details, I will create a ticket and escalate it to the appropriate team for immediate correction.
```
---

#### Case ZT-004: The address book is not letting me add a blank value to a fi...
- **Total Score:** 19/40
- **Latency:** 19.32s | **Tokens:** 5809
- **Judge Reasoning:** *The AI's explanation for the issue ('by design', 'required fields') and proposed resolution ('change request' from 'development team') directly contradicts the ground truth, which states 'Support confirmed this should be allowed and applied the fix'. This indicates a misunderstanding of the problem's nature and resolution. The AI hallucinates the cause and resolution. It also fails to adhere to the required output format and chooses an incorrect escalation path (offering to create a change request ticket instead of providing a solution or confirming a fix).*

**AI Response:**
```
Hi Tester,

I understand you're unable to add a blank value to a field in the address book. This is typically by design, as many fields are configured as 'required' to ensure data integrity and prevent essential information from being left empty.

Allowing a blank value for a specific field requires a configuration change from our development team to adjust its validation rules. I can submit a ticket on your behalf to have them review this as a potential change request.

Would you like me to proceed with creating that ticket for you?
```
---

#### Case ZT-005: We need to close the Daiwa fiscal year end. What is the proc...
- **Total Score:** 39/40
- **Latency:** 16.75s | **Tokens:** 6089
- **Judge Reasoning:** *The AI correctly identifies that the fiscal year-end close is a complex process requiring specialist intervention, aligning with the implication in the ground truth that 'Support walked through' it, suggesting it's not a self-service task. It offers a clear, actionable escalation path by creating a high-priority ticket. While the KB doesn't explicitly state it's 'not user-facing' or 'must be performed by a specialist,' this is a very reasonable and likely accurate inference for such a critical financial operation, hence a 4 for faithfulness. The AI correctly determines that a direct resolution with steps is not possible and thus doesn't apply the resolution format, which is appropriate. The tone is empathetic and professional.*

**AI Response:**
```
Hi Tester,

I understand you're looking for the procedure for the Daiwa fiscal year-end closing. This is a critical and sensitive financial operation that is managed by a dedicated team to ensure data integrity and compliance. Due to the complexity involved, this process isn't documented as a standard user-facing procedure.

The year-end close must be performed by a specialist from our **Finance Systems** team. I can create a high-priority service request and assign it directly to them to coordinate and execute this process with you.

Would you like me to proceed with creating and assigning that ticket for you?
```
---

#### Case ZT-006: I need to remove a member from the eligibility file. How do ...
- **Total Score:** 27/40
- **Latency:** 29.49s | **Tokens:** 7046
- **Judge Reasoning:** *The AI's response provides actionable steps but introduces specific names (Ashok Chinthala, Debiprasad Mohanty) and a 'Data Management team' that are not present in the provided KB context, indicating a hallucination. It also misses the 'effective date' mentioned in the ground truth for the termination request. Crucially, it failed to adhere to the required output format by not including the specified headers.*

**AI Response:**
```
Hi Tester,

I can certainly clarify the process for handling a member removal from an eligibility file. These types of data modifications are managed by a dedicated team to ensure data integrity and maintain a clear audit trail, which is why there isn't a direct user-facing tool for this task.

To process this request, please follow the internal procedure below:

1.  Ensure you have the original request from the client, typically in an email format.
2.  Forward the complete email request to our **Data Management** team. Based on historical tickets, the primary contacts for this are **Ashok Chinthala** and **Debiprasad Mohanty**.
3.  Before forwarding, please verify the request clearly includes the member's full name and unique Member ID to ensure the correct record is removed.

The Data Management team will then process the removal and confirm once it has been completed. If you have any further questions, please don't hesitate to ask.
```
---

#### Case ZT-007: Something is broken in the system....
- **Total Score:** 40/40
- **Latency:** 18.98s | **Tokens:** 5291
- **Judge Reasoning:** *The AI correctly identified the vagueness of the user's query and asked appropriate clarifying questions, aligning perfectly with the ground truth and expected action. The tone is empathetic and professional. The numbered questions make it actionable for the user. Format adherence is 5 as no specific headers were expected for a clarification response.*

**AI Response:**
```
Hi Tester,

I understand you're experiencing an issue with one of our systems. To help me investigate and resolve this for you as quickly as possible, I'll need a little more information to identify the specific application and the nature of the problem.

Could you please provide a few more details?

1.  Which application are you having trouble with?
2.  What is the exact error message you are receiving?
3.  If possible, could you please provide a screenshot of the issue?

Once I have these details, I can provide you with the correct resolution steps.
```
---


### Model: Grok 4.20 Reasoning
#### Case ZT-001: I am getting an error message during end of month reporting ...
- **Total Score:** 34/40
- **Latency:** 14.5s | **Tokens:** 6885
- **Judge Reasoning:** *The AI correctly identified plausible causes (unbalanced entries, record lock) and provided resolution steps that align with the ground truth's core resolution of deleting unposted/erroneous entries and reposting. The steps are actionable and the escalation logic is sound. However, it failed to adhere to the required output format by not using the specified headers.*

**AI Response:**
```
Hi Tester,

This error during end of month reporting when posting JE batches, where the batch shows **Error** status with a difference amount, is typically caused by unbalanced journal entries (debits not equaling credits) or a record lock from another user. This is a common issue in **JDE** during period-end processing.

To resolve this, please follow these steps:

1. Log into **JDE** and open the **Work Center**.
2. Locate the failed batch and review the detailed error message (commonly 'Poster Out of Balance').
3. If it indicates a record lock, ask the user currently holding the record to exit their session completely.
4. Open the batch in the journal entry screen, identify and delete any unbalanced or erroneous lines causing the difference.
5. Save the batch and attempt to post it again.

If the batch still fails after these steps, please let me know the exact error text from the Work Center and I can guide you further or escalate to the JDE team.
```
---

#### Case ZT-002: I cannot access any tickets for DC33 or JFK in Zoho with my ...
- **Total Score:** 32/40
- **Latency:** 14.34s | **Tokens:** 6241
- **Judge Reasoning:** *The AI correctly identified the cause (permissions) and the escalation path aligns with the ground truth's resolution. However, the initial troubleshooting steps (log out/in, incognito) are unlikely to resolve a permissions issue directly. The response failed to adhere to the required format by not using the specified headers.*

**AI Response:**
```
Hi Tester,

I understand you're getting an access denied error when trying to view any DC33 or JFK tickets in **Zoho**. This is typically caused by your user profile missing the required department or client-specific permissions that were recently updated in the backend **Zoho Desk** configuration.

To resolve this, please follow these steps:

1. Completely log out of **Zoho** and close all browser windows.
2. Open an incognito/private browsing window and navigate to **zoho.com**.
3. Log in with your **test@pcbapps.com** credentials and go directly to the **Tickets** tab.
4. Use the filter to select **DC33** or **JFK** and check if the tickets now load.

If you still receive the access denied message after these steps, please let me know the exact error text and I can escalate this to our Zoho administrator to update your permissions.
```
---

#### Case ZT-003: Retirees who are under the HMO plan are still showing as act...
- **Total Score:** 23/40
- **Latency:** 14.39s | **Tokens:** 7528
- **Judge Reasoning:** *The AI's response provides a plausible technical solution with clear steps. However, it completely hallucinates the cause and resolution steps as they are not present in the provided KB context. The KB only states that 'Support corrected the eligibility file records', implying an internal action, whereas the AI provides steps for the user to perform. This makes the response unfaithful to the KB and questionable in terms of correctness regarding the appropriate actor for the fix. It also failed to adhere to the required output format headers.*

**AI Response:**
```
Hi Tester,

Retirees under the **HMO** plan are continuing to appear as active on the eligibility file because the termination or plan-end record was not fully processed, often due to a missing or miscalculated eligibility end date that prevents the nightly export from reflecting the correct status.

To resolve this, please follow these steps:

1. Log into the **Benefits Administration System**.
2. Go to **Member Search**, enter the retiree's **P/N**, and open their record.
3. Navigate to the **Coverage Details** tab, locate the **HMO** plan line, and update the **Status** to **Terminated**.
4. Enter the correct **Eligibility End Date** (typically the retirement effective date) and save the record.
5. Run **Generate Eligibility File** from the **Reports** menu and verify the retiree no longer shows as active.

If the retirees still appear active after regenerating the file, please let me know the specific P/Ns affected so I can review the backend records.
```
---

#### Case ZT-004: The address book is not letting me add a blank value to a fi...
- **Total Score:** 21/40
- **Latency:** 15.58s | **Tokens:** 7937
- **Judge Reasoning:** *The AI's response contradicts the ground truth. The ground truth states that blank values *should* be allowed and a fix was applied. The AI's response provides reasons why blank values might *not* be allowed (UDC table, required field validation) and suggests workarounds or configuration changes, which is not aligned with the system's intended behavior after the fix. The format adherence is also poor as it did not use the specified headers.*

**AI Response:**
```
Hi Tester,

I understand the **Address Book** is blocking you from saving a blank value in a field. This usually occurs when the field is tied to a UDC table or has a required-field validation rule enabled to maintain data integrity, which is the default behavior in the current configuration.

To resolve this, please follow these steps:

1. Open the **Address Book** module and locate the affected record.
2. Switch to **Edit** mode and click the **Field Help** or **Visual Assist** button on the restricted field.
3. If a UDC search window appears, check whether a blank or "N/A" option exists; if not, enter a single space as a temporary placeholder and attempt to save.
4. If the error persists, go to **System Setup** > **UDC Maintenance**, search for the related code type, and verify if a blank value row needs to be added (requires appropriate permissions).

If these steps don't allow the blank value or you receive a specific error message, let me know the exact field name and I'll investigate further.
```
---

#### Case ZT-005: We need to close the Daiwa fiscal year end. What is the proc...
- **Total Score:** 25/40
- **Latency:** 21.69s | **Tokens:** 8719
- **Judge Reasoning:** *The AI hallucinated specific steps for the fiscal year-end close that are not present in the provided ground truth or KB context. The ground truth only states that 'Support walked through the required steps' but does not list them. The AI also failed to adhere to the required output format by not using the specified headers.*

**AI Response:**
```
Hi Tester,

The Daiwa fiscal year-end close is a high-priority finance operation that requires system stability over the next two weeks, as flagged in the business-wide notice. This period focuses on finalizing all transactions and reports, and disruptions often stem from unposted entries, access conflicts, or unmonitored application errors.

To support the close process, please follow these steps:

1. Confirm with the finance team that all transactions are posted in the **Daiwa accounting system**.
2. Open **Control Panel** > **Administrative Tools** and run a quick **Event Viewer** check for any errors under the **Application** log related to finance apps.
3. Log into the **Daiwa portal** and navigate to **Period Close** > **Run Reconciliation** to validate balances.
4. Once verified, execute the **Fiscal Year Close** function and export the final **trial balance report**.
5. Return any related hardware or access tokens to the **IT Assets desk** if team members are changing roles during this close.

If the close encounters any system errors or you need a specific access adjustment, reply with the exact message you're seeing and I'll assist further.
```
---

#### Case ZT-006: I need to remove a member from the eligibility file. How do ...
- **Total Score:** 34/40
- **Latency:** 20.25s | **Tokens:** 8366
- **Judge Reasoning:** *The AI's response correctly identifies the process for removing a member from the eligibility file, aligning with the ground truth. It provides clear, actionable, numbered steps for the user to follow. The tone is professional and helpful, even offering to assist with initial logging. However, it failed to adhere to the specified output format by not including the required headers (Issue Analysis, Cause, Resolution Steps, Next Steps). The mention of a specific ticket number is an embellishment not directly from the provided KB snippet, leading to a slightly reduced faithfulness score, though it doesn't detract from the core solution.*

**AI Response:**
```
Hi Tester,

Removing a member from the eligibility file is a standard update to maintain accurate benefits data, typically requested when a member's status changes. Our team processes these by updating the source data before the next file generation cycle, exactly as handled in prior tickets such as 111007000021084002.

To process this request, please follow these steps:

1. Collect the member's **full name**, **Member ID**, **DOB**, **effective removal date**, and reason.
2. Create a new email using the exact subject **"Request to take off eligibility file"**.
3. Address it to **support@pcbapps.com** (or the client contact if this is inbound) and include all details in the body.
4. Send the email so the Operations team can log the ticket and apply the update to the master eligibility file.
5. Monitor the ticket for confirmation once the revised file is generated and tested.

If you have the member details ready or this is an urgent client request, share them here and I'll handle the initial logging for you. Let me know how else I can help.
```
---

#### Case ZT-007: Something is broken in the system....
- **Total Score:** 11/40
- **Latency:** 14.44s | **Tokens:** 6830
- **Judge Reasoning:** *The user query is extremely vague. The ground truth explicitly states that the bot must ask clarifying questions *before attempting to provide a solution*. The AI, however, immediately jumps to assuming potential causes ('backend service update or when local cache and session data become corrupted' - a hallucination as it's not grounded in context) and provides troubleshooting steps. While it eventually asks for more details, it does so *after* attempting a solution, which contradicts the expected behavior. It also failed to use the required headers.*

**AI Response:**
```
Hi Tester,

I understand you're seeing a generic "something is broken" issue in the system. This usually occurs after a backend service update or when local cache and session data become corrupted, preventing normal connectivity.

To resolve this, please follow these steps:

1. Completely close all applications and **restart** your computer.
2. After reboot, open **Task Manager** (press **Ctrl + Shift + Esc**) and end any lingering processes related to **PCB Apps** or your browser.
3. Re-launch the system and test the affected area again.
4. If an error appears, note the exact message or code.

If the issue persists after these steps, please reply with more details on the specific error or area that's broken so I can provide a targeted fix.
```
---


