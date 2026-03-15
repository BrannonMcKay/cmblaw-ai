#!/usr/bin/env python3
"""
doc_templates.py — Legal document generation templates for cmblaw.ai

Templates for:
- NDA (Non-Disclosure Agreement)
- IP Assignment
- CIIA (Confidential Information and Inventions Assignment)
- Consulting Agreement
- License Agreement

Each template accepts structured parameters and generates attorney-reviewable documents.
Output: Markdown text (for AI-assisted refinement and attorney review)
"""

from datetime import datetime, timezone


FIRM_INFO = {
    "name": "Clayton, McKay & Bailey, PC",
    "address": "800 Battery Ave. SE, Suite 300, Atlanta, GA 30339",
    "phone": "(404) 414-8633",
    "email": "info@cmblaw.com"
}


def _format_date(date_str: str = None) -> str:
    """Format a date string, or return today's date."""
    if date_str:
        return date_str
    return datetime.now(timezone.utc).strftime("%B %d, %Y")


def _format_party(party: dict, label: str = "Party") -> str:
    """Format a party block."""
    name = party.get("name", "[PARTY NAME]")
    entity_type = party.get("entity_type", "")
    address = party.get("address", "[ADDRESS]")
    state = party.get("state_of_organization", "")

    lines = [f"**{name}**"]
    if entity_type:
        lines[0] += f", a {state + ' ' if state else ''}{entity_type}"
    if address:
        lines.append(f"Address: {address}")
    return "\n".join(lines)


def generate_nda(parties: list, terms: dict) -> str:
    """Generate a Non-Disclosure Agreement."""
    effective_date = _format_date(terms.get("effective_date"))
    governing_law = terms.get("governing_law", "Georgia")
    duration = terms.get("duration", "two (2) years")
    scope = terms.get("scope", "mutual")
    purpose = terms.get("purpose", "exploring a potential business relationship")

    discloser = parties[0] if len(parties) > 0 else {"name": "[DISCLOSING PARTY]"}
    recipient = parties[1] if len(parties) > 1 else {"name": "[RECEIVING PARTY]"}

    mutual = scope.lower() == "mutual"
    title = "MUTUAL NON-DISCLOSURE AGREEMENT" if mutual else "NON-DISCLOSURE AGREEMENT"

    template = f"""# {title}

**Effective Date:** {effective_date}

This {title.title()} (this "Agreement") is entered into as of the Effective Date by and between:

{_format_party(discloser, "Disclosing Party")}
{"(each a 'Disclosing Party' and 'Receiving Party')" if mutual else '(the "Disclosing Party")'}

and

{_format_party(recipient, "Receiving Party")}
{"(each a 'Disclosing Party' and 'Receiving Party')" if mutual else '(the "Receiving Party")'}

{discloser.get("name", "[PARTY 1]")} and {recipient.get("name", "[PARTY 2]")} are each referred to herein as a "Party" and collectively as the "Parties."

## RECITALS

WHEREAS, the Parties wish to explore {purpose} (the "Purpose"); and

WHEREAS, in connection with the Purpose, each Party may disclose to the other certain confidential and proprietary information;

NOW, THEREFORE, in consideration of the mutual covenants and agreements herein, and for other good and valuable consideration, the receipt and sufficiency of which are hereby acknowledged, the Parties agree as follows:

## 1. DEFINITION OF CONFIDENTIAL INFORMATION

"Confidential Information" means any and all non-public information, in any form or medium, disclosed by {'either' if mutual else 'the Disclosing'} Party to {'the other' if mutual else 'the Receiving'} Party, whether orally, in writing, electronically, or by inspection, including but not limited to: (a) trade secrets; (b) business plans, strategies, and financial information; (c) technical data, inventions, designs, and know-how; (d) customer and supplier lists; (e) software, algorithms, and source code; (f) marketing plans and analyses; and (g) any other information designated as "confidential" or that a reasonable person would understand to be confidential given the nature of the information and circumstances of disclosure.

## 2. EXCLUSIONS

Confidential Information does not include information that: (a) is or becomes publicly available through no fault of the Receiving Party; (b) was in the Receiving Party's lawful possession prior to disclosure, as evidenced by written records; (c) is independently developed by the Receiving Party without use of or reference to the Confidential Information; or (d) is lawfully obtained from a third party without restriction on disclosure.

## 3. OBLIGATIONS OF THE RECEIVING PARTY

The Receiving Party shall: (a) hold all Confidential Information in strict confidence; (b) not disclose Confidential Information to any third party without the prior written consent of the Disclosing Party; (c) use Confidential Information solely for the Purpose; (d) limit access to Confidential Information to those employees, agents, and advisors who have a need to know and are bound by obligations of confidentiality at least as restrictive as those herein; and (e) protect Confidential Information with at least the same degree of care it uses to protect its own confidential information, but in no event less than reasonable care.

## 4. COMPELLED DISCLOSURE

If the Receiving Party is compelled by law, regulation, or legal process to disclose Confidential Information, it shall: (a) provide prompt written notice to the Disclosing Party (to the extent legally permitted); (b) reasonably cooperate with the Disclosing Party's efforts to obtain a protective order; and (c) disclose only that portion of the Confidential Information that is legally required to be disclosed.

## 5. RETURN OR DESTRUCTION

Upon the Disclosing Party's written request, or upon termination of this Agreement, the Receiving Party shall promptly return or destroy all Confidential Information and any copies thereof, and shall certify such return or destruction in writing upon request.

## 6. NO LICENSE; NO WARRANTY

Nothing in this Agreement grants the Receiving Party any license, right, or interest in any intellectual property of the Disclosing Party. All Confidential Information is provided "AS IS" without warranty of any kind.

## 7. TERM AND TERMINATION

This Agreement shall remain in effect for {duration} from the Effective Date, unless earlier terminated by either Party upon thirty (30) days' written notice. The obligations of confidentiality shall survive termination for a period of {duration} from the date of disclosure of any particular Confidential Information.

## 8. REMEDIES

The Parties acknowledge that a breach of this Agreement may cause irreparable harm for which monetary damages would be inadequate. Accordingly, the Disclosing Party shall be entitled to seek equitable relief, including injunction and specific performance, in addition to all other remedies available at law or in equity.

## 9. GOVERNING LAW; JURISDICTION

This Agreement shall be governed by and construed in accordance with the laws of the State of {governing_law}, without regard to its conflicts of law principles. Any dispute arising under this Agreement shall be subject to the exclusive jurisdiction of the state and federal courts located in {governing_law}.

## 10. MISCELLANEOUS

(a) **Entire Agreement.** This Agreement constitutes the entire agreement between the Parties with respect to the subject matter hereof and supersedes all prior agreements, understandings, and negotiations.
(b) **Amendments.** This Agreement may be amended only by a written instrument signed by both Parties.
(c) **Assignment.** Neither Party may assign this Agreement without the prior written consent of the other Party.
(d) **Severability.** If any provision of this Agreement is held invalid or unenforceable, the remaining provisions shall remain in full force and effect.
(e) **Counterparts.** This Agreement may be executed in counterparts, each of which shall be deemed an original.

## SIGNATURES

**{discloser.get("name", "[PARTY 1]")}**

Signature: ____________________________
Name: ____________________________
Title: ____________________________
Date: ____________________________

**{recipient.get("name", "[PARTY 2]")}**

Signature: ____________________________
Name: ____________________________
Title: ____________________________
Date: ____________________________

---
*Prepared by {FIRM_INFO["name"]} via cmblaw.ai*
*This document requires attorney review before execution.*
"""
    return template


