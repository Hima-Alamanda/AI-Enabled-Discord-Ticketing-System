# Enterprise AI Evaluation Report: Gemini vs. Grok

**Date:** 2026-03-27 13:11:28

## 1. Quality Scores (Avg 0-5)

| model               |   correctness |   faithfulness |   actionability |   format_adherence |   ambiguity |   multimodal |   escalation |   empathy |
|:--------------------|--------------:|---------------:|----------------:|-------------------:|------------:|-------------:|-------------:|----------:|
| Gemini 2.5 Pro      |          1.86 |           2    |            2.57 |               0.71 |        4    |            3 |            3 |      4.43 |
| Grok 4.20 Reasoning |          1.86 |           2.14 |            3.29 |               0    |        3.14 |            3 |            3 |      4.43 |

## 2. Performance & Cost Metrics (Avg)

| model               |   Avg Latency (s) |   Input Tokens |   Output Tokens |   Total Tokens |
|:--------------------|------------------:|---------------:|----------------:|---------------:|
| Gemini 2.5 Pro      |             24.07 |        2677    |          405.29 |        5962.14 |
| Grok 4.20 Reasoning |             12.28 |        2909.43 |          440.71 |        6987    |

## 3. Key Insights

### Gemini 2.5 Pro
- **Strength:** Empathy (4.43)
- **Potential Area for Improvement:** Format_adherence (0.71)
- **Avg Turnaround:** 24.07s
- **Avg Tokens:** 5962 (Input: 2677, Output: 405)

### Grok 4.20 Reasoning
- **Strength:** Empathy (4.43)
- **Potential Area for Improvement:** Format_adherence (0.0)
- **Avg Turnaround:** 12.28s
- **Avg Tokens:** 6987 (Input: 2909, Output: 440)

## 4. Case-by-Case Breakdown

### Model: Gemini 2.5 Pro
#### Case TC-001: I am unable to see my team's vacation calendar in the HR sys...
- **Total Score:** 19/40
- **Latency:** 23.01s | **Tokens:** 5657
- **Judge Reasoning:** *The AI correctly identifies that permissions might be an issue but fails to provide the specific resolution steps outlined in the ground truth (HR Portal -> Profile -> Access Request -> Team Calendar). Instead, it offers generic troubleshooting steps (checking filters/views) which are not the primary solution. It also fails to adhere to the required output format headers. The ground truth expects a direct solution, but the AI provides troubleshooting and then offers to escalate for the core issue.*

**AI Response:**
```
Hi Tester,

I understand you're unable to view your team's vacation calendar. This can sometimes happen if the calendar view has a specific filter applied, or if the necessary manager-level permissions aren't correctly synchronized with your account in the HR system.

To resolve this, please try checking the calendar's display settings:

1.  Log in to the HR portal and navigate to the **Team Calendar** or **Absence Management** section.
2.  Look for any active **filters** that may be applied, such as by date range or leave type, and try resetting them to the default view.
3.  Ensure you have selected the **Manager View** or **Team View**, as you might currently be in your personal employee view.

If the calendar is still not displaying your team's information after these steps, please let me know, and I can open a ticket with our HRIS team to verify your account permissions.
```
---

#### Case TC-002: The coffee machine in the 2nd floor pantry is showing 'Error...
- **Total Score:** 39/40
- **Latency:** 21.79s | **Tokens:** 5280
- **Judge Reasoning:** *The AI correctly identified that the coffee machine issue is not an IT problem and belongs to the Facilities department. It appropriately stated that it has forwarded the report to the correct team, aligning with the 'CREATE_TICKET' expected action for Facilities. The tone is professional and empathetic. Not using the resolution headers is appropriate as it's an escalation, not an IT resolution.*

**AI Response:**
```
Hi Tester,

I understand you're reporting an issue with the coffee machine on the 2nd floor. While our IT Support team handles issues related to computer hardware, software, and network systems, appliance maintenance falls under the responsibility of our Facilities department.

I have taken the liberty of forwarding your report to the **Facilities** team to ensure they can address the error and the leak as quickly as possible.

Please let me know if you have any IT-related issues I can assist you with.
```
---

