#!/usr/bin/env python3
"""
Word Cloud Analysis Module for Paper Buckets

This module performs word cloud analysis on papers bucketed by boolean search terms.
It processes academic papers, applies boolean filtering, and generates visualizations
showing word frequency patterns within each bucket.

Author: Claude
Date: August 2025
"""

import json
import jsonlines
import re
import os
from collections import defaultdict, Counter
from pathlib import Path
import logging
from typing import Dict, List, Tuple, Set, Optional, Union
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import pandas as pd
import numpy as np
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from nltk.chunk import ne_chunk
from nltk.tag import pos_tag
import nltk

# Download required NLTK data
def download_nltk_data():
    """Download required NLTK data with proper error handling"""
    required_data = [
        ('tokenizers/punkt', 'punkt'),
        ('tokenizers/punkt_tab', 'punkt_tab'),  # For newer NLTK versions
        ('corpora/stopwords', 'stopwords'),
        ('taggers/averaged_perceptron_tagger', 'averaged_perceptron_tagger'),
        ('taggers/averaged_perceptron_tagger_eng', 'averaged_perceptron_tagger_eng'),  # For newer versions
    ]
    
    for resource_path, resource_name in required_data:
        try:
            nltk.data.find(resource_path)
        except LookupError:
            try:
                print(f"Downloading NLTK resource: {resource_name}")
                nltk.download(resource_name, quiet=True)
            except Exception as e:
                print(f"Warning: Could not download {resource_name}: {e}")

download_nltk_data()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BooleanSearchEngine:
    """Handles complex boolean search operations on text"""
    
    def __init__(self):
        self.stemmer = PorterStemmer()
    
    def parse_boolean_expression(self, expression: str) -> List[str]:
        """
        Parse boolean expression to extract search terms
        Returns list of terms for matching
        """
        # Remove outer parentheses and split by OR
        expression = expression.strip('()')
        terms = []
        
        # Split by OR operators
        or_parts = re.split(r'\s+OR\s+', expression, flags=re.IGNORECASE)
        
        for part in or_parts:
            # Remove quotes and clean up
            term = part.strip().strip('"').strip("'")
            if term and len(term) > 1:  # Avoid single character terms
                terms.append(term.lower())
        
        return terms
    
    def matches_boolean_expression(self, text: str, expression: str) -> bool:
        """
        Check if text matches the boolean expression
        """
        if not text or not expression:
            return False
            
        text_lower = text.lower()
        terms = self.parse_boolean_expression(expression)
        
        # Check if any of the OR terms match
        for term in terms:
            if term in text_lower:
                return True
        
        return False