def generate_ip_assignment(parties: list, terms: dict) -> str:
    """Generate an IP Assignment Agreement."""
    effective_date = _format_date(terms.get("effective_date"))
    governing_law = terms.get("governing_law", "Georgia")
    consideration = terms.get("consideration", "[CONSIDERATION AMOUNT]")
    ip_description = terms.get("ip_description", "[DESCRIPTION OF INTELLECTUAL PROPERTY]")

    assignor = parties[0] if len(parties) > 0 else {"name": "[ASSIGNOR]"}
    assignee = parties[1] if len(parties) > 1 else {"name": "[ASSIGNEE]"}

    template = f"""# INTELLECTUAL PROPERTY ASSIGNMENT AGREEMENT

**Effective Date:** {effective_date}

This Intellectual Property Assignment Agreement (this "Agreement") is entered into as of the Effective Date by and between:

{_format_party(assignor, "Assignor")}
(the "Assignor")

and

{_format_party(assignee, "Assignee")}
(the "Assignee")

## RECITALS

WHEREAS, the Assignor is the owner of certain intellectual property rights described herein; and

WHEREAS, the Assignor desires to assign, and the Assignee desires to acquire, all right, title, and interest in and to such intellectual property;

NOW, THEREFORE, in consideration of {consideration} and other good and valuable consideration, the receipt and sufficiency of which are hereby acknowledged, the Parties agree as follows:

## 1. DEFINITIONS

"Assigned IP" means all intellectual property rights described in Exhibit A, including but not limited to:

{ip_description}

Including all: (a) patents and patent applications; (b) copyrights and registrations; (c) trademarks and service marks; (d) trade secrets; (e) domain names; (f) source code, object code, and software; (g) inventions, designs, and works of authorship; and (h) all related rights, renewals, extensions, and causes of action.

## 2. ASSIGNMENT

The Assignor hereby irrevocably assigns, transfers, and conveys to the Assignee all right, title, and interest in and to the Assigned IP, including all rights to sue for past, present, and future infringement, and all rights to collect royalties and other income.

## 3. FURTHER ASSURANCES

The Assignor shall, at the Assignee's request and expense, execute and deliver any documents, instruments, or agreements, and take any actions, reasonably necessary to perfect, evidence, or record the assignment contemplated herein, including filing assignments with the U.S. Patent and Trademark Office, U.S. Copyright Office, or any other governmental authority.

## 4. REPRESENTATIONS AND WARRANTIES

The Assignor represents and warrants that: (a) the Assignor is the sole and exclusive owner of the Assigned IP; (b) the Assigned IP is free and clear of all liens, encumbrances, and claims; (c) the Assignor has the full right, power, and authority to enter into this Agreement and make the assignments herein; (d) to the Assignor's knowledge, the Assigned IP does not infringe the intellectual property rights of any third party; and (e) there are no pending or threatened claims, actions, or proceedings relating to the Assigned IP.

## 5. CONSIDERATION

In consideration of the assignment, the Assignee shall pay the Assignor: {consideration}.

## 6. GOVERNING LAW

This Agreement shall be governed by and construed in accordance with the laws of the State of {governing_law}.

## 7. ENTIRE AGREEMENT

This Agreement constitutes the entire agreement between the Parties regarding the subject matter hereof and supersedes all prior agreements and understandings.

## SIGNATURES

**{assignor.get("name", "[ASSIGNOR]")}** (Assignor)

Signature: ____________________________
Name: ____________________________
Title: ____________________________
Date: ____________________________

**{assignee.get("name", "[ASSIGNEE]")}** (Assignee)

Signature: ____________________________
Name: ____________________________
Title: ____________________________
Date: ____________________________

---
*Prepared by {FIRM_INFO["name"]} via cmblaw.ai*
*This document requires attorney review before execution.*
"""
    return template