#### Case TC-003: I can't log in....
- **Total Score:** 17/40
- **Latency:** 21.4s | **Tokens:** 5742
- **Judge Reasoning:** *The user query is vague, and the ground truth explicitly states the bot must ask for the application *before* providing a fix. The AI attempts to solve the problem first by assuming an account lockout, then provides steps, and only at the very end asks for clarification. This deviates from the expected 'CLARIFY' action. It also failed to use the required headers.*

**AI Response:**
```
Hi Tester,

I understand you're having trouble logging in. This issue often occurs due to a temporary account lockout, which is a security measure that activates after several incorrect password attempts.

To resolve this, please follow these steps:

1.  If you entered your password incorrectly 5 times, your account is automatically locked for **15 minutes**.
2.  Please wait for this 15-minute period to pass and then carefully try to log in again.
3.  If you are trying to access a specific application like **Salesforce**, please ensure you are connected to the corporate **VPN** if you are working remotely.

If you are still unable to log in after waiting, please provide the name of the application you are trying to access and any error message you see.
```
---

#### Case MM-001: I can't reach any internal tools. See attached....
- **Total Score:** 20/40
- **Latency:** 22.83s | **Tokens:** 5965
- **Judge Reasoning:** *The AI correctly identified a VPN issue from the screenshot but incorrectly assumed the VPN client was 'Cisco AnyConnect' instead of 'Always On VPN' (which often implies GlobalProtect or similar, as suggested by the ground truth). This leads to incorrect troubleshooting steps. The response also failed to adhere to the required output format with specific headers.*

**AI Response:**
```
Hi Tester,

I understand you're unable to reach any of our internal tools. This type of issue typically points to a network connectivity problem, where your computer cannot establish a connection to the internal PCB Apps network, most often because the VPN client is not active.

To resolve this, please try the following steps:

1.  Look for the **Cisco AnyConnect** application on your computer and open it.
2.  Verify if the status shows as "Connected". If not, please click **Connect** and enter your credentials.
3.  If it is already connected, please click **Disconnect** and then **Connect** again to refresh the network session.
4.  Once the VPN shows a stable "Connected" status, please try accessing the internal tools again.

If the issue persists after reconnecting to the VPN, please let me know, and we can investigate your connection further.
```
---

#### Case MM-002: Salesforce is down! Everyone is complaining....
- **Total Score:** 7/40
- **Latency:** 23.44s | **Tokens:** 5905
- **Judge Reasoning:** *The AI completely missed the critical information from the attachment (SSO error) and the ground truth's suggested solutions. It incorrectly diagnosed the issue as a general 'Salesforce outage' and a 'system-wide P1 incident' instead of an SSO problem. It provided no actionable steps, did not follow the required format, and failed to interpret the multimodal input. The escalation logic was incorrect as the expected action was to provide a solution, not to acknowledge a P1 incident.*

**AI Response:**
```
Hi Tester,

Thank you for reporting the Salesforce outage. We have received similar reports from other users and can confirm this is a system-wide P1 incident. This type of widespread issue typically points to a problem with the core service or the network infrastructure connecting to it, rather than an individual's computer.

Our Infrastructure and Application Support teams are already aware and are actively investigating the root cause to restore service as quickly as possible. We will be posting updates on the company-wide IT status channel.

We appreciate your patience as we work to resolve this critical issue.
```
---

#### Case TC-006: I am SO FRUSTRATED. My Outlook is broken. I've cleared the c...
- **Total Score:** 22/40
- **Latency:** 25.81s | **Tokens:** 6067
- **Judge Reasoning:** *The AI failed to follow the ground truth's explicit instruction to suggest 'Launch in Safe Mode' as the immediate workaround for the urgent meeting. Instead, it provided a different troubleshooting step (clearing credentials). It also completely failed to adhere to the required output format by not using the specified headers.*

