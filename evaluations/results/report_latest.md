# AI Evaluation Report: Gemini vs. Grok (Zoho Ticket)

**Date:** 2026-03-31 15:48:42
**Dataset:** Zoho Ticket (7 test cases)

## 1. Quality Metrics (0-5 Scale)
Each model's response is scored by an independent AI Auditor based on this scale:

| Score | Rating | Description |
|:---:|:---|:---|
| **5** | **Excellent** | Perfect answer, follows all rules, tone is ideal. |
| **4** | **Good** | Accurate and helpful with minor style or formatting oversights. |
| **3** | **Acceptable** | Generally correct but misses some details. |
| **1-2** | **Poor** | Significant errors, confusing steps, or missed the user's intent. |
| **0** | **Failure** | Completely incorrect, hallucinated facts, or ignored the query. |

### The 8 Quality Categories
1. **Correctness:** Accuracy vs historical Zoho resolution.
2. **Faithfulness:** Factuality (no hallucinations/invented facts).
3. **Actionability:** Clarity of step-by-step instructions.
4. **Format Adherence:** Use of required headers (Analysis, Cause, etc.).
5. **Ambiguity:** Handling vague queries (correctly asking for info first).
6. **Multimodal:** Understanding images/screenshots attached to tickets.
7. **Escalation:** Correct decision to solve vs raise a human ticket.
8. **Empathy:** Professional, warm, and helpful tone.

## 2. Quality Scores Summary

| model               |   correctness |   faithfulness |   actionability |   format_adherence |   ambiguity |   multimodal |   escalation |   empathy |
|:--------------------|--------------:|---------------:|----------------:|-------------------:|------------:|-------------:|-------------:|----------:|
| Gemini 2.5 Pro      |          3.5  |           3.83 |            3.33 |               0.83 |         4.5 |          5   |         3.67 |      4.83 |
| Grok 4.20 Reasoning |          2.67 |           2.5  |            3.33 |               0    |         4   |          2.5 |         3.17 |      4.67 |

## 2. Performance & Cost Metrics (Avg)

| model               |   Avg Latency (s) |   Input Tokens |   Output Tokens |   Total Tokens |
|:--------------------|------------------:|---------------:|----------------:|---------------:|
| Gemini 2.5 Pro      |             25.43 |        2648.83 |          387.67 |        5954.67 |
| Grok 4.20 Reasoning |             15.65 |        3037    |          443.5  |        7098.5  |

## 3. Key Insights

### Gemini 2.5 Pro
- **Strength:** Multimodal (5.0)
- **Potential Area for Improvement:** Format_adherence (0.83)
- **Avg Turnaround:** 25.43s
- **Avg Tokens:** 5954 (Input: 2648, Output: 387)

### Grok 4.20 Reasoning
- **Strength:** Empathy (4.67)
- **Potential Area for Improvement:** Format_adherence (0.0)
- **Avg Turnaround:** 15.65s
- **Avg Tokens:** 7098 (Input: 3037, Output: 443)

## 4. Case-by-Case Breakdown

### Model: Gemini 2.5 Pro
#### Case ZT-001: I am getting an error message during end of month reporting ...
- **Total Score:** 17/40
- **Latency:** 39.72s | **Tokens:** 6010
- **Judge Reasoning:** *The AI asked for clarification instead of providing a solution, which was the expected action based on the ground truth. While asking for clarification is a form of ambiguity handling, the user's query was specific enough about 'posting JE batches' that a solution should have been attempted. The AI's question also included a less relevant option ('specific financial report') given the user's description of a batch posting error.*

**AI Response:**
```
Is this error occurring during the JDE batch post process (R09801), or is it with a specific financial report?
```
---

#### Case ZT-002: I cannot access any tickets for DC33 or JFK in Zoho with my ...
- **Total Score:** 33/40
- **Latency:** 21.4s | **Tokens:** 5418
- **Judge Reasoning:** *The AI correctly identified the issue as a permissions problem requiring escalation to an administrator. It offered to create a ticket, which is the correct escalation path. The tone is empathetic and professional. However, it failed to adhere to the required output format by not including the four specified headers. Actionability is rated 3 because while it correctly identifies the next step for itself (creating a ticket), it doesn't provide numbered steps for the user, which is appropriate given the nature of the issue but still a deviation from the 'numbered steps' expectation for actionability.*