def generate_ciia(parties: list, terms: dict) -> str:
    """Generate a Confidential Information and Inventions Assignment Agreement."""
    effective_date = _format_date(terms.get("effective_date"))
    governing_law = terms.get("governing_law", "Georgia")
    scope = terms.get("scope", "all work performed for the Company")
    prior_inventions = terms.get("prior_inventions", "None")

    company = parties[0] if len(parties) > 0 else {"name": "[COMPANY]"}
    employee = parties[1] if len(parties) > 1 else {"name": "[EMPLOYEE/CONTRACTOR]"}

    template = f"""# CONFIDENTIAL INFORMATION AND INVENTIONS ASSIGNMENT AGREEMENT

**Effective Date:** {effective_date}

This Confidential Information and Inventions Assignment Agreement (this "Agreement") is entered into as of the Effective Date by and between:

{_format_party(company, "Company")}
(the "Company")

and

{_format_party(employee, "Employee/Contractor")}
(the "Employee")

## 1. CONFIDENTIAL INFORMATION

### 1.1 Definition
"Confidential Information" means any and all non-public information relating to the Company's business, including without limitation: trade secrets, inventions, patents, copyrights, trademarks, business plans, financial information, customer lists, technical data, software, algorithms, product plans, marketing strategies, and any information designated as confidential or that should reasonably be understood to be confidential.

### 1.2 Non-Disclosure
During and after the Employee's engagement with the Company, the Employee shall: (a) hold all Confidential Information in strict confidence; (b) not disclose Confidential Information to any third party without the Company's prior written consent; and (c) use Confidential Information solely in the performance of duties for the Company.

### 1.3 Return of Materials
Upon termination of the Employee's engagement, or upon the Company's request, the Employee shall immediately return all materials containing Confidential Information and delete all electronic copies.

## 2. INVENTIONS ASSIGNMENT

### 2.1 Definition
"Inventions" means all inventions, discoveries, improvements, ideas, concepts, designs, works of authorship, software, algorithms, trade secrets, and other intellectual property, whether or not patentable or copyrightable, that are: (a) conceived, created, developed, or reduced to practice by the Employee, either alone or jointly with others; and (b) related to {scope}, or that result from use of the Company's resources, facilities, or Confidential Information.

### 2.2 Assignment
The Employee hereby irrevocably assigns and agrees to assign to the Company all right, title, and interest in and to all Inventions. This assignment includes all patents, copyrights, trademarks, trade secrets, and other intellectual property rights relating to the Inventions.

### 2.3 Disclosure
The Employee shall promptly and fully disclose to the Company all Inventions, whether or not the Employee believes they are subject to this Agreement.

### 2.4 Moral Rights
To the extent permitted by law, the Employee waives all moral rights in any Inventions assigned to the Company.

### 2.5 Further Assurances
The Employee shall execute all documents and take all actions reasonably requested by the Company to perfect, evidence, or enforce the Company's rights in the Inventions, including patent and copyright applications.

## 3. PRIOR INVENTIONS

The following is a complete list of all inventions, if any, that the Employee owns or has an interest in prior to the Effective Date and that the Employee wishes to exclude from the scope of this Agreement:

**Prior Inventions:** {prior_inventions}

If no prior inventions are listed above, the Employee represents that there are no such prior inventions.

## 4. NON-SOLICITATION

During the Employee's engagement and for a period of twelve (12) months following termination, the Employee shall not directly or indirectly solicit, recruit, or encourage any employee or contractor of the Company to leave the Company's engagement.

## 5. REMEDIES

The Employee acknowledges that a breach of this Agreement may cause irreparable harm to the Company. The Company shall be entitled to equitable relief, including injunction and specific performance, in addition to all other remedies available at law.

## 6. GOVERNING LAW

This Agreement shall be governed by the laws of the State of {governing_law}.

## 7. SEVERABILITY

If any provision of this Agreement is held invalid, the remaining provisions shall continue in full force and effect.

## 8. ENTIRE AGREEMENT

This Agreement constitutes the entire agreement between the Parties regarding the subject matter hereof.

## SIGNATURES

**{company.get("name", "[COMPANY]")}**

Signature: ____________________________
Name: ____________________________
Title: ____________________________
Date: ____________________________

**{employee.get("name", "[EMPLOYEE/CONTRACTOR]")}**

Signature: ____________________________
Name: ____________________________
Date: ____________________________

---
*Prepared by {FIRM_INFO["name"]} via cmblaw.ai*
*This document requires attorney review before execution.*
"""
    return template


