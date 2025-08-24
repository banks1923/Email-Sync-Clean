"""
Simplified Legal Boilerplate Remover using existing libraries + legal patterns

This approach uses established boilerplate removal libraries as a foundation
and adds legal-specific pattern matching on top.
"""

import re
from typing import Tuple

# Try to import existing libraries
try:
    import justext
    JUSTEXT_AVAILABLE = True
except ImportError:
    JUSTEXT_AVAILABLE = False

try:
    BOILERPIPE_AVAILABLE = True
except ImportError:
    BOILERPIPE_AVAILABLE = False


class SimpleLegalCleaner:
    """Simple legal document cleaner using existing libraries + legal patterns"""
    
    def __init__(self):
        # Legal boilerplate patterns (simplified from our full version)
        self.legal_boilerplate_patterns = [
            # Standard objections
            r'Responding Party objects.*?burdensome.*?oppressive.*?harassing.*?in its entirety',
            r'Responding Party does not have an obligation to obtain information.*?equally available',
            r'Responding Party is not required to prepare the Plaintiff.*?s case',
            
            # Standard responses  
            r'Subject to.*?objections.*?without waiving.*?responds as follows',
            r'After diligent search and reasonable inquiry.*?identifies and produces',
            r'Discovery is ongoing.*?reserves the right to.*?supplement.*?response',
            
            # Citations
            r'\(Sav-On Drugs.*?Inc\..*?v\..*?Superior Court.*?Los Angeles County.*?\(1975\).*?\)',
            r'\(CCP.*?§.*?2030\.220\(c\)\.\)',
        ]
        
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE | re.DOTALL)
            for pattern in self.legal_boilerplate_patterns
        ]
    
    def clean_legal_text(self, text: str, method: str = 'patterns') -> tuple[str, dict]:
        """
        Clean legal text using different methods
        
        Args:
            text: Input text to clean
            method: 'patterns', 'justext', 'hybrid'
            
        Returns:
            (cleaned_text, stats)
        """
        
        if method == 'justext' and JUSTEXT_AVAILABLE:
            return self._clean_with_justext(text)
        elif method == 'hybrid' and JUSTEXT_AVAILABLE:
            return self._clean_hybrid(text)
        else:
            return self._clean_with_patterns(text)
    
    def _clean_with_patterns(self, text: str) -> tuple[str, dict]:
        """Clean using only legal patterns (our approach)"""
        
        original_length = len(text)
        cleaned_text = text
        removals = 0
        
        for pattern in self.compiled_patterns:
            matches = list(pattern.finditer(cleaned_text))
            
            # Remove matches (reverse order to maintain indices)
            for match in reversed(matches):
                cleaned_text = (
                    cleaned_text[:match.start()] + 
                    '\n[BOILERPLATE REMOVED]\n' + 
                    cleaned_text[match.end():]
                )
                removals += 1
        
        stats = {
            'method': 'patterns',
            'original_length': original_length,
            'cleaned_length': len(cleaned_text),
            'removals': removals,
            'reduction_percent': (original_length - len(cleaned_text)) / original_length * 100
        }
        
        return cleaned_text, stats
    
    def _clean_with_justext(self, text: str) -> tuple[str, dict]:
        """Clean using jusText library"""
        
        # jusText expects HTML, so wrap plain text
        html_text = f"<html><body><p>{text.replace(chr(10), '</p><p>')}</p></body></html>"
        
        try:
            paragraphs = justext.justext(html_text, justext.get_stoplist("English"))
            
            clean_paragraphs = []
            total_paragraphs = len(paragraphs)
            removed_paragraphs = 0
            
            for paragraph in paragraphs:
                if not paragraph.is_boilerplate:
                    clean_paragraphs.append(paragraph.text)
                else:
                    removed_paragraphs += 1
            
            cleaned_text = '\n\n'.join(clean_paragraphs)
            
            stats = {
                'method': 'justext',
                'original_length': len(text),
                'cleaned_length': len(cleaned_text),
                'total_paragraphs': total_paragraphs,
                'removed_paragraphs': removed_paragraphs,
                'reduction_percent': (len(text) - len(cleaned_text)) / len(text) * 100
            }
            
            return cleaned_text, stats
            
        except Exception as e:
            print(f"jusText failed: {e}")
            return self._clean_with_patterns(text)
    
    def _clean_hybrid(self, text: str) -> tuple[str, dict]:
        """Clean using jusText + legal patterns"""
        
        # First pass: jusText
        cleaned_text, justext_stats = self._clean_with_justext(text)
        
        # Second pass: Legal patterns on jusText result
        final_cleaned, pattern_stats = self._clean_with_patterns(cleaned_text)
        
        stats = {
            'method': 'hybrid',
            'original_length': len(text),
            'cleaned_length': len(final_cleaned),
            'justext_removals': justext_stats.get('removed_paragraphs', 0),
            'pattern_removals': pattern_stats.get('removals', 0),
            'reduction_percent': (len(text) - len(final_cleaned)) / len(text) * 100
        }
        
        return final_cleaned, stats


def compare_methods(text: str):
    """Compare different cleaning methods on the same text"""
    
    cleaner = SimpleLegalCleaner()
    
    print("Comparing boilerplate removal methods:")
    print("=" * 60)
    
    methods = ['patterns']
    if JUSTEXT_AVAILABLE:
        methods.extend(['justext', 'hybrid'])
    
    results = {}
    
    for method in methods:
        cleaned, stats = cleaner.clean_legal_text(text, method)
        results[method] = (cleaned, stats)
        
        print(f"\n{method.upper()} METHOD:")
        print(f"  Original length: {stats['original_length']:,}")
        print(f"  Cleaned length:  {stats['cleaned_length']:,}")
        print(f"  Reduction:       {stats['reduction_percent']:.1f}%")
        
        if method == 'justext':
            print(f"  Paragraphs removed: {stats.get('removed_paragraphs', 0)}")
        elif method == 'patterns':
            print(f"  Pattern matches: {stats.get('removals', 0)}")
        elif method == 'hybrid':
            print(f"  jusText + Pattern removals: {stats.get('justext_removals', 0)} + {stats.get('pattern_removals', 0)}")
    
    return results


# Simple usage example
if __name__ == "__main__":
    
    sample_legal_text = """
REQUEST FOR PRODUCTION OF DOCUMENTS NO. 1:
ALL DOCUMENTS RELATING TO any lease agreement.

RESPONSE TO REQUEST FOR PRODUCTION OF DOCUMENTS NO. 1:
Responding Party objects to this request on the grounds that it is burdensome, oppressive, 
and harassing in its entirety. Responding Party objects that this request calls for documents already in the 
Propounding Party's possession. Responding Party does not have an obligation to obtain 
information that is equally available to the Propounding Party. (CCP § 2030.220(c).) Responding 
Party is not required to prepare the Plaintiff's case. (Sav-On Drugs, Inc. v. Superior Court of Los
Angeles County (1975) 15 Cal. 3d 1, 5.).

Subject to these objections but without waiving, Responding Party responds as follows: 
After diligent search and reasonable inquiry, Responding Party identifies and produces the 
following documents: DEF 000001-DEF 000046.
    """
    
    results = compare_methods(sample_legal_text)
    
    print(f"\n{'='*60}")
    print("BEST METHOD RESULT:")
    print(f"{'='*60}")
    
    # Show the pattern-based result (usually best for legal)
    if 'patterns' in results:
        cleaned_text, stats = results['patterns']
        print(cleaned_text)