class TextPreprocessor:
    """Handles text cleaning and preprocessing for word cloud generation"""
    
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        
        # Add comprehensive non-informative words
        self.stop_words.update({
            # Common verbs (less conceptually relevant)
            'using', 'used', 'use', 'based', 'show', 'shows', 'showed', 'showing',
            'present', 'presents', 'presented', 'presenting', 'propose', 'proposed',
            'proposing', 'work', 'works', 'worked', 'working', 'make', 'makes',
            'made', 'making', 'give', 'gives', 'given', 'giving', 'take', 'takes',
            'taken', 'taking', 'get', 'gets', 'getting', 'got', 'find', 'finds',
            'found', 'finding', 'help', 'helps', 'helped', 'helping', 'provide',
            'provides', 'provided', 'providing', 'perform', 'performs', 'performed',
            'performing', 'apply', 'applies', 'applied', 'applying', 'develop',
            'develops', 'developed', 'developing', 'create', 'creates', 'created',
            'creating', 'build', 'builds', 'built', 'building', 'design', 'designs',
            'designed', 'designing', 'implement', 'implements', 'implemented',
            'implementing', 'train', 'trains', 'trained', 'training', 'test',
            'tests', 'tested', 'testing', 'evaluate', 'evaluates', 'evaluated',
            'evaluating', 'compare', 'compares', 'compared', 'comparing',
            'demonstrate', 'demonstrates', 'demonstrated', 'demonstrating',
            'achieve', 'achieves', 'achieved', 'achieving', 'improve', 'improves',
            'improved', 'improving', 'increase', 'increases', 'increased', 'increasing',
            'reduce', 'reduces', 'reduced', 'reducing', 'analyze', 'analyzes',
            'analyzed', 'analyzing', 'examine', 'examines', 'examined', 'examining',
            'investigate', 'investigates', 'investigated', 'investigating',
            'explore', 'explores', 'explored', 'exploring', 'consider', 'considers',
            'considered', 'considering', 'discuss', 'discusses', 'discussed',
            'discussing', 'address', 'addresses', 'addressed', 'addressing',
            'focus', 'focuses', 'focused', 'focusing', 'enable', 'enables',
            'enabled', 'enabling', 'allow', 'allows', 'allowed', 'allowing',
            'require', 'requires', 'required', 'requiring', 'include', 'includes',
            'included', 'including', 'contain', 'contains', 'contained', 'containing',
            'involve', 'involves', 'involved', 'involving', 'support', 'supports',
            'supported', 'supporting', 'obtain', 'obtains', 'obtained', 'obtaining',
            'collect', 'collects', 'collected', 'collecting', 'generate', 'generates',
            'generated', 'generating', 'produce', 'produces', 'produced', 'producing',
            
            # Adverbs
            'also', 'however', 'therefore', 'thus', 'furthermore', 'moreover',
            'additionally', 'although', 'though', 'whereas', 'nevertheless',
            'nonetheless', 'consequently', 'hence', 'accordingly', 'specifically',
            'particularly', 'especially', 'mainly', 'primarily', 'largely',
            'significantly', 'substantially', 'considerably', 'effectively',
            'efficiently', 'successfully', 'accurately', 'precisely', 'clearly',
            'obviously', 'evidently', 'apparently', 'presumably', 'probably',
            'possibly', 'potentially', 'generally', 'typically', 'commonly',
            'frequently', 'often', 'usually', 'normally', 'regularly',
            'consistently', 'constantly', 'continuously', 'simultaneously',
            'subsequently', 'previously', 'recently', 'currently', 'finally',
            'ultimately', 'eventually', 'gradually', 'immediately', 'directly',
            'indirectly', 'relatively', 'comparatively', 'relatively', 'extremely',
            'highly', 'very', 'quite', 'rather', 'fairly', 'somewhat', 'slightly',
            'moderately', 'reasonably', 'sufficiently', 'adequately', 'properly',
            'appropriately', 'suitably', 'accordingly', 'respectively', 'similarly',
            'likewise', 'alternatively', 'conversely', 'oppositely', 'differently',
            'separately', 'independently', 'jointly', 'collectively', 'individually',
            
            # Determiners and pronouns
            'this', 'that', 'these', 'those', 'such', 'each', 'every', 'all',
            'some', 'any', 'many', 'much', 'few', 'little', 'several', 'various',
            'different', 'certain', 'particular', 'specific', 'general', 'overall',
            'total', 'whole', 'entire', 'complete', 'full', 'partial', 'individual',
            'single', 'multiple', 'numerous', 'diverse', 'varied', 'distinct',
            'separate', 'unique', 'common', 'similar', 'same', 'other', 'another',
            'additional', 'extra', 'further', 'more', 'less', 'most', 'least',
            'first', 'second', 'third', 'last', 'final', 'initial', 'main',
            'primary', 'secondary', 'major', 'minor', 'key', 'important',
            'significant', 'relevant', 'related', 'associated', 'corresponding',
            'respective', 'given', 'certain', 'particular', 'specific',
            
            # Generic academic words
            'paper', 'study', 'research', 'analysis', 'results', 'result',
            'approach', 'method', 'methods', 'methodology', 'technique', 'techniques',
            'framework', 'model', 'models', 'system', 'systems', 'data', 'dataset',
            'datasets', 'algorithm', 'algorithms', 'process', 'processes', 'procedure',
            'procedures', 'task', 'tasks', 'problem', 'problems', 'issue', 'issues',
            'challenge', 'challenges', 'solution', 'solutions', 'tool', 'tools',
            'resource', 'resources', 'information', 'knowledge', 'concept', 'concepts',
            'idea', 'ideas', 'theory', 'theories', 'principle', 'principles',
            'factor', 'factors', 'element', 'elements', 'component', 'components',
            'feature', 'features', 'characteristic', 'characteristics', 'property',
            'properties', 'attribute', 'attributes', 'aspect', 'aspects', 'dimension',
            'dimensions', 'parameter', 'parameters', 'variable', 'variables',
            'measure', 'measures', 'metric', 'metrics', 'indicator', 'indicators',
            'criterion', 'criteria', 'standard', 'standards', 'benchmark', 'benchmarks',
            'baseline', 'baselines', 'reference', 'references', 'example', 'examples',
            'case', 'cases', 'instance', 'instances', 'sample', 'samples',
            'observation', 'observations', 'finding', 'findings', 'outcome', 'outcomes',
            'output', 'outputs', 'input', 'inputs', 'source', 'sources', 'target',
            'targets', 'goal', 'goals', 'objective', 'objectives', 'purpose',
            'purposes', 'aim', 'aims', 'application', 'applications', 'domain',
            'domains', 'field', 'fields', 'area', 'areas', 'scope', 'context',
            'contexts', 'setting', 'settings', 'environment', 'environments',
            'situation', 'situations', 'condition', 'conditions', 'state', 'states',
            'status', 'level', 'levels', 'degree', 'degrees', 'extent', 'range',
            'ranges', 'scale', 'scales', 'size', 'sizes', 'type', 'types', 'kind',
            'kinds', 'category', 'categories', 'class', 'classes', 'group', 'groups',
            'set', 'sets', 'collection', 'collections', 'series', 'sequence',
            'sequences', 'order', 'orders', 'structure', 'structures', 'organization',
            'organizations', 'arrangement', 'arrangements', 'configuration',
            'configurations', 'format', 'formats', 'form', 'forms', 'shape', 'shapes',
            'pattern', 'patterns', 'trend', 'trends', 'tendency', 'tendencies',
            'behavior', 'behaviors', 'behaviour', 'behaviours', 'performance',
            'performances', 'function', 'functions', 'functionality', 'operation',
            'operations', 'activity', 'activities', 'action', 'actions', 'step',
            'steps', 'stage', 'stages', 'phase', 'phases', 'part', 'parts',
            'section', 'sections', 'portion', 'portions', 'segment', 'segments',
            'unit', 'units', 'item', 'items', 'piece', 'pieces', 'bit', 'bits',
            'value', 'values', 'amount', 'amounts', 'number', 'numbers', 'quantity',
            'quantities', 'quality', 'qualities', 'rate', 'rates', 'ratio', 'ratios',
            'proportion', 'proportions', 'percentage', 'percentages', 'fraction',
            'fractions', 'share', 'shares', 'portion', 'portions',
            
            # Common acronyms and abbreviations (less conceptually meaningful)
            'et', 'al', 'etc', 'ie', 'eg', 'vs', 'via', 'inc', 'ltd', 'corp',
            'co', 'llc', 'usa', 'uk', 'eu', 'un', 'org', 'gov', 'edu', 'com',
            'net', 'www', 'http', 'https', 'html', 'xml', 'pdf', 'doc', 'txt',
            'csv', 'json', 'sql', 'api', 'url', 'uri', 'id', 'ids', 'no', 'nos',
            'fig', 'figs', 'table', 'tables', 'ref', 'refs', 'eqs', 'eq',
            'vol', 'pp', 'page', 'pages', 'chapter', 'chapters', 'section', 'sections',
            
            # Numbers and ordinals
            'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
            'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
            'seventeen', 'eighteen', 'nineteen', 'twenty', 'thirty', 'forty',
            'fifty', 'sixty', 'seventy', 'eighty', 'ninety', 'hundred', 'thousand',
            'million', 'billion', 'trillion', 'first', 'second', 'third', 'fourth',
            'fifth', 'sixth', 'seventh', 'eighth', 'ninth', 'tenth', 'eleventh',
            'twelfth', 'thirteenth', 'fourteenth', 'fifteenth', 'sixteenth',
            'seventeenth', 'eighteenth', 'nineteenth', 'twentieth', 'thirtieth',
            'fortieth', 'fiftieth', 'sixtieth', 'seventieth', 'eightieth',
            'ninetieth', 'hundredth', 'thousandth', 'millionth', 'billionth',
            
            # Time-related words (less conceptual)
            'time', 'times', 'period', 'periods', 'duration', 'durations',
            'moment', 'moments', 'instant', 'instants', 'interval', 'intervals',
            'year', 'years', 'month', 'months', 'week', 'weeks', 'day', 'days',
            'hour', 'hours', 'minute', 'minutes', 'second', 'seconds', 'today',
            'tomorrow', 'yesterday', 'now', 'then', 'when', 'while', 'during',
            'before', 'after', 'since', 'until', 'till', 'from', 'to', 'at',
            'in', 'on', 'by', 'within', 'throughout', 'across', 'over', 'under',
            'above', 'below', 'between', 'among', 'amongst', 'through', 'via',
            'around', 'near', 'close', 'far', 'away', 'here', 'there', 'where',
            'everywhere', 'anywhere', 'somewhere', 'nowhere',
            
            # Generic modifiers and qualifiers
            'new', 'old', 'recent', 'current', 'existing', 'previous', 'next',
            'future', 'past', 'present', 'modern', 'traditional', 'conventional',
            'standard', 'normal', 'regular', 'typical', 'usual', 'common', 'rare',
            'unique', 'special', 'particular', 'specific', 'general', 'broad',
            'wide', 'narrow', 'limited', 'extensive', 'comprehensive', 'complete',
            'incomplete', 'partial', 'full', 'empty', 'large', 'small', 'big',
            'little', 'huge', 'tiny', 'massive', 'minor', 'major', 'great',
            'good', 'bad', 'best', 'worst', 'better', 'worse', 'high', 'low',
            'higher', 'lower', 'highest', 'lowest', 'maximum', 'minimum', 'max',
            'min', 'top', 'bottom', 'upper', 'lower', 'right', 'left', 'correct',
            'wrong', 'true', 'false', 'real', 'actual', 'virtual', 'potential',
            'possible', 'impossible', 'likely', 'unlikely', 'probable', 'improbable',
            'certain', 'uncertain', 'sure', 'unsure', 'clear', 'unclear', 'obvious',
            'hidden', 'visible', 'invisible', 'public', 'private', 'open', 'closed',
            'available', 'unavailable', 'accessible', 'inaccessible', 'easy', 'hard',
            'difficult', 'simple', 'complex', 'complicated', 'basic', 'advanced',
            'elementary', 'sophisticated', 'crude', 'refined', 'rough', 'smooth',
            'sharp', 'blunt', 'strong', 'weak', 'powerful', 'powerless', 'active',
            'inactive', 'passive', 'dynamic', 'static', 'stable', 'unstable',
            'consistent', 'inconsistent', 'reliable', 'unreliable', 'valid', 'invalid',
            'accurate', 'inaccurate', 'precise', 'imprecise', 'exact', 'approximate',
            'perfect', 'imperfect', 'ideal', 'realistic', 'practical', 'theoretical',
            'abstract', 'concrete', 'physical', 'mental', 'intellectual', 'emotional',
            'social', 'cultural', 'political', 'economic', 'financial', 'technical',
            'scientific', 'academic', 'professional', 'personal', 'individual',
            'collective', 'public', 'private', 'local', 'global', 'national',
            'international', 'domestic', 'foreign', 'external', 'internal'
        })
        self.stemmer = PorterStemmer()
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove URLs, emails, and special characters
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        text = re.sub(r'\S+@\S+', '', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_meaningful_words(self, text: str, min_length: int = 3) -> List[str]:
        """Extract meaningful words from text, focusing on conceptual terms"""
        cleaned_text = self.clean_text(text)
        
        # Fallback tokenization if NLTK fails
        try:
            tokens = word_tokenize(cleaned_text)
        except Exception as e:
            logger.warning(f"NLTK tokenization failed, using simple split: {e}")
            # Simple fallback tokenization
            tokens = re.findall(r'\b[a-zA-Z]+\b', cleaned_text)
        
        # Get POS tags to filter by part of speech (if available)
        try:
            pos_tags = pos_tag(tokens)
        except Exception:
            # Fallback: assume all tokens are nouns for filtering
            pos_tags = [(token, 'NN') for token in tokens]
        
        # Filter tokens - focus on nouns and adjectives that represent concepts
        meaningful_words = []
        for token, pos in pos_tags:
            token_lower = token.lower()
            
            # Keep only nouns (NN, NNS, NNP, NNPS) and adjectives (JJ, JJR, JJS)
            # Also keep some specific technical terms regardless of POS
            if (len(token) >= min_length and 
                token_lower not in self.stop_words and
                not token.isdigit() and
                token.isalpha() and
                self._is_conceptual_word(token_lower, pos)):
                
                meaningful_words.append(token_lower)
        
        return meaningful_words
    
    def _is_conceptual_word(self, word: str, pos: str) -> bool:
        """Check if a word is conceptually meaningful"""
        # Focus on nouns and adjectives
        conceptual_pos = {'NN', 'NNS', 'NNP', 'NNPS', 'JJ', 'JJR', 'JJS'}
        
        # Allow technical/domain-specific terms even if not tagged as noun/adjective
        technical_terms = {
            'algorithm', 'algorithmic', 'algorithms', 'neural', 'network', 'networks',
            'machine', 'learning', 'deep', 'artificial', 'intelligence', 'ai',
            'model', 'models', 'modeling', 'training', 'supervised', 'unsupervised',
            'reinforcement', 'classification', 'regression', 'clustering',
            'optimization', 'gradient', 'descent', 'backpropagation', 'transformer',
            'attention', 'embedding', 'vector', 'matrix', 'tensor', 'computation',
            'computational', 'statistical', 'probability', 'probabilistic',
            'bayesian', 'markov', 'gaussian', 'distribution', 'feature', 'features',
            'extraction', 'selection', 'dimensionality', 'reduction', 'pca',
            'clustering', 'classification', 'prediction', 'forecasting',
            'recognition', 'detection', 'segmentation', 'generation', 'synthesis',
            'analysis', 'preprocessing', 'postprocessing', 'evaluation', 'validation',
            'testing', 'accuracy', 'precision', 'recall', 'f1', 'score', 'metric',
            'performance', 'benchmark', 'dataset', 'corpus', 'annotation',
            'labeling', 'crowdsourcing', 'scraping', 'crawling', 'mining',
            'extraction', 'nlp', 'nlg', 'nlu', 'cv', 'computer', 'vision',
            'speech', 'text', 'language', 'linguistic', 'semantic', 'syntactic',
            'sentiment', 'emotion', 'topic', 'document', 'corpus', 'tokenization',
            'stemming', 'lemmatization', 'parsing', 'tagging', 'chunking',
            'entity', 'relation', 'knowledge', 'graph', 'ontology', 'taxonomy',
            'humanitarian', 'crisis', 'disaster', 'emergency', 'response', 'relief',
            'aid', 'assistance', 'intervention', 'protection', 'vulnerability',
            'resilience', 'sustainability', 'development', 'poverty', 'inequality',
            'justice', 'rights', 'human', 'civil', 'social', 'economic', 'political',
            'governance', 'policy', 'regulation', 'compliance', 'ethics', 'ethical',
            'bias', 'fairness', 'transparency', 'explainability', 'interpretability',
            'accountability', 'responsibility', 'privacy', 'security', 'safety',
            'robustness', 'reliability', 'trustworthiness', 'verification',
            'validation', 'certification', 'audit', 'monitoring', 'surveillance',
            'healthcare', 'medical', 'clinical', 'diagnosis', 'treatment', 'therapy',
            'patient', 'doctor', 'nurse', 'hospital', 'clinic', 'pharmaceutical',
            'drug', 'medication', 'dosage', 'side', 'effect', 'adverse', 'reaction',
            'epidemiology', 'public', 'health', 'pandemic', 'epidemic', 'outbreak',
            'infection', 'disease', 'illness', 'syndrome', 'symptom', 'pathology',
            'biomedical', 'biotechnology', 'genomics', 'proteomics', 'bioinformatics',
            'environmental', 'climate', 'weather', 'temperature', 'precipitation',
            'carbon', 'emission', 'greenhouse', 'gas', 'renewable', 'energy',
            'sustainable', 'sustainability', 'conservation', 'biodiversity',
            'ecosystem', 'habitat', 'species', 'extinction', 'endangered',
            'pollution', 'contamination', 'waste', 'recycling', 'circular', 'economy',
            'infrastructure', 'transportation', 'mobility', 'urban', 'rural',
            'agriculture', 'farming', 'crop', 'livestock', 'food', 'nutrition',
            'security', 'safety', 'risk', 'hazard', 'threat', 'vulnerability',
            'mitigation', 'adaptation', 'preparedness', 'recovery', 'reconstruction',
            'education', 'learning', 'teaching', 'curriculum', 'pedagogy',
            'student', 'teacher', 'instructor', 'professor', 'academic', 'university',
            'college', 'school', 'classroom', 'online', 'distance', 'remote',
            'digital', 'technology', 'platform', 'software', 'hardware', 'device',
            'sensor', 'actuator', 'robot', 'robotic', 'automation', 'autonomous',
            'internet', 'web', 'cloud', 'server', 'database', 'storage', 'computing',
            'blockchain', 'cryptocurrency', 'bitcoin', 'ethereum', 'smart', 'contract',
            'iot', 'edge', 'fog', 'distributed', 'decentralized', 'peer', 'network',
            'protocol', 'encryption', 'cryptography', 'authentication', 'authorization',
            'access', 'control', 'firewall', 'intrusion', 'malware', 'virus',
            'cybersecurity', 'information', 'data', 'big', 'analytics', 'visualization'
        }
        
        return (pos in conceptual_pos) or (word in technical_terms)
    
    def get_word_frequencies(self, texts: List[str], top_n: int = 100) -> Dict[str, int]:
        """Get word frequencies from a list of texts"""
        all_words = []
        
        for text in texts:
            if text and text.strip():  # Skip empty texts
                try:
                    words = self.extract_meaningful_words(text)
                    all_words.extend(words)
                except Exception as e:
                    logger.warning(f"Error processing text: {e}")
                    continue
        
        if not all_words:
            logger.warning("No words extracted from texts")
            return {}
        
        # Count frequencies
        word_freq = Counter(all_words)
        
        # Return top N words
        return dict(word_freq.most_common(top_n))


class PaperBucketing:
    """Handles bucketing of papers based on boolean combinations"""
    
    def __init__(self, boolean_combinations: List[Dict]):
        self.boolean_combinations = boolean_combinations
        self.search_engine = BooleanSearchEngine()
        self.buckets = defaultdict(list)
    
    def bucket_papers(self, papers: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Bucket papers based on boolean combinations
        Returns dictionary with bucket names as keys and lists of papers as values
        """
        logger.info(f"Bucketing {len(papers)} papers into {len(self.boolean_combinations)} buckets")
        
        for paper in papers:
            # Get full text content for matching
            content = self._get_paper_content(paper)
            
            for combo in self.boolean_combinations:
                bucket_name = combo['WORD']
                boolean_expr = combo['boolean_combination']
                
                if self.search_engine.matches_boolean_expression(content, boolean_expr):
                    self.buckets[bucket_name].append(paper)
        
        # Log bucket sizes
        for bucket_name, papers_in_bucket in self.buckets.items():
            logger.info(f"Bucket '{bucket_name}': {len(papers_in_bucket)} papers")
        
        return dict(self.buckets)
    
    def _get_paper_content(self, paper: Dict) -> str:
        """Extract all relevant text content from a paper"""
        content_parts = []
        
        # Add title
        if 'title' in paper and paper['title']:
            content_parts.append(paper['title'])
        
        # Add abstract
        if 'abstract' in paper and paper['abstract']:
            content_parts.append(paper['abstract'])
        
        # Add extracted text (main content)
        if 'extracted_text' in paper and paper['extracted_text']:
            content_parts.append(paper['extracted_text'])
        
        return ' '.join(content_parts)


class WordCloudGenerator:
    """Generates word clouds and related visualizations"""
    
    def __init__(self, output_dir: str = "analysis/output/bucket"): # Update path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.preprocessor = TextPreprocessor()
        
        # Set up matplotlib style
        plt.style.use('default')
        sns.set_palette("husl")
    
    def generate_wordcloud(self, word_freq: Dict[str, int], title: str, 
                          filename: str) -> None:
        """Generate and save a word cloud"""
        if not word_freq:
            logger.warning(f"No words found for {title}")
            return
        
        # Create word cloud
        wordcloud = WordCloud(
            width=1200, 
            height=800,
            background_color='white',
            max_words=100,
            colormap='viridis',
            relative_scaling=0.5,
            random_state=42
        ).generate_from_frequencies(word_freq)
        
        # Create figure
        fig, ax = plt.subplots(figsize=(15, 10))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        ax.set_title(f"Word Cloud: {title}", fontsize=20, fontweight='bold', pad=20)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / f"{filename}_wordcloud.png", 
                   dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"Word cloud saved: {filename}_wordcloud.png")
    
    def generate_frequency_chart(self, word_freq: Dict[str, int], title: str, 
                                filename: str, top_n: int = 20) -> None:
        """Generate and save a frequency bar chart"""
        if not word_freq:
            return
        
        # Get top N words
        top_words = dict(list(word_freq.items())[:top_n])
        
        # Create bar chart
        fig, ax = plt.subplots(figsize=(12, 8))
        words = list(top_words.keys())
        frequencies = list(top_words.values())
        
        bars = ax.barh(words, frequencies)
        ax.set_xlabel('Frequency', fontsize=12)
        ax.set_ylabel('Words', fontsize=12)
        ax.set_title(f"Top {top_n} Most Frequent Words: {title}", 
                    fontsize=14, fontweight='bold')
        
        # Add value labels on bars
        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2, 
                   f'{int(width)}', ha='left', va='center', fontsize=10)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / f"{filename}_frequency_chart.png", 
                   dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        logger.info(f"Frequency chart saved: {filename}_frequency_chart.png")
    
    def generate_summary_report(self, bucket_stats: Dict, filename: str = "analysis_summary") -> None:
        """Generate a summary report of the analysis"""
        # Create summary statistics
        df_stats = pd.DataFrame(bucket_stats).T
        df_stats.columns = ['Paper Count', 'Unique Words', 'Total Words', 'Avg Words per Paper']
        df_stats = df_stats.sort_values('Paper Count', ascending=False)
        
        # Create summary plot
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # Plot 1: Paper count by bucket
        df_stats['Paper Count'].plot(kind='bar', ax=ax1, color='skyblue')
        ax1.set_title('Number of Papers per Bucket', fontweight='bold')
        ax1.set_ylabel('Paper Count')
        ax1.tick_params(axis='x', rotation=45)
        
        # Plot 2: Unique words by bucket
        df_stats['Unique Words'].plot(kind='bar', ax=ax2, color='lightgreen')
        ax2.set_title('Unique Words per Bucket', fontweight='bold')
        ax2.set_ylabel('Unique Word Count')
        ax2.tick_params(axis='x', rotation=45)
        
        # Plot 3: Total words by bucket
        df_stats['Total Words'].plot(kind='bar', ax=ax3, color='salmon')
        ax3.set_title('Total Words per Bucket', fontweight='bold')
        ax3.set_ylabel('Total Word Count')
        ax3.tick_params(axis='x', rotation=45)
        
        # Plot 4: Average words per paper
        df_stats['Avg Words per Paper'].plot(kind='bar', ax=ax4, color='gold')
        ax4.set_title('Average Words per Paper by Bucket', fontweight='bold')
        ax4.set_ylabel('Average Word Count')
        ax4.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / f"{filename}_summary.png", 
                   dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        # Save CSV summary
        df_stats.to_csv(self.output_dir / f"{filename}_statistics.csv")
        
        logger.info(f"Summary report saved: {filename}_summary.png and {filename}_statistics.csv")


class WordCloudAnalyzer:
    """Main analyzer class that orchestrates the entire analysis"""
    
    def __init__(self, papers_file: str, boolean_combinations_file: str, 
                 screening_file: Optional[str] = None):
        self.papers_file = papers_file
        self.boolean_combinations_file = boolean_combinations_file
        self.screening_file = screening_file
        
        # Load data
        self.papers = self._load_papers()
        self.boolean_combinations = self._load_boolean_combinations()
        self.screening_results = self._load_screening_results() if screening_file else None
        
        # Initialize components
        self.bucketing = PaperBucketing(self.boolean_combinations)
        self.wordcloud_gen = WordCloudGenerator()
        self.preprocessor = TextPreprocessor()
    
    def _load_papers(self) -> List[Dict]:
        """Load papers from JSON file"""
        try:
            with open(self.papers_file, 'r', encoding='utf-8') as f:
                papers = json.load(f)
            logger.info(f"Loaded {len(papers)} papers from {self.papers_file}")
            return papers
        except Exception as e:
            logger.error(f"Error loading papers: {e}")
            return []
    
    def _load_boolean_combinations(self) -> List[Dict]:
        """Load boolean combinations from JSON file"""
        try:
            with open(self.boolean_combinations_file, 'r', encoding='utf-8') as f:
                combinations = json.load(f)
            logger.info(f"Loaded {len(combinations)} boolean combinations")
            return combinations
        except Exception as e:
            logger.error(f"Error loading boolean combinations: {e}")
            return []
    
    def _load_screening_results(self) -> List[Dict]:
        """Load screening results from JSONL file"""
        try:
            results = []
            with jsonlines.open(self.screening_file) as reader:
                for obj in reader:
                    results.append(obj)
            logger.info(f"Loaded {len(results)} screening results")
            return results
        except Exception as e:
            logger.error(f"Error loading screening results: {e}")
            return []
    
    def run_analysis(self) -> None:
        """Run the complete word cloud analysis"""
        logger.info("Starting word cloud analysis...")
        
        # Step 1: Bucket papers
        buckets = self.bucketing.bucket_papers(self.papers)
        
        if not buckets:
            logger.error("No papers were bucketed. Check boolean combinations and paper content.")
            return
        
        # Step 2: Analyze each bucket
        bucket_stats = {}
        
        for bucket_name, papers_in_bucket in buckets.items():
            if not papers_in_bucket:
                logger.warning(f"Skipping empty bucket: {bucket_name}")
                continue
            
            logger.info(f"Analyzing bucket: {bucket_name} ({len(papers_in_bucket)} papers)")
            
            # Extract text from papers in bucket
            texts = []
            for paper in papers_in_bucket:
                content = self._get_paper_text(paper)
                if content:
                    texts.append(content)
            
            if not texts:
                logger.warning(f"No text content found in bucket: {bucket_name}")
                continue
            
            # Get word frequencies
            word_freq = self.preprocessor.get_word_frequencies(texts)
            
            if word_freq:
                # Generate visualizations
                safe_filename = self._make_safe_filename(bucket_name)
                
                self.wordcloud_gen.generate_wordcloud(
                    word_freq, bucket_name, safe_filename
                )
                
                self.wordcloud_gen.generate_frequency_chart(
                    word_freq, bucket_name, safe_filename
                )
                
                # Collect statistics
                total_words = sum(word_freq.values())
                bucket_stats[bucket_name] = [
                    len(papers_in_bucket),
                    len(word_freq),
                    total_words,
                    round(total_words / len(papers_in_bucket), 2)
                ]
        
        # Step 3: Generate summary report
        if bucket_stats:
            self.wordcloud_gen.generate_summary_report(bucket_stats)
        
        logger.info("Word cloud analysis completed!")
        logger.info(f"Results saved in: {self.wordcloud_gen.output_dir}")
    
    def _get_paper_text(self, paper: Dict) -> str:
        """Extract text content from paper for analysis"""
        content_parts = []
        
        if 'title' in paper and paper['title']:
            content_parts.append(paper['title'])
        
        if 'abstract' in paper and paper['abstract']:
            content_parts.append(paper['abstract'])
        
        if 'extracted_text' in paper and paper['extracted_text']:
            content_parts.append(paper['extracted_text'])
        
        return ' '.join(content_parts)
    
    def _make_safe_filename(self, name: str) -> str:
        """Convert bucket name to safe filename"""
        # Remove special characters and replace spaces
        safe_name = re.sub(r'[^\w\s-]', '', name)
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        return safe_name.lower().strip('_')


def main():
    """Main function to run the analysis"""
    # Configuration
    papers_file = "../output/obtained_lit.json"
    boolean_combinations_file = "../data/boolean_combinations.json"
    screening_file = "../output/screening_results_20250811_204753.jsonl"
    
    # Check if files exist
    for file_path in [papers_file, boolean_combinations_file]:
        if not os.path.exists(file_path):
            logger.error(f"Required file not found: {file_path}")
            return
    
    try:
        # Initialize and run analyzer
        analyzer = WordCloudAnalyzer(
            papers_file=papers_file,
            boolean_combinations_file=boolean_combinations_file,
            screening_file=screening_file if os.path.exists(screening_file) else None
        )
        
        analyzer.run_analysis()
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()