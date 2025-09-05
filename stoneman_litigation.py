#!/usr/bin/env python3
"""
Stoneman Discovery & Deposition Prep Tool
Generate discovery questions and find contradictions
"""
import sqlite3
import re
from pathlib import Path
from datetime import datetime

def generate_discovery_questions():
    """Generate specific discovery questions based on case issues"""
    
    questions = {
        "Mold Certification & Conflict of Interest": [
            "INTERROGATORY: Identify all certifications held by Dean Houser related to mold inspection, including certification numbers, issuing organizations, and dates of certification.",
            "REQUEST FOR PRODUCTION: Produce all documents evidencing Dean Houser's mold inspector certifications, training certificates, and any continuing education records.",
            "INTERROGATORY: Explain why Dean Houser, who claims to be a certified mold inspector, was selected to perform remediation work in violation of IICRC S520-2024 independence standards.",
            "REQUEST FOR ADMISSION: Admit that Dean Houser has never held a valid mold inspector certification from any recognized certifying body.",
            "INTERROGATORY: Identify all instances where Dean Houser has performed both mold inspection and remediation on the same property."
        ],
        
        "Recording & Privacy": [
            "REQUEST FOR ADMISSION: Admit that you observed visible signs warning of audio and video recording at 518 N. Stoneman Ave on multiple occasions prior to August 14, 2025.",
            "INTERROGATORY: Describe all instances where you photographed or recorded the interior of the tenant's unit, including dates and what was recorded.",
            "REQUEST FOR PRODUCTION: Produce all photographs, videos, or recordings you have made of the tenant's unit interior.",
            "INTERROGATORY: Explain why you continued to conduct the inspection on [date] after explicitly stating you did not consent to being recorded.",
            "REQUEST FOR ADMISSION: Admit that on [prior date], you photographed the tenant's closet without announcing your intent to do so."
        ],
        
        "Repair History & Delays": [
            "INTERROGATORY: For each repair request made by tenants since [move-in date], state: (a) date of request, (b) nature of repair needed, (c) date repair was completed, (d) reason for any delays.",
            "REQUEST FOR PRODUCTION: Produce all communications with contractors regarding repairs at 518 N. Stoneman Ave, including cancelled or rescheduled appointments.",
            "REQUEST FOR ADMISSION: Admit that more than 30 days elapsed between the tenant's notification of mold issues and the commencement of proper remediation.",
            "INTERROGATORY: Identify all instances where repairs were scheduled but not completed, and explain the reason for each cancellation.",
            "REQUEST FOR PRODUCTION: Produce all invoices, receipts, and proof of payment for repairs allegedly completed at the property."
        ],
        
        "Health & Habitability": [
            "INTERROGATORY: State when you first became aware that a child with respiratory issues resided at the property.",
            "REQUEST FOR ADMISSION: Admit that visible mold was present in the unit for more than 90 days after you were notified.",
            "INTERROGATORY: Describe all actions taken to address water intrusion issues identified in the MI&T report dated March 12, 2025.",
            "REQUEST FOR PRODUCTION: Produce all communications with or about MI&T and their mold inspection report.",
            "REQUEST FOR ADMISSION: Admit that you received the MI&T professional mold inspection report recommending immediate remediation."
        ],
        
        "Retaliation": [
            "INTERROGATORY: Explain why physical notices were posted at the tenant's door only after they asserted their legal rights.",
            "REQUEST FOR ADMISSION: Admit that the eviction notice dated July 19 was issued within 180 days of the tenant's complaint to code enforcement.",
            "INTERROGATORY: Identify all complaints made to any government agency about the property and your responses to each.",
            "REQUEST FOR PRODUCTION: Produce all communications with code enforcement, health department, or other agencies regarding the property."
        ]
    }
    
    # Save to file
    with open('discovery_questions.txt', 'w') as f:
        f.write("STONEMAN CASE - DISCOVERY QUESTIONS\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        
        for category, qs in questions.items():
            f.write(f"\n{category.upper()}\n")
            f.write("-" * 40 + "\n\n")
            for q in qs:
                f.write(f"{q}\n\n")
    
    print(f"✅ Discovery questions saved to discovery_questions.txt")
    return questions

def find_deposition_contradictions():
    """Find specific contradictions to explore in depositions"""
    
    contradictions = {
        "Mold Knowledge Timeline": {
            "Setup": "Dean claims he wasn't aware of mold severity",
            "Contradiction": "MI&T report provided March 12, 2025; Dean claimed ability to handle mold August 14, 2025",
            "Questions": [
                "When did you first receive the MI&T mold inspection report?",
                "You claim to be a certified mold inspector - when did you obtain this certification?",
                "Why did you wait 5 months after receiving professional recommendations to attempt remediation?"
            ]
        },
        
        "Recording Consent": {
            "Setup": "Claims privacy violation and non-consent",
            "Contradiction": "Previously photographed tenant's closet surreptitiously; continued inspection despite objection",
            "Questions": [
                "You took photographs of the tenant's closet on [date] - did you obtain consent?",
                "If recording requires consent, why didn't you ask before photographing their belongings?",
                "You said 'we do not consent' but stayed - doesn't that show implied consent?"
            ]
        },
        
        "Repair Completion Claims": {
            "Setup": "Claims repairs are completed promptly",
            "Contradiction": "87.8% of repair emails contain excuses/delays; 74.8% failure rate on scheduled repairs",
            "Questions": [
                "How many times was the mold repair rescheduled?",
                "Can you identify a single repair completed within 30 days of request?",
                "Why do 165 out of 188 repair emails contain excuses or delays?"
            ]
        },
        
        "Professional Standards": {
            "Setup": "Claims to follow professional standards",
            "Contradiction": "Violates IICRC S520-2024 by having same party inspect and remediate",
            "Questions": [
                "Are you familiar with IICRC S520-2024 standards?",
                "The standard requires independent assessment and remediation - why are you doing both?",
                "What qualified you to override MI&T's professional recommendations?"
            ]
        }
    }
    
    # Save to file
    with open('deposition_contradictions.txt', 'w') as f:
        f.write("DEPOSITION CONTRADICTION MATRIX\n")
        f.write("=" * 60 + "\n\n")
        
        for topic, details in contradictions.items():
            f.write(f"\n{topic.upper()}\n")
            f.write("-" * 40 + "\n")
            f.write(f"Setup: {details['Setup']}\n")
            f.write(f"Contradiction: {details['Contradiction']}\n")
            f.write("\nDeposition Questions:\n")
            for i, q in enumerate(details['Questions'], 1):
                f.write(f"  {i}. {q}\n")
            f.write("\n")
    
    print(f"✅ Deposition contradictions saved to deposition_contradictions.txt")
    return contradictions

def generate_amended_complaint_points():
    """Generate key points for amended complaint"""
    
    complaint_points = {
        "Breach of Implied Warranty of Habitability": [
            "Defendants permitted mold growth for 18+ months affecting premature infant",
            "Failed to remediate despite professional MI&T report dated March 12, 2025",
            "90+ days elapsed since professional assessment with no proper remediation",
            "Visible mold remains exposed in unit with young children"
        ],
        
        "Negligence": [
            "Knew or should have known about serious mold hazard from MI&T report",
            "Failed to follow IICRC S520-2024 professional standards",
            "Attempted self-remediation despite lack of proper certification",
            "Created conflict of interest by acting as both inspector and remediator"
        ],
        
        "Breach of Statutory Duties": [
            "Violated Civil Code § 1942 - exceeded 30-day presumptive repair period",
            "Violated Civil Code § 1941.1 - failed to maintain habitable premises",
            "Pattern of 87.8% repair communications containing delays/excuses"
        ],
        
        "Retaliatory Eviction": [
            "July 19 eviction notice issued after code enforcement complaints",
            "Physical notices posted only after tenants asserted legal rights",
            "Pattern of intimidation including August 14, 2025 confrontation"
        ],
        
        "Intentional Infliction of Emotional Distress": [
            "Knowing exposure of premature infant to mold for 18 months",
            "Confrontational behavior when tenants exercised legal rights",
            "Surreptitious photographing of tenant's personal belongings"
        ],
        
        "Violation of Privacy": [
            "Photographed tenant's closet without notice or consent",
            "Demanded entry beyond statutory requirements",
            "Pattern of unauthorized recording of tenant's private spaces"
        ]
    }
    
    # Calculate damages
    damages = {
        "Special Damages": [
            "Medical expenses for child's respiratory treatment",
            "Cost of professional mold inspection (MI&T)",
            "Temporary relocation costs during proper remediation",
            "Property damage to personal belongings from mold"
        ],
        
        "General Damages": [
            "Pain and suffering from 18 months of mold exposure",
            "Emotional distress from child's health impacts",
            "Loss of quiet enjoyment of premises",
            "Ongoing anxiety from confrontational landlord behavior"
        ],
        
        "Punitive Damages": [
            "Willful violation of habitability standards",
            "Conscious disregard of child's health",
            "Pattern of deceptive repair practices (87.8% excuse rate)",
            "Fraudulent claim of mold inspector certification"
        ]
    }
    
    with open('amended_complaint_outline.txt', 'w') as f:
        f.write("AMENDED COMPLAINT OUTLINE - STONEMAN v. LANDLORDS\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("CAUSES OF ACTION:\n")
        f.write("-" * 40 + "\n")
        for cause, points in complaint_points.items():
            f.write(f"\n{cause}:\n")
            for point in points:
                f.write(f"  • {point}\n")
        
        f.write("\n\nDAMAGES:\n")
        f.write("-" * 40 + "\n")
        for damage_type, items in damages.items():
            f.write(f"\n{damage_type}:\n")
            for item in items:
                f.write(f"  • {item}\n")
    
    print(f"✅ Amended complaint outline saved to amended_complaint_outline.txt")

if __name__ == "__main__":
    import sys
    
    print("\nSTONEMAN LITIGATION TOOLS")
    print("=" * 40)
    
    if len(sys.argv) < 2 or sys.argv[1] == "all":
        # Run everything
        generate_discovery_questions()
        find_deposition_contradictions()
        generate_amended_complaint_points()
        print("\n✅ All litigation documents generated")
    elif sys.argv[1] == "discovery":
        generate_discovery_questions()
    elif sys.argv[1] == "deposition":
        find_deposition_contradictions()
    elif sys.argv[1] == "complaint":
        generate_amended_complaint_points()
    else:
        print("""
Usage:
  python stoneman_litigation.py all        # Generate all documents
  python stoneman_litigation.py discovery   # Discovery questions
  python stoneman_litigation.py deposition  # Deposition contradictions
  python stoneman_litigation.py complaint   # Amended complaint points
        """)