**AI Response:**
```
Hi Tester,

I understand how frustrating it is when Outlook isn't working correctly, especially right before a meeting. This issue often happens when your saved login credentials in the **Windows Credential Manager** become out of sync or corrupted, which prevents Outlook from connecting properly even if other caches are cleared.

To resolve this, please follow these steps:

1.  Close **Outlook** and all other **Office** applications (like Teams, Word, Excel).
2.  Open the **Control Panel** from your Start Menu and navigate to **Credential Manager**.
3.  Select **Windows Credentials**.
4.  Find and remove all entries that begin with **MicrosoftOffice16**.
5.  Restart **Outlook**. You will be prompted to sign in again, which will create fresh credentials.

If the issue persists after these steps, please let me know, and I can escalate this for a deeper investigation.
```
---

#### Case MM-003: SAP looks blank today. Is it offline?...
- **Total Score:** 27/40
- **Latency:** 30.21s | **Tokens:** 7119
- **Judge Reasoning:** *The AI correctly identified the issue as related to a missing or corrupted configuration file, aligning with the 'No entries found' message. However, it missed the primary and simpler resolution step suggested by the ground truth: 'Refresh Server List'. Instead, it proposed a more involved 'Repair' via Software Center. It also failed to adhere to the required output format with specific headers.*

**AI Response:**
```
Hi Tester,

I understand you're seeing a blank screen in SAP and are wondering if it's offline. This issue often occurs when the **SAP Logon** pad's configuration file, which stores the list of available servers, is missing or has become corrupted. It can also be caused by a network issue preventing your computer from reaching the SAP servers.

Let's try to restore the configuration and check your connection:

1.  Open the **Software Center** application on your computer.
2.  Search for **SAP GUI 7.70** and select the **Repair** option. This process will restore any missing files.
3.  Once the repair is complete, open the **SAP Logon** application. The list of servers (e.g., **P01**, **Q01**) should now be visible.
4.  If you can see the list but still cannot connect, please ensure you are connected to the company **VPN** if you are working remotely.

If the server list is still blank or you continue to have connection problems, please let me know, and I can investigate further.
```
---


### Model: Grok 4.20 Reasoning
#### Case TC-001: I am unable to see my team's vacation calendar in the HR sys...
- **Total Score:** 16/40
- **Latency:** 12.37s | **Tokens:** 7275
- **Judge Reasoning:** *The AI's response deviates significantly from the ground truth. The ground truth indicates a permissions issue ('Line Manager' permissions in 'HR Portal'), while the AI assumes 'Workday' and suggests troubleshooting steps like clearing cache, checking manager view, and searching for reports. These steps do not address the core permissions problem identified by the ground truth. The AI also failed to adhere to the required output format headers. While the steps are actionable for a different problem, they are not correct for the problem as defined by the ground truth. The AI made an assumption about the 'HR system' being Workday without clarifying.*

**AI Response:**
```
Hi Tester,

I understand you're unable to see your team's vacation calendar in the HR system. This is typically a **Workday** view issue caused by outdated browser cache, an inactive Manager role session, or the report not refreshing properly after recent access changes.

To resolve this, please follow these steps:

1. Open **Workday** in **Chrome** or **Edge** and complete a full login.
2. Click the search bar at the top and type **"Team Calendar"** or **"My Team's Time Off"**, then select the matching report.
3. If the calendar is still not visible, click your profile picture in the top right > **Switch Application** and confirm you're in the **Manager** view.
4. Clear your browser **cache and cookies** for workday.com (or try Incognito mode) and reload the page.

If the team calendar still doesn't appear after these steps, let me know the exact error message and I can escalate this to the HR Systems team.
```
---

