#!/usr/bin/env python3
"""
Legal Timeline Export Tool
Generates an editable markdown timeline file that can be processed back into the system.
"""

import sqlite3
from datetime import datetime


def export_legal_timeline(
    output_file: str = "legal_timeline_draft.md",
    start_date: str = "2024-01-01",
    end_date: str = "2025-12-31",
    case_number: str = "202409-26239516",
) -> str:
    """Export timeline as editable markdown with annotation sections."""

    # Connect to database
    conn = sqlite3.connect("emails.db")
    conn.row_factory = sqlite3.Row

    # Get timeline events
    query = """
    SELECT datetime_utc, subject, sender, message_id, body_text
    FROM emails
    WHERE datetime_utc BETWEEN ? AND ?
    AND (subject LIKE '%water%' OR subject LIKE '%CRD%' OR subject LIKE '%discovery%'
         OR subject LIKE '%landlord%' OR subject LIKE '%repair%' OR subject LIKE '%intrusion%'
         OR sender LIKE '%teshalelaw%' OR sender LIKE '%stoneman%' OR sender LIKE '%dignitylawgroup%')
    ORDER BY datetime_utc DESC
    """

    cursor = conn.execute(query, (start_date, end_date))
    events = cursor.fetchall()

    # Build markdown timeline
    content = f"""# Legal Timeline - Case #{case_number}
*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*
*Editable Draft - Add notes between events and reprocess*

---

## Instructions for Editing
1. Add timeline entries by copying the template below
2. Fill in [YOUR NOTES] sections with additional context
3. When done editing, save and run: `python process_timeline_updates.py legal_timeline_draft.md`

### Template for New Entries:
```
## YYYY-MM-DD: Event Title
**Type:** [legal/communication/inspection/repair]
**Parties:** Who was involved
**Summary:** Brief description
**Impact:** Legal/practical significance
**Evidence:** Email ID, documents, photos
**Notes:** [YOUR ADDITIONAL CONTEXT HERE]
```

---

## Timeline Events

"""

    for event in events:
        event_date = event["datetime_utc"][:10]  # Extract date
        subject = event["subject"] or "No Subject"
        sender = event["sender"]
        body_preview = (event["body_text"] or "")[:200] + "..." if event["body_text"] else ""

        content += f"""## {event_date}: {subject}
**Type:** communication
**From:** {sender}
**Email ID:** {event['message_id']}
**Summary:** {body_preview}
**Impact:** [NEEDS ANALYSIS]
**Evidence:** Email in database
**Notes:** [YOUR NOTES HERE - Add legal significance, follow-up actions, connections to other events]

---

"""

    # Add sections for manual entries
    content += """
## Manual Timeline Entries
*Add important events not captured in emails*

## [DATE]: [EVENT TITLE]
**Type:** [legal/inspection/repair/communication]
**Parties:** [Who was involved]
**Summary:** [What happened]
**Impact:** [Legal/practical significance]
**Evidence:** [Documents, photos, recordings]
**Notes:** [YOUR DETAILED NOTES]

---

## Key Legal Milestones Checklist
- [ ] Initial water intrusion report (Feb 4, 2024)
- [ ] CRD case filing (#202409-26239516)
- [ ] Property management transition
- [ ] Discovery requests filed
- [ ] Meet and confer sessions
- [ ] Inspection dates
- [ ] Repair estimates/refusals
- [ ] Health impact documentation
- [ ] Current status

## Case Strategy Notes
[Add your strategic thoughts, next steps, deadlines]

## Evidence Cross-Reference
[Link timeline events to physical evidence, photos, documents]
"""

    # Write to file
    with open(output_file, "w") as f:
        f.write(content)

    conn.close()
    print(f"✅ Legal timeline exported to: {output_file}")
    print(f"📝 Found {len(events)} relevant events")
    print("✏️  Edit the file and run process_timeline_updates.py to sync changes")

    return output_file


if __name__ == "__main__":
    export_legal_timeline()