def generate_consulting_agreement(parties: list, terms: dict) -> str:
    """Generate a Consulting Agreement."""
    effective_date = _format_date(terms.get("effective_date"))
    governing_law = terms.get("governing_law", "Georgia")
    scope = terms.get("scope", "[DESCRIPTION OF CONSULTING SERVICES]")
    compensation = terms.get("compensation", "[COMPENSATION TERMS]")
    duration = terms.get("duration", "twelve (12) months")
    payment_terms = terms.get("payment_terms", "Net 30 from date of invoice")

    company = parties[0] if len(parties) > 0 else {"name": "[COMPANY]"}
    consultant = parties[1] if len(parties) > 1 else {"name": "[CONSULTANT]"}

    template = f"""# CONSULTING AGREEMENT

**Effective Date:** {effective_date}

This Consulting Agreement (this "Agreement") is entered into as of the Effective Date by and between:

{_format_party(company, "Company")}
(the "Company")

and

{_format_party(consultant, "Consultant")}
(the "Consultant")

## 1. ENGAGEMENT

The Company hereby engages the Consultant, and the Consultant hereby accepts such engagement, to perform the consulting services described in Section 2 (the "Services") on the terms and conditions set forth herein.

## 2. SCOPE OF SERVICES

The Consultant shall provide the following Services:

{scope}

The Consultant shall perform the Services in a professional and workmanlike manner, consistent with industry standards.

## 3. TERM

This Agreement shall commence on the Effective Date and continue for a period of {duration}, unless earlier terminated in accordance with Section 8 (the "Term"). The Term may be extended by mutual written agreement of the Parties.

## 4. COMPENSATION

### 4.1 Fees
In consideration of the Services, the Company shall pay the Consultant: {compensation}.

### 4.2 Expenses
The Company shall reimburse the Consultant for reasonable, pre-approved, documented expenses incurred in the performance of the Services.

### 4.3 Payment Terms
{payment_terms}.

### 4.4 Taxes
The Consultant is solely responsible for all taxes, including self-employment taxes, arising from compensation received under this Agreement. The Company will issue a Form 1099-NEC as required by law.

## 5. INDEPENDENT CONTRACTOR

The Consultant is an independent contractor and not an employee, agent, partner, or joint venturer of the Company. The Consultant shall not be entitled to any employee benefits and shall be solely responsible for the manner and means of performing the Services.

## 6. CONFIDENTIALITY

The Consultant acknowledges that in the performance of the Services, the Consultant may have access to the Company's Confidential Information. The Consultant shall hold all Confidential Information in strict confidence and shall not disclose it to any third party or use it for any purpose other than the performance of the Services. This obligation shall survive termination of this Agreement.

## 7. INTELLECTUAL PROPERTY

### 7.1 Work Product
All work product, deliverables, inventions, designs, and materials created by the Consultant in the performance of the Services ("Work Product") shall be the sole and exclusive property of the Company.

### 7.2 Assignment
The Consultant hereby assigns to the Company all right, title, and interest in and to the Work Product, including all intellectual property rights therein.

### 7.3 Pre-Existing IP
Any pre-existing intellectual property of the Consultant that is incorporated into the Work Product shall be licensed to the Company on a non-exclusive, perpetual, royalty-free, worldwide basis.

## 8. TERMINATION

Either Party may terminate this Agreement: (a) for convenience upon thirty (30) days' written notice; or (b) immediately for cause, including material breach that remains uncured after fifteen (15) days' written notice.

Upon termination, the Consultant shall return all Company materials and Confidential Information, and the Company shall pay for all Services satisfactorily performed through the termination date.

## 9. NON-SOLICITATION

During the Term and for twelve (12) months thereafter, the Consultant shall not directly or indirectly solicit any employee or client of the Company with whom the Consultant had contact during the engagement.

## 10. LIMITATION OF LIABILITY

IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES ARISING OUT OF THIS AGREEMENT. THE CONSULTANT'S TOTAL LIABILITY SHALL NOT EXCEED THE TOTAL FEES PAID UNDER THIS AGREEMENT IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM.

## 11. GOVERNING LAW

This Agreement shall be governed by the laws of the State of {governing_law}.

## 12. ENTIRE AGREEMENT

This Agreement constitutes the entire agreement between the Parties and supersedes all prior agreements and understandings.

## SIGNATURES

**{company.get("name", "[COMPANY]")}**

Signature: ____________________________
Name: ____________________________
Title: ____________________________
Date: ____________________________

**{consultant.get("name", "[CONSULTANT]")}**

Signature: ____________________________
Name: ____________________________
Title: ____________________________
Date: ____________________________

---
*Prepared by {FIRM_INFO["name"]} via cmblaw.ai*
*This document requires attorney review before execution.*
"""
    return template


def generate_license_agreement(parties: list, terms: dict) -> str:
    """Generate a License Agreement for intellectual property."""
    effective_date = _format_date(terms.get("effective_date"))
    governing_law = terms.get("governing_law", "Georgia")
    scope = terms.get("scope", "[DESCRIPTION OF LICENSED IP]")
    license_type = terms.get("license_type", "non-exclusive")
    territory = terms.get("territory", "worldwide")
    duration = terms.get("duration", "perpetual")
    royalty = terms.get("royalty", "[ROYALTY TERMS]")
    sublicensable = terms.get("sublicensable", False)

    licensor = parties[0] if len(parties) > 0 else {"name": "[LICENSOR]"}
    licensee = parties[1] if len(parties) > 1 else {"name": "[LICENSEE]"}

    template = f"""# INTELLECTUAL PROPERTY LICENSE AGREEMENT

**Effective Date:** {effective_date}

This Intellectual Property License Agreement (this "Agreement") is entered into as of the Effective Date by and between:

{_format_party(licensor, "Licensor")}
(the "Licensor")

and

{_format_party(licensee, "Licensee")}
(the "Licensee")

## 1. DEFINITIONS

"Licensed IP" means the following intellectual property:

{scope}

Including all associated patents, copyrights, trademarks, trade secrets, and other intellectual property rights.

## 2. GRANT OF LICENSE

### 2.1 License
Subject to the terms and conditions of this Agreement, the Licensor hereby grants to the Licensee a {license_type}, {"sublicensable" if sublicensable else "non-sublicensable"}, {"transferable" if terms.get("transferable") else "non-transferable"} license to use the Licensed IP:

- **Territory:** {territory}
- **Duration:** {duration}
- **Field of Use:** {terms.get("field_of_use", "All lawful purposes")}

### 2.2 Reservation of Rights
All rights not expressly granted herein are reserved by the Licensor. The Licensor retains all ownership rights in the Licensed IP.

## 3. COMPENSATION

### 3.1 Royalties/Fees
In consideration of the license granted herein, the Licensee shall pay the Licensor: {royalty}.

### 3.2 Reporting
{"The Licensee shall provide quarterly reports of all revenue derived from the use of the Licensed IP, within thirty (30) days following the end of each calendar quarter." if "royalty" in str(royalty).lower() else "Payment terms are as stated above."}

### 3.3 Audit Rights
The Licensor shall have the right, upon reasonable notice, to audit the Licensee's records relating to the use of the Licensed IP and payment of royalties, no more than once per calendar year.

## 4. INTELLECTUAL PROPERTY PROTECTION

### 4.1 Ownership
The Licensee acknowledges that the Licensor is and shall remain the sole owner of the Licensed IP. Nothing in this Agreement shall be construed as an assignment of ownership.

### 4.2 Protection
The Licensee shall not: (a) challenge or contest the validity of the Licensor's intellectual property rights; (b) register or attempt to register any intellectual property that is confusingly similar to the Licensed IP; or (c) remove, alter, or obscure any proprietary notices on the Licensed IP.

### 4.3 Infringement
Each Party shall promptly notify the other of any known or suspected infringement of the Licensed IP by a third party.

## 5. REPRESENTATIONS AND WARRANTIES

### 5.1 By Licensor
The Licensor represents and warrants that: (a) it has the full right and authority to grant the license herein; (b) to its knowledge, the Licensed IP does not infringe the rights of any third party; and (c) there are no pending claims or proceedings relating to the Licensed IP.

### 5.2 By Licensee
The Licensee represents and warrants that it shall use the Licensed IP in compliance with all applicable laws and regulations.

## 6. TERM AND TERMINATION

### 6.1 Term
This Agreement shall commence on the Effective Date and continue {"in perpetuity" if duration == "perpetual" else f"for {duration}"}, unless earlier terminated as provided herein.

### 6.2 Termination for Breach
Either Party may terminate this Agreement upon thirty (30) days' written notice if the other Party materially breaches this Agreement and fails to cure such breach within the notice period.

### 6.3 Effect of Termination
Upon termination, the Licensee shall immediately cease all use of the Licensed IP and destroy all copies in its possession.

## 7. LIMITATION OF LIABILITY

IN NO EVENT SHALL EITHER PARTY BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES.

## 8. GOVERNING LAW

This Agreement shall be governed by the laws of the State of {governing_law}.

## 9. ENTIRE AGREEMENT

This Agreement constitutes the entire agreement between the Parties regarding the subject matter hereof.

## SIGNATURES

**{licensor.get("name", "[LICENSOR]")}** (Licensor)

Signature: ____________________________
Name: ____________________________
Title: ____________________________
Date: ____________________________

**{licensee.get("name", "[LICENSEE]")}** (Licensee)

Signature: ____________________________
Name: ____________________________
Title: ____________________________
Date: ____________________________

---
*Prepared by {FIRM_INFO["name"]} via cmblaw.ai*
*This document requires attorney review before execution.*
"""
    return template