**AI Response:**
```
Hi Tester,

I understand you're getting an "access denied" error when trying to view tickets for DC33 and JFK in **Zoho**. This issue typically points to a permissions misconfiguration within your user profile, which restricts your access to specific departments or ticket categories.

Since account permissions are managed on the backend by our administrators, I will need to escalate this issue to have your access rights reviewed and corrected.

I can create a ticket to get this process started for you. Would you like me to proceed?
```
---

#### Case ZT-003: Retirees who are under the HMO plan are still showing as act...
- **Total Score:** 30/40
- **Latency:** 26.11s | **Tokens:** 6438
- **Judge Reasoning:** *The AI correctly identifies the issue and the need for specialist intervention, aligning with the KB's implication that 'Support corrected' the records. The escalation logic is sound as it's likely not a user-fixable issue. However, the AI did not use the required headers, and the explanation of the cause is an inference rather than directly from the KB. While it offers an actionable path (escalation), it doesn't provide steps for the user to perform a fix themselves, which might be expected from 'PROVIDE_SOLUTION'.*

**AI Response:**
```
Hi Tester,

I understand you're finding that retirees on the HMO plan are incorrectly showing as active on the eligibility file. This issue typically arises from a data processing discrepancy where the system hasn't correctly updated a member's status after a change, such as a plan termination or transition.

Correcting this requires a manual data update by a specialist with backend access to the eligibility system. Since this isn't a fix that can be performed from the user interface, I will need to escalate this issue for you.

I can create a ticket and escalate this to the data management team to investigate and correct the records. Would you like me to proceed?
```
---

#### Case ZT-005: We need to close the Daiwa fiscal year end. What is the proc...
- **Total Score:** 24/40
- **Latency:** 19.25s | **Tokens:** 6094
- **Judge Reasoning:** *The AI correctly identified the user's need but stated it could not provide the specific steps due to the sensitive nature and lack of detailed documentation in its knowledge base. This contradicts the 'GROUND TRUTH' which states 'Support walked through the required steps and timing with the team to complete the close successfully,' implying that the information *should* be available to 'Support' (which the AI is acting as). Therefore, while the AI's decision to escalate is appropriate given its stated limitations, it fails to meet the expectation of providing a solution as per the ground truth. The AI did not adhere to the required output format headers. Faithfulness is rated 3 because while it's faithful to its *stated* internal knowledge limitation, we cannot verify if its KB *actually* lacks this information, especially given the ground truth implies it should be available.*

**AI Response:**
```
Hi Tester,

I understand you're looking for the procedure for the Daiwa fiscal year-end close. This is a critical and sensitive financial process that is carefully managed to ensure the integrity of the system's data. The documentation on record is a high-level notification regarding the importance of this period, but it does not contain the specific technical steps for execution.

Due to the sensitive nature of this task, the year-end close is handled directly by our dedicated **Financial Systems team**. They have the specialized access and tools required to perform this operation correctly.

I can create a high-priority service request and assign it to the **Financial Systems team** to begin this process for you. Would you like me to proceed?
```
---

#### Case ZT-006: I need to remove a member from the eligibility file. How do ...
- **Total Score:** 33/40
- **Latency:** 24.08s | **Tokens:** 6128
- **Judge Reasoning:** *The AI provides clear, actionable steps to address the user's request, aligning with the ground truth's instruction to submit a termination request. It correctly identifies the need to involve support. However, it misses the 'effective date' detail from the ground truth and completely fails to adhere to the required output format headers.*

**AI Response:**
```
Hi Tester,

I understand you need to process a member removal from an eligibility file. To ensure data integrity and maintain a clear audit trail, these types of data modifications are managed directly by our technical teams.

To initiate this request, please follow these steps:

1.  Compose an email to our **Support Desk** at `support@pcbapps.com`.
2.  Use the subject line: **Eligibility File - Member Removal Request**.
3.  In the body of the email, please provide the member's full name, their internal ID, and a brief reason for the removal.

Once this request is submitted, a ticket will be generated and our team will process the removal from the file.
```
---