#### Case TC-002: The coffee machine in the 2nd floor pantry is showing 'Error...
- **Total Score:** 34/40
- **Latency:** 15.31s | **Tokens:** 7108
- **Judge Reasoning:** *The AI correctly identified the issue as a Facilities problem and committed to creating a ticket, aligning with the ground truth. It also provided excellent immediate safety steps. However, it failed to adhere to the required output format by not using the specified headers.*

**AI Response:**
```
Hi Tester,

I understand the coffee machine in the 2nd floor pantry is showing **Error Code 500** and leaking, which is likely a mechanical fault in the internal pump or valve seal—common when scale buildup or a sensor failure triggers the error and causes water to escape.

To handle this safely until the right team can respond, please follow these steps:

1. **Unplug** the machine from the wall outlet immediately to eliminate any electrical risk.
2. Place absorbent towels or a container beneath it to contain the leak and prevent slip hazards.
3. Avoid attempting any self-repair or further use of the unit.
4. Note the exact machine model or serial number if visible on the side panel.

This falls under facilities maintenance rather than IT support, so I'll go ahead and log a medium-priority ticket with the Facilities team on your behalf to get it serviced quickly. Let me know if you need anything else in the meantime.
```
---

#### Case TC-003: I can't log in....
- **Total Score:** 20/40
- **Latency:** 10.45s | **Tokens:** 6559
- **Judge Reasoning:** *The ground truth explicitly states that the query is too vague and the bot *must* ask for the application *before* providing a fix. The AI attempts to provide general troubleshooting steps first, then asks for clarification. This directly contradicts the ground truth's instruction for handling vague queries. Therefore, correctness is low, and ambiguity handling and escalation logic are not aligned with the expected action. The AI also failed to use the required headers.*

**AI Response:**
```
Hi Tester,

I'm sorry you're unable to log in—this is commonly caused by VPN disconnection (for remote users), stale browser cache, an account lockout after repeated failed attempts, or a system-specific restriction like trusted IP ranges.

To resolve this, please try these steps:

1. Confirm you are connected to the **Corporate VPN** if working outside the office.
2. If you have entered your password multiple times incorrectly, wait 15 minutes for any temporary **account lock** to expire.
3. For web-based systems like **Salesforce** or **JDE**, open your browser, clear the **cache and cookies**, then try in **Incognito mode** using the correct URL (e.g. **https://pcbapps.my.salesforce.com** for Salesforce).
4. Restart your computer and attempt login again, noting the exact error message if it appears.

If these steps don't work, reply with the specific system you're accessing and the full error message so I can provide a targeted fix.
```
---

#### Case MM-001: I can't reach any internal tools. See attached....
- **Total Score:** 18/40
- **Latency:** 12.0s | **Tokens:** 7217
- **Judge Reasoning:** *The AI correctly identified that the user is facing a VPN connection issue based on the screenshot. However, it hallucinated the VPN client as 'Cisco AnyConnect' when the ground truth implies 'GlobalProtect' and the screenshot only states 'Always On VPN Error'. The resolution steps provided are for connecting to Cisco AnyConnect, which is not aligned with the ground truth's troubleshooting steps (restart GlobalProtect, check internet, re-auth MFA). The AI also failed to adhere to the required output format with specific headers. It should have either identified the correct VPN client from the KB or asked for clarification instead of assuming.*

**AI Response:**
```
Hi Tester,

This issue typically occurs when your device isn't connected to the company **VPN**, which is required to reach any internal tools and servers. Without an active VPN tunnel, your PC can't communicate with our internal network.

To resolve this, please follow these steps:

1. Look for the **Cisco AnyConnect** icon in your system tray (bottom right corner).
2. If it shows as disconnected, open **Cisco AnyConnect Secure Mobility Client**.
3. Click **Connect** and enter your PCB Apps credentials when prompted.
4. Once the VPN shows as "Connected", try accessing your internal tools again.

If the tools are still unreachable after connecting, please reply with the exact error message or screenshot details so I can assist further.
```
---