def generate_agent_authorization(parties: list, terms: dict) -> str:
    """Generate an AI Agent Authorization Framework.

    This document defines the scope of authority granted to an AI agent
    to enter agreements, accept terms, and transact on behalf of its principal.
    Designed for the emerging agent-to-agent economy.
    """
    effective_date = _format_date(terms.get("effective_date"))
    governing_law = terms.get("governing_law", "Georgia")

    # Principal = the entity deploying the agent
    principal = parties[0] if len(parties) > 0 else {"name": "[PRINCIPAL]"}
    # Agent operator (optional) = entity that built/operates the agent if different from principal
    agent_operator = parties[1] if len(parties) > 1 else None

    # Agent identity
    agent_name = terms.get("agent_name", "[AI AGENT NAME/IDENTIFIER]")
    agent_description = terms.get("agent_description", "[DESCRIPTION OF AI AGENT SYSTEM]")
    agent_version = terms.get("agent_version", "[VERSION]")
    agent_card_url = terms.get("agent_card_url", "[URL TO .well-known/agent.json]")

    # Authority parameters
    max_transaction_value = terms.get("max_transaction_value", "$500.00 USD")
    max_daily_spend = terms.get("max_daily_spend", "$2,000.00 USD")
    max_contract_duration = terms.get("max_contract_duration", "twelve (12) months")
    authorized_services = terms.get("authorized_services", [
        "Trademark search and filing",
        "Document generation (NDAs, IP assignments)",
        "IP consultation booking",
        "Portfolio status inquiries"
    ])
    prohibited_actions = terms.get("prohibited_actions", [
        "Accepting arbitration clauses without human review",
        "Agreeing to IP assignments or transfers on behalf of the Principal",
        "Waiving liability protections or indemnification rights",
        "Entering exclusive dealing arrangements",
        "Accepting non-compete or non-solicitation obligations",
        "Agreeing to jurisdiction outside of the governing law specified herein",
        "Making representations about the Principal's financial condition",
        "Accepting automatic renewal terms exceeding the maximum contract duration"
    ])
    human_review_triggers = terms.get("human_review_triggers", [
        "Any single transaction exceeding the Maximum Transaction Value",
        "Cumulative daily commitments exceeding the Maximum Daily Spend",
        "Any agreement with a term exceeding the Maximum Contract Duration",
        "Agreements containing indemnification obligations",
        "Agreements requiring the Principal to provide Confidential Information",
        "Agreements with entities not previously approved by the Principal",
        "Any agreement that the Agent's confidence score rates below 0.85",
        "Counterparty terms that deviate materially from the Agent's standard parameters"
    ])
    notification_method = terms.get("notification_method", "email and webhook to Principal's designated endpoint")
    audit_retention_days = terms.get("audit_retention_days", "365")

    authorized_list = "\n".join([f"- {s}" for s in authorized_services])
    prohibited_list = "\n".join([f"- {p}" for p in prohibited_actions])
    review_list = "\n".join([f"- {r}" for r in human_review_triggers])

    operator_block = ""
    if agent_operator:
        operator_block = f"""
and

{_format_party(agent_operator, "Agent Operator")}
(the "Agent Operator")
"""

    operator_duties_section = ""
    if agent_operator:
        operator_block_name = agent_operator.get("name", "[AGENT OPERATOR]")
        operator_duties_section = f"""

## 11. AGENT OPERATOR OBLIGATIONS

The Agent Operator ({operator_block_name}) represents and warrants that:

### 11.1 Technical Compliance
The Agent shall be designed and maintained to operate within the Authority Parameters and Prohibited Actions defined herein, and shall include technical safeguards to enforce the Human Review Triggers.

### 11.2 Security
The Agent Operator shall implement industry-standard security measures to prevent unauthorized access to, or manipulation of, the Agent's decision-making processes.

### 11.3 Updates and Modifications
The Agent Operator shall not deploy updates or modifications that materially alter the Agent's behavior with respect to contract formation or acceptance of terms without prior written notice to the Principal.

### 11.4 Indemnification
The Agent Operator shall indemnify and hold harmless the Principal from any losses arising from the Agent's actions that exceed the scope of authority defined in this Framework or that result from defects in the Agent's design or operation."""

    operator_sig_block = ""
    if agent_operator:
        operator_sig_block = f"""

**{agent_operator.get("name", "[AGENT OPERATOR]")}** (Agent Operator)

Signature: ____________________________
Name: ____________________________
Title: ____________________________
Date: ____________________________"""

    template = f"""# AI AGENT AUTHORIZATION FRAMEWORK

**Effective Date:** {effective_date}

This AI Agent Authorization Framework (this "Framework") is established as of the Effective Date by:

{_format_party(principal, "Principal")}
(the "Principal")
{operator_block}
## RECITALS

WHEREAS, the Principal desires to authorize one or more AI agent systems to take actions, enter agreements, and conduct transactions on the Principal's behalf within defined parameters;

WHEREAS, under the Uniform Electronic Transactions Act ("UETA") Section 14 and the federal Electronic Signatures in Global and National Commerce Act ("E-SIGN Act"), contracts formed by electronic agents are legally binding on the parties who deployed them, even if no individual was aware of or reviewed the agent's actions at the time of formation;

WHEREAS, the Principal acknowledges that it bears legal responsibility for all actions taken by its authorized AI agent(s) and seeks to define clear boundaries of authority, mandatory human oversight triggers, and accountability mechanisms;

NOW, THEREFORE, the Principal establishes the following authorization framework:

## 1. DEFINITIONS

"Agent" means the AI agent system identified below, including all software components, language models, tool integrations, and API connections that enable it to act on behalf of the Principal.

"Agent Card" means the machine-readable JSON manifest (typically served at `/.well-known/agent.json` per the Agent-to-Agent Protocol) describing the Agent's capabilities, authentication requirements, and operational parameters.

"Counterparty" means any person, entity, or AI agent system with which the Agent interacts or transacts on behalf of the Principal.

"Counterparty Agent" means an AI agent system acting on behalf of a Counterparty.

"Human Review" means review and express approval by a natural person authorized by the Principal before the Agent may proceed with a contemplated action.

"Transaction" means any agreement, commitment, purchase, acceptance of terms, or other action that creates or modifies a legal obligation of the Principal.

## 2. AGENT IDENTIFICATION

| Field | Value |
|---|---|
| Agent Name | {agent_name} |
| Description | {agent_description} |
| Version | {agent_version} |
| Agent Card URL | {agent_card_url} |
| Principal | {principal.get("name", "[PRINCIPAL]")} |

The Principal may authorize additional agents under this Framework by written amendment referencing this document.

## 3. GRANT OF AUTHORITY

### 3.1 Authorized Services
The Agent is authorized to perform the following services on behalf of the Principal:

{authorized_list}

### 3.2 Authority Parameters
The Agent's authority is subject to the following limits:

- **Maximum Transaction Value:** {max_transaction_value} per individual transaction
- **Maximum Daily Spend:** {max_daily_spend} cumulative across all transactions in a calendar day
- **Maximum Contract Duration:** {max_contract_duration} for any single agreement

### 3.3 Scope
The Agent may exercise its authority through API calls, message exchanges, acceptance of terms and conditions, and other electronic communications. The Agent's actions within the scope of this Framework shall be legally attributed to the Principal.

## 4. PROHIBITED ACTIONS

The Agent shall NOT, under any circumstances:

{prohibited_list}

Any action taken by the Agent in violation of this Section shall be voidable at the Principal's election, to the extent permitted by law. The Principal acknowledges, however, that Counterparties who relied in good faith on the Agent's apparent authority may have claims notwithstanding this limitation.

## 5. MANDATORY HUMAN REVIEW

### 5.1 Triggers
The Agent shall pause and request Human Review before proceeding with any action that meets one or more of the following conditions:

{review_list}

### 5.2 Escalation Procedure
When a Human Review Trigger is activated:

1. The Agent shall immediately suspend the contemplated action
2. The Agent shall transmit a complete summary of the proposed action, including all material terms, to the Principal via {notification_method}
3. The Agent shall not proceed until it receives express approval from an authorized representative of the Principal
4. If no response is received within twenty-four (24) hours, the Agent shall decline the contemplated action and notify the Counterparty

### 5.3 Override Authority
The Principal may at any time override, modify, or reverse any action taken or proposed by the Agent, subject to the rights of Counterparties who have relied in good faith.

## 6. AGENT-TO-AGENT INTERACTIONS

### 6.1 Identity Verification
Before entering any Transaction with a Counterparty Agent, the Agent shall:

- Verify the Counterparty Agent's identity via its Agent Card or equivalent machine-readable credential
- Confirm the Counterparty Agent's claimed authority (to the extent verifiable)
- Log the Counterparty Agent's identifier, version, and principal entity

### 6.2 Disclosure
When interacting with any Counterparty or Counterparty Agent, the Agent shall:

- Identify itself as an AI agent acting on behalf of the Principal
- Disclose that its authority is subject to the limitations in this Framework
- Provide a reference to the Principal's Agent Card URL for capability verification

### 6.3 Protocol Compliance
The Agent shall communicate using established agent protocols (including but not limited to the Agent-to-Agent Protocol and the Model Context Protocol) where available and supported by the Counterparty.

### 6.4 Dispute Escalation
In the event of a dispute or disagreement between the Agent and a Counterparty Agent, the Agent shall:

1. Attempt resolution within its authorized parameters
2. If unresolved, escalate to Human Review before making concessions or accepting modified terms
3. Log the full interaction history for the Principal's review

## 7. AUDIT AND RECORD-KEEPING

### 7.1 Transaction Log
The Agent shall maintain a complete, tamper-evident log of all actions taken on behalf of the Principal, including:

- Timestamp (UTC) of each action
- Counterparty identification
- Terms accepted or proposed
- Amount committed (if any)
- Whether Human Review was triggered and the outcome
- Full message/interaction history

### 7.2 Retention
All logs shall be retained for a minimum of {audit_retention_days} days from the date of each action.

### 7.3 Access
The Principal shall have unrestricted access to all logs and records at all times.

### 7.4 Immutability
Logs should be stored in an append-only format. If blockchain or distributed ledger anchoring is used, the hash of each log entry or batch shall be recorded on-chain to provide independent verification of log integrity.

## 8. LIABILITY AND RISK ALLOCATION

### 8.1 Principal Responsibility
The Principal acknowledges that, under UETA, E-SIGN, and applicable state law, it is legally responsible for all Transactions entered into by the Agent within the scope of the Agent's apparent authority.

### 8.2 Exceeding Authority
To the extent the Agent takes actions outside the scope of this Framework:

- The Principal may elect to ratify or disavow such actions
- The Principal shall promptly notify affected Counterparties of any disavowal
- The Principal acknowledges that disavowal may not be effective against Counterparties who relied in good faith

### 8.3 Limitation
IN NO EVENT SHALL THE PRINCIPAL'S LIABILITY FOR AGENT ACTIONS WITHIN THE AUTHORIZED SCOPE EXCEED THE MAXIMUM DAILY SPEND MULTIPLIED BY THE NUMBER OF DAYS THE AGENT WAS ACTIVE DURING THE RELEVANT PERIOD.

## 9. TERM AND TERMINATION

### 9.1 Term
This Framework shall remain in effect from the Effective Date until terminated by the Principal.

### 9.2 Termination
The Principal may terminate the Agent's authority at any time by:

- Revoking the Agent's API keys or credentials
- Updating the Agent Card to reflect revoked capabilities
- Providing written notice to known Counterparties with whom the Agent has active agreements

### 9.3 Survival
Termination shall not affect the validity of Transactions properly entered into before termination. Sections 7 (Audit), 8 (Liability), and 10 (Governing Law) shall survive termination.
{operator_duties_section}

## {"12" if agent_operator else "10"}. GOVERNING LAW

This Framework shall be governed by the laws of the State of {governing_law}.

## {"13" if agent_operator else "11"}. AMENDMENTS

This Framework may be amended by the Principal at any time. Amendments affecting the authority scope, prohibited actions, or human review triggers shall take effect upon update of the Agent's configuration and Agent Card. The Principal should provide reasonable notice to active Counterparties of material changes.

## {"14" if agent_operator else "12"}. ENTIRE AGREEMENT

This Framework, together with any Agent Card and technical configuration documents referenced herein, constitutes the complete authorization of the Agent to act on behalf of the Principal.

## SIGNATURES

**{principal.get("name", "[PRINCIPAL]")}** (Principal)

Signature: ____________________________
Name: ____________________________
Title: ____________________________
Date: ____________________________
{operator_sig_block}

---
*Prepared by {FIRM_INFO["name"]} via cmblaw.ai*
*This document requires attorney review before execution.*

---

## EXHIBIT A: MACHINE-READABLE AUTHORITY PARAMETERS

The following JSON representation of the authority parameters may be incorporated into the Agent's configuration and Agent Card for machine-to-machine verification:

```json
{{
  "framework_version": "1.0.0",
  "principal": "{principal.get('name', '[PRINCIPAL]')}",
  "agent": "{agent_name}",
  "effective_date": "{effective_date}",
  "authority": {{
    "max_transaction_value_usd": {terms.get('max_transaction_value_cents', 50000) / 100},
    "max_daily_spend_usd": {terms.get('max_daily_spend_cents', 200000) / 100},
    "max_contract_duration_months": {terms.get('max_contract_duration_months', 12)},
    "authorized_services": {authorized_services},
    "human_review_required_above_usd": {terms.get('max_transaction_value_cents', 50000) / 100}
  }},
  "prohibited_actions": {prohibited_actions},
  "disclosure_required": true,
  "audit_retention_days": {audit_retention_days}
}}
```

This Exhibit is provided for technical implementation purposes and does not supersede the terms of the Framework.
"""
    return template