#### Case ZT-007: Something is broken in the system....
- **Total Score:** 40/40
- **Latency:** 22.01s | **Tokens:** 5640
- **Judge Reasoning:** *The user query was extremely vague, and the AI correctly identified this. It followed the ground truth's instruction to ask clarifying questions, specifically asking for the system name, error messages, and the task being performed, which aligns well with the expected clarification points. The tone is empathetic and professional, and the questions are presented clearly. The escalation logic correctly led to a clarification request.*

**AI Response:**
```
Hi Tester,

I understand you're experiencing an issue with one of our systems. To help you resolve this as quickly as possible, I'll need a bit more specific information about the problem you're encountering.

Could you please provide the following details?

1.  The name of the application or system that is broken.
2.  Any specific error messages you are seeing on the screen.
3.  A brief description of the task you were performing when the issue occurred.

Once I have these details, I can provide you with the correct troubleshooting steps.
```
---


### Model: Grok 4.20 Reasoning
#### Case ZT-001: I am getting an error message during end of month reporting ...
- **Total Score:** 27/40
- **Latency:** 12.89s | **Tokens:** 7099
- **Judge Reasoning:** *The AI's resolution steps are correct and align well with the ground truth's resolution. However, the AI's stated cause ('batch is out of balance') is a common reason for the symptom but not strictly identical to the ground truth's specific cause ('unposted entries'). This slightly impacts faithfulness. The AI failed to adhere to the required output format by not including the specified headers.*

**AI Response:**
```
Hi Tester,

This error during end of month JE batch posting in **JDE** typically occurs when the batch is out of balance, meaning the debits and credits do not match, which leaves a visible difference amount and sets the batch status to Error.

To resolve this, please follow these steps:

1. Log into **JDE** and open the **Work Center**.
2. Locate the failed batch and review the full error details for the exact difference amount.
3. Open the batch in the **Journal Entry** program and scan for unbalanced or incomplete entries.
4. **Delete** the entries causing the imbalance.
5. Save the batch and attempt to **post** it again.

If the batch still fails to post after these steps, let me know the exact error text so I can assist further.
```
---

#### Case ZT-002: I cannot access any tickets for DC33 or JFK in Zoho with my ...
- **Total Score:** 32/40
- **Latency:** 14.75s | **Tokens:** 6378
- **Judge Reasoning:** *The AI correctly identified the likely cause and provided relevant troubleshooting steps, with a clear escalation path if those steps fail. However, it failed to adhere to the required output format by not including the specified headers. The troubleshooting steps are good first steps, but a direct permission issue would ultimately require backend intervention, which the AI correctly identifies as a next step.*

**AI Response:**
```
Hi Tester,

I understand you're getting an access denied error when trying to view any tickets for DC33 or JFK in **Zoho**. This is typically caused by your user account missing the required department or group permissions for those specific clients in the Zoho Desk configuration.

To resolve this, please try these steps first:

1. Completely log out of **Zoho** by clicking your profile icon in the top right and selecting **Sign Out**.
2. Clear your browser cache and cookies specifically for zoho.com.
3. Log back in using your **test@pcbapps.com** credentials.
4. Go to the **Tickets** module, select **All Tickets**, and use the filter to search for DC33 or JFK.

If you still receive the access denied error after these steps, the permissions will need to be updated on the backend. Let me know the result and I'll take care of it for you.
```
---

#### Case ZT-003: Retirees who are under the HMO plan are still showing as act...
- **Total Score:** 19/40
- **Latency:** 17.92s | **Tokens:** 8079
- **Judge Reasoning:** *The AI's response deviates significantly from the ground truth. The ground truth states that 'Support corrected the eligibility file records,' implying an internal support action. The AI, however, provides detailed steps for the user to perform the correction themselves in an invented 'Benefits Administration System' with specific tabs and fields not present in the KB. This constitutes a major hallucination (faithfulness=0) and a mismatch with the 'Golden Answer' (correctness=1). The actionability is low because the system and steps are invented. The required headers were not used (format_adherence=0).*