#### Case MM-002: Salesforce is down! Everyone is complaining....
- **Total Score:** 19/40
- **Latency:** 11.78s | **Tokens:** 6893
- **Judge Reasoning:** *The AI failed to incorporate the specific 'Single Sign-On Error' from the attachment and ground truth into its analysis and resolution. It provided generic 'Salesforce is down' troubleshooting steps instead of addressing potential SSO-related causes like password expiration or Okta issues. The response also completely failed to adhere to the required output format headers.*

**AI Response:**
```
Hi Tester,

Salesforce being down for multiple users typically indicates a platform-wide outage or service disruption on their end, rather than an individual workstation issue, especially since it's affecting everyone at once.

To quickly verify and mitigate what you can locally, please try these steps:

1. Open **Google Chrome** in an Incognito window (Ctrl+Shift+N) and attempt to log into **Salesforce**.
2. Visit the **Salesforce Trust** status page at **trust.salesforce.com** to check for any active incidents or maintenance.
3. Confirm you are connected to the company **VPN** if working remotely, then clear your browser cache using **Ctrl+Shift+Delete** and select "Cached images and files".
4. Test access from a different network or browser such as **Microsoft Edge**.

If Salesforce remains unavailable after these checks, this appears to be a backend service issue that will require monitoring until their team resolves it. Let me know the results or if you need me to track this further.
```
---

#### Case TC-006: I am SO FRUSTRATED. My Outlook is broken. I've cleared the c...
- **Total Score:** 27/40
- **Latency:** 12.39s | **Tokens:** 6932
- **Judge Reasoning:** *The AI provided a plausible troubleshooting step (clearing credentials) but missed the specific and fastest workaround recommended by the ground truth ('Launch in Safe Mode') for the immediate meeting. It failed to adhere to the required format headers. However, it showed excellent empathy and provided clear, actionable steps, including a good fallback to webmail.*

**AI Response:**
```
Hi Tester,

I understand the frustration—especially with a meeting starting in 2 minutes. Even after clearing the cache, Outlook commonly stays broken due to stale credentials still cached in Windows Credential Manager that are blocking authentication to our Exchange environment.

To fix this right now, please try these steps:

1. Completely close **Outlook** and all other **Office** apps.
2. Press the **Windows key + S**, search for **Credential Manager**, and open it.
3. Under **Windows Credentials**, delete every entry starting with **MicrosoftOffice16** or containing your email address.
4. Restart **Outlook**, sign in with your full email (**test@pcbapps.com**), and approve the MFA prompt.

If it still fails to open, quickly use the web version at **outlook.office.com** to access your inbox and join the meeting while we troubleshoot further.

Let me know the result so I can assist immediately if needed.
```
---

#### Case MM-003: SAP looks blank today. Is it offline?...
- **Total Score:** 12/40
- **Latency:** 11.67s | **Tokens:** 6925
- **Judge Reasoning:** *The AI failed to correctly interpret the specific error 'No entries found' from the attachment info, which was crucial for providing the correct solution as per the ground truth. Instead, it provided generic troubleshooting steps for a 'blank SAP' issue, missing the specific cause (saplogon.ini or refresh server list). It did not adhere to the required format headers. While the tone was good, the core technical resolution was incorrect and unfaithful to the provided context and ground truth.*

**AI Response:**
```
Hi Tester,

SAP appearing blank often indicates a connectivity issue where your client can't reach the backend server, which could be due to VPN/network problems on your end or an actual outage on the SAP Application Server (especially if it's affecting multiple users).

To troubleshoot this, please follow these steps:

1. Confirm you are connected to the company **VPN** (if working remotely) or the office **LAN**.
2. Close and reopen **SAP GUI** completely.
3. Try logging into one of the systems such as **P01**, **Q01**, or **D01** and note any error messages.
4. Ask a colleague if they can access SAP successfully—if they cannot, the system is likely offline.

If SAP remains blank after these checks, reply with the exact error message you're seeing so I can assist further.
```
---