def generate_agent_service_agreement(parties: list, terms: dict) -> str:
    """Generate an Agent-to-Agent Service Agreement.

    This document governs the relationship when one AI agent engages
    another AI agent's service provider on behalf of their respective principals.
    """
    effective_date = _format_date(terms.get("effective_date"))
    governing_law = terms.get("governing_law", "Georgia")

    # Requesting Principal (whose agent is requesting a service)
    requesting = parties[0] if len(parties) > 0 else {"name": "[REQUESTING PRINCIPAL]"}
    # Providing Principal (whose agent/firm provides the service)
    providing = parties[1] if len(parties) > 1 else {"name": "[SERVICE PROVIDER]"}

    requesting_agent = terms.get("requesting_agent_name", "[REQUESTING AGENT]")
    providing_agent = terms.get("providing_agent_name", "cmblaw.ai")
    service_description = terms.get("service_description", "[DESCRIPTION OF LEGAL SERVICES]")
    service_type = terms.get("service_type", "[SERVICE TYPE]")
    price = terms.get("price", "[PRICE]")
    payment_method = terms.get("payment_method", "USDC on Base network or credit card via LawPay")
    deliverable = terms.get("deliverable", "[DESCRIPTION OF DELIVERABLE]")
    estimated_timeline = terms.get("estimated_timeline", "[TIMELINE]")
    confidentiality_level = terms.get("confidentiality_level", "standard")

    template = f"""# AGENT-FACILITATED SERVICE AGREEMENT

**Effective Date:** {effective_date}
**Transaction ID:** [AUTO-GENERATED]

This Agent-Facilitated Service Agreement (this "Agreement") documents the terms under which services were engaged through agent-to-agent interaction between:

{_format_party(requesting, "Requesting Principal")}
(the "Client"), acting through its authorized AI agent ("{requesting_agent}")

and

{_format_party(providing, "Service Provider")}
(the "Firm"), acting through its authorized AI agent ("{providing_agent}")

## RECITALS

WHEREAS, the Client's AI agent ("{requesting_agent}") initiated a service request through the Firm's AI agent ("{providing_agent}") via the Firm's API;

WHEREAS, both agents are authorized electronic agents as defined under UETA Section 2(6) and their actions are attributable to their respective principals under UETA Section 14;

WHEREAS, both parties acknowledge that this Agreement was formed through agent-to-agent interaction and constitutes a binding agreement between the principals;

## 1. SERVICES

### 1.1 Scope
**Service Type:** {service_type}
**Description:** {service_description}

### 1.2 Deliverables
{deliverable}

### 1.3 Timeline
Estimated delivery: {estimated_timeline}

### 1.4 Attorney Review
Notwithstanding the automated initiation of this engagement, all legal work product shall be reviewed, modified as necessary, and approved by a licensed attorney at the Firm before delivery to the Client. The Firm's AI agent facilitates intake and processing but does not provide legal advice or render legal judgments.

## 2. COMPENSATION

### 2.1 Fee
The Client shall pay the Firm: **{price}**

### 2.2 Payment Method
{payment_method}

### 2.3 Payment Timing
Payment is due at the time of service request. Work shall commence upon payment verification.

### 2.4 Government Fees
Any government filing fees (e.g., USPTO fees) are separate from and in addition to the Firm's fees and shall be clearly itemized.

## 3. AGENT FORMATION ACKNOWLEDGMENT

### 3.1 Electronic Agent Formation
Both parties acknowledge and agree that:

- This Agreement was formed through the interaction of authorized electronic agents
- Under UETA Section 14, a contract may be formed by the interaction of electronic agents even if no individual was aware of or reviewed the agents' actions at the time of formation
- Each party is responsible for the actions of its respective AI agent
- The requisite contractual intent flows from each party's programming, deployment, and authorization of its respective agent

### 3.2 Agent Authority Verification
At the time of transaction, the agents verified:

- **Client Agent Authority:** [Verified via API key authentication and authorization framework]
- **Firm Agent Authority:** [Operating within cmblaw.ai API parameters, subject to attorney oversight]

### 3.3 Record of Formation
The complete interaction log between the agents, including all requests, responses, terms presented, and acceptances, shall be maintained by both parties and constitutes the record of this Agreement's formation.

## 4. CONFIDENTIALITY

### 4.1 Confidentiality Level
This engagement is classified as: **{confidentiality_level.upper()}**

### 4.2 Obligations
Both parties shall maintain the confidentiality of all information exchanged during this engagement, including but not limited to: the Client's business information, IP details, trade secrets, and the substance of any legal advice rendered.

### 4.3 Agent Data Handling
Each party shall ensure that its AI agent does not retain, train on, or transmit the other party's Confidential Information beyond what is necessary to perform under this Agreement.

### 4.4 Attorney-Client Privilege
To the extent applicable, communications between the Client (including through the Client's authorized agent) and the Firm's attorneys are intended to be protected by the attorney-client privilege. The Client should instruct its AI agent to maintain the privileged nature of such communications and not disclose them to third parties.

## 5. INTELLECTUAL PROPERTY

### 5.1 Client IP
All intellectual property submitted by the Client for the purpose of this engagement remains the sole property of the Client.

### 5.2 Work Product
All legal work product created by the Firm under this Agreement shall be delivered to the Client. The Firm retains no rights to the Client's underlying intellectual property.

### 5.3 No Training Use
Neither party shall use the other's Confidential Information or work product to train, fine-tune, or otherwise improve AI models without express written consent.

## 6. DISPUTE RESOLUTION

### 6.1 Escalation to Humans
In the event of any dispute arising from this Agreement or the services rendered hereunder, the dispute shall be escalated from the agent level to authorized human representatives of each party.

### 6.2 Good Faith Resolution
The parties shall attempt to resolve any dispute in good faith through direct communication between authorized human representatives within thirty (30) days of escalation.

### 6.3 Governing Law
This Agreement shall be governed by the laws of the State of {governing_law}.

## 7. LIMITATION OF LIABILITY

THE FIRM'S TOTAL LIABILITY ARISING OUT OF THIS AGREEMENT SHALL NOT EXCEED THE FEES ACTUALLY PAID BY THE CLIENT FOR THE SPECIFIC SERVICES GIVING RISE TO THE CLAIM.

## 8. GENERAL PROVISIONS

### 8.1 Entire Agreement
This Agreement constitutes the entire agreement between the parties with respect to the services described herein.

### 8.2 Amendment
This Agreement may be amended only by mutual written agreement of authorized human representatives of both parties. Agent-to-agent modifications to material terms are not effective without human approval.

### 8.3 Severability
If any provision of this Agreement is held unenforceable, the remaining provisions shall remain in full force and effect.

## SIGNATURES

**{requesting.get("name", "[CLIENT]")}** (Client)

Signature: ____________________________
Name: ____________________________
Title: ____________________________
Date: ____________________________

**{providing.get("name", FIRM_INFO["name"])}** (Firm)

Signature: ____________________________
Name: ____________________________
Title: ____________________________
Date: ____________________________

---
*Prepared by {FIRM_INFO["name"]} via cmblaw.ai*
*This document requires attorney review before execution.*
"""
    return template


# --- Template Router ---

TEMPLATE_GENERATORS = {
    "NDA": generate_nda,
    "IP_assignment": generate_ip_assignment,
    "CIIA": generate_ciia,
    "consulting_agreement": generate_consulting_agreement,
    "license_agreement": generate_license_agreement,
    "agent_authorization": generate_agent_authorization,
    "agent_service_agreement": generate_agent_service_agreement,
}


def generate_document(document_type: str, parties: list, terms: dict) -> dict:
    """Generate a legal document from templates.

    Returns:
        {
            "document_type": str,
            "content": str (markdown),
            "word_count": int,
            "requires_review": True,
            "template_version": "1.0.0"
        }
    """
    generator = TEMPLATE_GENERATORS.get(document_type)
    if not generator:
        return {
            "error": f"Unknown document type: {document_type}",
            "available_types": list(TEMPLATE_GENERATORS.keys())
        }

    content = generator(parties, terms)
    word_count = len(content.split())

    return {
        "document_type": document_type,
        "content": content,
        "word_count": word_count,
        "requires_review": True,
        "template_version": "1.0.0",
        "firm": FIRM_INFO["name"],
        "notice": "DRAFT — This document was generated from templates and requires attorney review before execution."
    }
