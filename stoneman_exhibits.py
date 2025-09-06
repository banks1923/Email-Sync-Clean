#!/usr/bin/env python3
"""
Stoneman Case Analysis - Quick Stats & Exhibits
Generate litigation exhibits and statistical analysis
"""
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

STONEMAN_DIR = Path("/Users/jim/Projects/Litigator_solo/data/Stoneman_dispute")

def analyze_repair_patterns():
    """Generate statistical analysis of repair avoidance pattern"""
    
    print("\n📊 REPAIR AVOIDANCE PATTERN ANALYSIS")
    print("=" * 60)
    
    # Based on the identity analysis document
    stats = {
        "Total Repair Emails": 188,
        "Emails with Excuses/Delays": 165,
        "Excuse Rate": "87.8%",
        "Scheduled Repairs": 135,
        "Cancelled Repairs": 41,
        "Delayed Repairs": 60,
        "Total Disruptions": 101,
        "Failure Rate": "74.8%",
        "Top Excuses": {
            "Contractor issues": 107,
            "Scheduling conflicts": 89,
            "Parts/materials unavailable": 72,
            "Weather delays": 45,
            "Need more assessment": 38
        }
    }
    
    # Create exhibit format
    with open('EXHIBIT_A_repair_pattern.txt', 'w') as f:
        f.write("EXHIBIT A - SYSTEMATIC REPAIR AVOIDANCE PATTERN\n")
        f.write("=" * 60 + "\n\n")
        f.write("STATISTICAL SUMMARY OF 426 DOCUMENTS (420 EMAILS)\n")
        f.write("-" * 40 + "\n\n")
        
        f.write("KEY FINDINGS:\n\n")
        f.write(f"• {stats['Excuse Rate']} of repair communications contain excuses\n")
        f.write(f"• {stats['Failure Rate']} failure rate on scheduled repairs\n")
        f.write(f"• {stats['Total Disruptions']} total disruptions out of {stats['Scheduled Repairs']} scheduled repairs\n\n")
        
        f.write("EXCUSE FREQUENCY ANALYSIS:\n")
        for excuse, count in stats['Top Excuses'].items():
            percentage = (count / stats['Total Repair Emails']) * 100
            f.write(f"  {excuse:30} {count:3} mentions ({percentage:.1f}%)\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("LEGAL SIGNIFICANCE:\n")
        f.write("This pattern demonstrates systematic bad faith in repair obligations,\n")
        f.write("supporting claims for breach of warranty of habitability,\n")
        f.write("negligence, and potentially punitive damages.\n")
    
    print(f"✅ Exhibit A saved: EXHIBIT_A_repair_pattern.txt")
    return stats

def create_timeline_exhibit():
    """Create a formatted timeline suitable for court exhibit"""
    
    key_dates = [
        ("January 2024", "Water intrusion and mold issues begin (18 months before present)"),
        ("March 12, 2025", "MI&T professional mold inspection conducted by Sean Dare"),
        ("May 5, 2025", "MI&T report provided to landlord's counsel during discovery"),
        ("July 19, 2025", "Surprise eviction notice issued (potential retaliation)"),
        ("August 14, 2025 9:49 AM", "Jennifer documents denied repair after Dean confrontation"),
        ("August 14, 2025 2:02 PM", "Landlord claims no mold found, disputes entry rights"),
        ("August 14, 2025 4:47 PM", "Tenants cite CC §1954, assert contractor access sufficient"),
        ("August 14, 2025 4:47 PM", "Dean claims 'certified mold inspector' status"),
        ("August 16-17, 2025", "Proposed remediation by Dean (violates IICRC standards)"),
        ("August 21, 2025", "Current date - 90+ days since professional assessment")
    ]
    
    with open('EXHIBIT_B_timeline.txt', 'w') as f:
        f.write("EXHIBIT B - CHRONOLOGICAL TIMELINE OF EVENTS\n")
        f.write("STONEMAN PROPERTY - MOLD & HABITABILITY ISSUES\n")
        f.write("=" * 60 + "\n\n")
        
        for date, event in key_dates:
            f.write(f"{date:25} {event}\n")
            f.write("-" * 60 + "\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("CRITICAL TIMEFRAMES:\n\n")
        f.write("• 18 MONTHS: Duration of mold exposure to premature infant\n")
        f.write("• 161 DAYS: Since professional mold inspection (March 12)\n")
        f.write("• 90+ DAYS: Since landlords received remediation recommendations\n")
        f.write("• 30 DAYS: California statutory presumption for repairs (exceeded)\n")
    
    print(f"✅ Exhibit B saved: EXHIBIT_B_timeline.txt")

def create_violation_summary():
    """Create summary of all legal violations for quick reference"""
    
    violations = {
        "California Civil Code Violations": [
            "§1941.1 - Failure to maintain habitable premises (18 months mold)",
            "§1942 - Exceeded 30-day repair presumption (90+ days)",
            "§1954 - Demanding unnecessary personal presence during repairs",
            "§1942.5 - Potential retaliatory eviction within 180 days"
        ],
        
        "Industry Standard Violations": [
            "IICRC S520-2024 § 12.2.1 - Same party inspection and remediation",
            "IICRC S520-2024 § 14.3 - Lack of independent assessment",
            "EPA Guidelines - Failure to address water source before remediation",
            "OSHA Standards - Exposure of residents during mold work"
        ],
        
        "Health & Safety Code Violations": [
            "H&S Code §17920.3 - Substandard conditions (mold infestation)",
            "H&S Code §17920.10 - Inadequate weather protection",
            "Local ordinances - Failure to abate cited conditions"
        ],
        
        "Potential Criminal Violations": [
            "Penal Code §484 - Fraud (false mold certification claims)",
            "Penal Code §646.9 - Harassment pattern",
            "B&P Code §7027 - Unlicensed contractor work"
        ]
    }
    
    with open('EXHIBIT_C_violations.txt', 'w') as f:
        f.write("EXHIBIT C - COMPREHENSIVE VIOLATION SUMMARY\n")
        f.write("=" * 60 + "\n\n")
        
        for category, items in violations.items():
            f.write(f"{category}:\n")
            f.write("-" * 40 + "\n")
            for item in items:
                f.write(f"  ✗ {item}\n")
            f.write("\n")
        
        f.write("=" * 60 + "\n")
        f.write("TOTAL VIOLATIONS IDENTIFIED: {}\n".format(
            sum(len(items) for items in violations.values())
        ))
    
    print(f"✅ Exhibit C saved: EXHIBIT_C_violations.txt")

def create_damage_calculation():
    """Create damage calculation worksheet"""
    
    with open('damage_calculation.txt', 'w') as f:
        f.write("STONEMAN CASE - DAMAGE CALCULATION WORKSHEET\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("SPECIAL DAMAGES (Documentable):\n")
        f.write("-" * 40 + "\n")
        f.write("[ ] Medical expenses - child respiratory treatment    $______\n")
        f.write("[ ] MI&T mold inspection cost                        $______\n")
        f.write("[ ] Future remediation (proper IICRC contractor)     $______\n")
        f.write("[ ] Personal property damaged by mold                $______\n")
        f.write("[ ] Temporary relocation during remediation          $______\n")
        f.write("[ ] Lost wages for medical appointments              $______\n")
        f.write("                                          SUBTOTAL:  $______\n\n")
        
        f.write("GENERAL DAMAGES (Pain & Suffering):\n")
        f.write("-" * 40 + "\n")
        f.write("18 months of mold exposure × $____/month =          $______\n")
        f.write("Child's respiratory distress × multiplier =         $______\n")
        f.write("Emotional distress from confrontations =            $______\n")
        f.write("Loss of quiet enjoyment =                           $______\n")
        f.write("                                          SUBTOTAL:  $______\n\n")
        
        f.write("STATUTORY DAMAGES:\n")
        f.write("-" * 40 + "\n")
        f.write("CC §1942.4 (Actual damages + $100-$5,000)          $______\n")
        f.write("CC §789.3 (Retaliatory eviction: $2,000 min)       $______\n")
        f.write("                                          SUBTOTAL:  $______\n\n")
        
        f.write("PUNITIVE DAMAGES:\n")
        f.write("-" * 40 + "\n")
        f.write("Factors:\n")
        f.write("• Willful disregard of infant health (18 months)\n")
        f.write("• Fraudulent mold certification claims\n")
        f.write("• 87.8% repair excuse rate shows malice\n")
        f.write("• Violation of professional standards\n")
        f.write("Suggested multiplier: 3-10x compensatory =          $______\n\n")
        
        f.write("=" * 60 + "\n")
        f.write("TOTAL DAMAGES SOUGHT:                               $______\n")
    
    print(f"✅ Damage calculation worksheet saved: damage_calculation.txt")

def quick_case_summary():
    """Generate a one-page case summary"""
    
    with open('case_summary.txt', 'w') as f:
        f.write("STONEMAN MOLD LITIGATION - CASE SUMMARY\n")
        f.write("=" * 60 + "\n\n")
        
        f.write("PARTIES:\n")
        f.write("Plaintiffs: Jennifer & James Burbank (tenants w/ premature infant)\n")
        f.write("Defendants: Brad & Dean (landlords), 518 Stoneman LLC\n\n")
        
        f.write("KEY FACTS:\n")
        f.write("• 18-month ongoing mold exposure to premature infant\n")
        f.write("• Professional inspection ignored for 90+ days\n")
        f.write("• 87.8% of repair communications contain excuses\n")
        f.write("• Landlord falsely claims mold certification\n")
        f.write("• Retaliatory eviction after code complaints\n\n")
        
        f.write("STRONGEST CLAIMS:\n")
        f.write("1. Breach of Habitability (CC §1941.1) - SLAM DUNK\n")
        f.write("2. Negligence - Strong (knew of danger to infant)\n")
        f.write("3. Retaliation (CC §1942.5) - Strong timeline evidence\n")
        f.write("4. Fraud - Moderate (false certification claims)\n\n")
        
        f.write("SMOKING GUNS:\n")
        f.write("• MI&T report + 90-day inaction\n")
        f.write("• Statistical proof of repair avoidance (87.8%)\n")
        f.write("• Video of surreptitious photographing\n")
        f.write("• Dean's conflicting mold claims\n\n")
        
        f.write("IMMEDIATE ACTIONS:\n")
        f.write("1. File amended complaint with all claims\n")
        f.write("2. Depose Dean re: certification fraud\n")
        f.write("3. Subpoena all contractor communications\n")
        f.write("4. Motion for preliminary injunction (immediate remediation)\n")
        f.write("5. Document ongoing health impacts\n")
    
    print(f"✅ Case summary saved: case_summary.txt")

if __name__ == "__main__":
    print("\nGENERATING LITIGATION EXHIBITS & ANALYSIS")
    print("=" * 60)
    
    # Run all analyses
    analyze_repair_patterns()
    create_timeline_exhibit()
    create_violation_summary()
    create_damage_calculation()
    quick_case_summary()
    
    print("\n✅ ALL EXHIBITS GENERATED")
    print("\nFiles created:")
    print("  • EXHIBIT_A_repair_pattern.txt")
    print("  • EXHIBIT_B_timeline.txt")
    print("  • EXHIBIT_C_violations.txt")
    print("  • damage_calculation.txt")
    print("  • case_summary.txt")
    print("\n📋 Ready for filing/deposition/mediation")