**AI Response:**
```
Hi Tester,

This issue typically occurs when a retiree's HMO plan termination or status change has not been fully processed in the eligibility system, leaving the record flagged as active when the file is generated.

To correct this, please follow these steps:

1. Log into the **Benefits Administration System**.
2. Search for the affected retiree using their **Member Number** or name in the main search bar.
3. Open their record and navigate to the **Eligibility** tab, then select the **HMO Plan** line.
4. Enter the correct **Termination Date**, change the **Status** to **Retired/Inactive**, and ensure the **Retiree Flag** is set to Yes.
5. Click **Save Changes**, then go to **Reports > Generate Eligibility File** and run a fresh export for the current period.
6. Download and review the new eligibility file to confirm the retirees no longer appear as active under HMO.

If the retirees are still showing as active after refreshing the file, please reply with a couple of example member numbers and I'll escalate this to the configuration team for a deeper review.
```
---

#### Case ZT-004: The address book is not letting me add a blank value to a fi...
- **Total Score:** 16/40
- **Latency:** 17.82s | **Tokens:** 7728
- **Judge Reasoning:** *The AI's proposed resolution steps (adding a space, modifying UDC) are incorrect and do not align with the ground truth, which states that support applied a fix to allow blank values. While the AI's explanation for the cause is plausible, the resolution is not what actually happened. It also failed to adhere to the specified output format headers. It did, however, handle ambiguity well by asking for more information if its initial suggestions failed, and maintained an empathetic tone.*

**AI Response:**
```
Hi Tester,

I understand the address book is blocking you from saving a blank value in a field. This usually happens because the field is either marked as required or linked to a UDC table that doesn't contain a blank entry, which is a standard data validation rule in the system.

To resolve this, please follow these steps:

1. Open the **Address Book** module and locate the record and specific field.
2. Try entering a single **space** character in the field as a temporary workaround.
3. If you have setup access, navigate to **Setup** > **User Defined Codes**, select the related **UDC table**, and add a blank or "N/A" entry.
4. Return to the record, clear the field again, save, and test.

If the issue continues after these steps, please reply with the exact field name and I'll check the configuration for you.
```
---

#### Case ZT-006: I need to remove a member from the eligibility file. How do ...
- **Total Score:** 35/40
- **Latency:** 17.51s | **Tokens:** 6756
- **Judge Reasoning:** *The AI correctly identifies the process for removing a member from the eligibility file, providing clear, actionable steps including specific details needed and the email address for submission. It is faithful to the KB by elaborating on the 'submit a termination request' instruction. The tone is professional and helpful. However, it completely failed to adhere to the required output format by not including the specified headers.*

**AI Response:**
```
Hi Tester,

Removing a member from the eligibility file is a standard update to reflect status changes such as termination or corrections in the benefits system. This prevents ongoing inclusion in generated files while maintaining compliance and data integrity, similar to prior requests we've handled for your team.

To process this request, please follow these steps:

1. Gather the member's **full name**, **member ID**, **date of birth**, **effective removal date**, and the **reason for removal**.
2. Compose an email to **support@pcbapps.com** using the subject line **Request to take off eligibility file**.
3. Include all collected details in the email body and attach any supporting documentation such as termination notices.
4. Send the email—our team will confirm receipt and schedule the update for the next file generation cycle.

Let me know if you have the member details ready or if the request doesn't go through so I can assist further.
```
---

#### Case ZT-007: Something is broken in the system....
- **Total Score:** 8/40
- **Latency:** 13.01s | **Tokens:** 6551
- **Judge Reasoning:** *The user query is extremely vague ('Something is broken in the system'). The ground truth explicitly states the bot *must* ask clarifying questions. The AI fails to do this, instead making assumptions about the problem (stale browser, ITSM platform) and providing a resolution. This is a critical failure in ambiguity handling and escalation logic. While the steps provided are clear, they are for an assumed problem, not the user's stated one. The required format headers were also not used.*

**AI Response:**
```
Hi Tester,

I understand you're seeing something broken in the system, which is commonly caused by a stale browser session, cached credentials, or a temporary backend service hiccup in our ITSM platform.

To resolve this, please follow these steps:

1. Fully close all browser windows and reopen your browser in **Incognito/Private mode**.
2. Navigate to the **PCB Apps portal** and attempt to log in again.
3. If the issue persists, go to your browser settings and clear **cache and cookies** specifically for pcbapps.com.
4. Restart your computer and test the system once more.

Let me know the results or share any specific error message you see so I can assist further.
```
---


