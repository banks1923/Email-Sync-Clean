"""Dependency parser for syntactic analysis using spaCy.

Extracts grammatical dependencies and relationships from text.
"""

from typing import Any, Dict, List

import spacy
from loguru import logger


class DependencyParser:
    """
    Extract syntactic dependencies and grammatical relationships.
    """
    
    def __init__(self):
        """
        Initialize with spaCy model that includes parser.
        """
        self.name = "dependency"
        try:
            self.nlp = spacy.load("en_core_web_sm")
            if "parser" not in self.nlp.pipe_names:
                raise ValueError("spaCy model lacks parser component")
            self.available = True
            logger.info("Dependency parser initialized")
        except Exception as e:
            logger.error(f"Failed to initialize dependency parser: {e}")
            self.nlp = None
            self.available = False
    
    def extract_dependencies(self, text: str, doc_id: str = "") -> Dict[str, Any]:
        """Extract dependency parse from text.

        Args:
            text: Text to parse
            doc_id: Document identifier

        Returns:
            Dict with dependencies, subjects, objects, and actions
        """
        if not self.available:
            return {"success": False, "error": "Parser not available"}
        
        try:
            doc = self.nlp(text)
            
            # Extract dependencies
            dependencies = []
            for token in doc:
                dep_info = {
                    "text": token.text,
                    "lemma": token.lemma_,
                    "pos": token.pos_,
                    "tag": token.tag_,
                    "dep": token.dep_,
                    "head": token.head.text,
                    "head_pos": token.head.pos_,
                    "children": [child.text for child in token.children],
                    "ancestors": [anc.text for anc in token.ancestors]
                }
                dependencies.append(dep_info)
            
            # Extract subject-verb-object triples
            triples = self._extract_svo_triples(doc)
            
            # Extract noun phrases
            noun_phrases = [
                {
                    "text": chunk.text,
                    "root": chunk.root.text,
                    "root_dep": chunk.root.dep_
                }
                for chunk in doc.noun_chunks
            ]
            
            # Extract sentences with their roots
            sentences = []
            for sent in doc.sents:
                root = [token for token in sent if token.dep_ == "ROOT"]
                sentences.append({
                    "text": sent.text,
                    "root": root[0].text if root else None,
                    "root_lemma": root[0].lemma_ if root else None
                })
            
            return {
                "success": True,
                "doc_id": doc_id,
                "dependencies": dependencies,
                "svo_triples": triples,
                "noun_phrases": noun_phrases,
                "sentences": sentences,
                "stats": {
                    "token_count": len(doc),
                    "sentence_count": len(list(doc.sents)),
                    "noun_phrase_count": len(noun_phrases),
                    "triple_count": len(triples)
                }
            }
            
        except Exception as e:
            logger.error(f"Dependency parsing failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _extract_svo_triples(self, doc) -> List[Dict[str, str]]:
        """Extract subject-verb-object triples from parsed document.

        Returns:
            List of SVO triples with grammatical roles
        """
        triples = []
        
        for token in doc:
            # Find verbs
            if token.pos_ == "VERB":
                subject = None
                obj = None
                
                # Find subject
                for child in token.children:
                    if child.dep_ in ["nsubj", "nsubjpass"]:
                        subject = child
                    elif child.dep_ in ["dobj", "pobj"]:
                        obj = child
                
                if subject:
                    triple = {
                        "subject": subject.text,
                        "subject_pos": subject.pos_,
                        "verb": token.text,
                        "verb_lemma": token.lemma_,
                        "object": obj.text if obj else None,
                        "object_pos": obj.pos_ if obj else None,
                        "passive": "pass" in subject.dep_
                    }
                    triples.append(triple)
        
        return triples
    
    def extract_legal_actions(self, text: str) -> List[Dict[str, Any]]:
        """Extract legal actions and their actors from text.

        Specialized for legal documents to find who did what.
        """
        doc = self.nlp(text)
        actions = []
        
        legal_verbs = {
            "file", "filed", "filing", "submit", "submitted", "claim", "claimed",
            "allege", "alleged", "deny", "denied", "motion", "moved", "request",
            "requested", "order", "ordered", "grant", "granted", "dismiss",
            "dismissed", "appeal", "appealed", "rule", "ruled"
        }
        
        for token in doc:
            if token.lemma_.lower() in legal_verbs:
                action = {
                    "action": token.text,
                    "lemma": token.lemma_,
                    "actor": None,
                    "recipient": None,
                    "object": None,
                    "date": None,
                    "context": token.sent.text
                }
                
                # Find actor (subject)
                for child in token.children:
                    if child.dep_ in ["nsubj", "nsubjpass"]:
                        action["actor"] = child.text
                    elif child.dep_ == "dobj":
                        action["object"] = child.text
                    elif child.dep_ == "prep":
                        # Look for recipient after prepositions
                        for prep_child in child.children:
                            if prep_child.dep_ == "pobj":
                                action["recipient"] = prep_child.text
                
                # Find dates in same sentence
                for ent in token.sent.ents:
                    if ent.label_ == "DATE":
                        action["date"] = ent.text
                        break
                
                actions.append(action)
        
        return actions
    
    def is_available(self) -> bool:
        """
        Check if parser is available.
        """
        return self.available