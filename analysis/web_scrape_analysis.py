#!/usr/bin/env python3
"""
Research Paper Analysis and Visualization Script
Analyzes JSON files containing research papers and generates comprehensive visualizations
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from collections import Counter, defaultdict
import re
from pathlib import Path
import warnings
from urllib.parse import urlparse
from itertools import combinations
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.figure_factory as ff

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Set style for better-looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class PaperAnalyzer:
    def __init__(self, json_file_path, boolean_combinations_file):
        """Initialize the analyzer with data files."""
        self.json_file_path = json_file_path
        self.boolean_combinations_file = boolean_combinations_file
        self.papers = []
        self.boolean_combinations = {}
        self.output_dir = Path("analysis/plots/web_scrape") # Update path
        self.output_dir.mkdir(exist_ok=True)
        
        # Color palette for consistent styling
        self.colors = px.colors.qualitative.Set3
        
    def load_data(self):
        """Load papers data and boolean combinations."""
        try:
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                self.papers = json.load(f)
            print(f"Loaded {len(self.papers)} papers")
            
            with open(self.boolean_combinations_file, 'r', encoding='utf-8') as f:
                bool_data = json.load(f)
                self.boolean_combinations = {item['Combination_title']: item['boolean_combination'] 
                                           for item in bool_data}
            print(f"Loaded {len(self.boolean_combinations)} boolean combinations")
            
        except Exception as e:
            print(f"Error loading data: {e}")
            return False
        return True
    
    def clean_data(self):
        """Clean and preprocess the data."""
        cleaned_papers = []
        for paper in self.papers:
            if paper and isinstance(paper, dict):
                # Handle null values
                cleaned_paper = {
                    'title': paper.get('title', 'Unknown Title'),
                    'authors': paper.get('authors', 'Unknown Authors'),
                    'url': paper.get('url', ''),
                    'abstract': paper.get('abstract', ''),
                    'year': self._extract_year(paper.get('year')),
                    'extracted_text': paper.get('extracted_text', ''),
                    'source': self._extract_source(paper.get('url', ''))
                }
                cleaned_papers.append(cleaned_paper)
        
        self.papers = cleaned_papers
        print(f"Cleaned data: {len(self.papers)} valid papers")
    
    def _extract_year(self, year_data):
        """Extract and validate year information."""
        if not year_data or year_data == 'null':
            return None
        
        if isinstance(year_data, (int, float)):
            year = int(year_data)
            return year if 1900 <= year <= 2025 else None
        
        if isinstance(year_data, str):
            # Try to extract 4-digit year from string
            match = re.search(r'\b(19|20)\d{2}\b', year_data)
            if match:
                return int(match.group())
        
        return None
    
    def _extract_source(self, url):
        """Extract source platform from URL with dynamic domain recognition."""
        if not url or url == 'null':
            return 'Unknown'
        
        try:
            domain = urlparse(url).netloc.lower()
            
            # Define domain mappings for better organization and extensibility
            domain_mappings = {
                # Preprint servers
                'arxiv': 'arXiv',
                
                # Medical/Life Sciences databases
                'pubmed': 'PubMed',
                'ncbi': 'PubMed/NCBI',
                'cell.com': 'Cell Press',
                
                # Major publishers
                'nature.com': 'Nature Publishing',
                'springer': 'Springer',
                'elsevier': 'Elsevier',
                'sciencedirect': 'ScienceDirect',
                'wiley': 'Wiley',
                'mdpi.com': 'MDPI',
                'sagepub.com': 'SAGE Publications',
                
                # Professional societies
                'ieee': 'IEEE',
                'acm': 'ACM',
                
                # General science
                'science': 'Science Magazine',
                
                # DOI and resolver services
                'doi.org': 'DOI System',
                'resolver.sub.uni-goettingen.de': 'University Repository',
                'uni-goettingen': 'University Repository',
                
                # Additional common domains
                'taylor': 'Taylor & Francis',
                'tandfonline': 'Taylor & Francis Online',
                'cambridge': 'Cambridge University Press',
                'oxford': 'Oxford University Press',
                'oup.com': 'Oxford University Press',
                'plos': 'PLOS',
                'frontiersin': 'Frontiers',
                'bmc': 'BMC',
                'biomedcentral': 'BioMed Central',
                'hindawi': 'Hindawi',
                'karger': 'Karger',
                'thieme': 'Thieme',
                'jmir': 'JMIR Publications',
            }
            
            # Check for exact matches first
            for keyword, source_name in domain_mappings.items():
                if keyword in domain:
                    return source_name
            
            # Additional pattern matching for special cases
            if 'repository' in domain or 'repo' in domain:
                return 'Repository'
            elif 'university' in domain or 'edu' in domain:
                return 'Academic Institution'
            elif 'gov' in domain:
                return 'Government Source'
            elif 'research' in domain:
                return 'Research Institution'
            elif any(word in domain for word in ['journal', 'publication', 'publish']):
                return 'Academic Journal'
            else:
                # Extract main domain name for unknown sources
                domain_parts = domain.split('.')
                if len(domain_parts) >= 2:
                    main_domain = domain_parts[-2].title()  # Get second-to-last part and capitalize
                    return f"{main_domain} (Other)"
                return 'Other'
                
        except Exception as e:
            print(f"Error parsing URL '{url}': {e}")
            return 'Unknown'
    
    def plot_year_distribution(self):
        """Plot distribution of papers by year."""
        years = [p['year'] for p in self.papers if p['year'] is not None]
        
        if not years:
            print("No valid year data found")
            return
        
        # Create histogram
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # Year distribution histogram
        ax1.hist(years, bins=min(30, len(set(years))), alpha=0.7, color='skyblue', edgecolor='black')
        ax1.set_title('Distribution of Papers by Year', fontsize=16, fontweight='bold')
        ax1.set_xlabel('Year', fontsize=12)
        ax1.set_ylabel('Number of Papers', fontsize=12)
        ax1.grid(True, alpha=0.3)
        
        # Add statistics
        mean_year = np.mean(years)
        median_year = np.median(years)
        ax1.axvline(mean_year, color='red', linestyle='--', label=f'Mean: {mean_year:.1f}')
        ax1.axvline(median_year, color='orange', linestyle='--', label=f'Median: {median_year:.1f}')
        ax1.legend()
        
        # Cumulative distribution
        year_counts = Counter(years)
        sorted_years = sorted(year_counts.keys())
        cumulative_counts = np.cumsum([year_counts[year] for year in sorted_years])
        
        ax2.plot(sorted_years, cumulative_counts, marker='o', linewidth=2, markersize=4)
        ax2.set_title('Cumulative Distribution of Papers Over Time', fontsize=16, fontweight='bold')
        ax2.set_xlabel('Year', fontsize=12)
        ax2.set_ylabel('Cumulative Number of Papers', fontsize=12)
        ax2.grid(True, alpha=0.3)
        ax2.fill_between(sorted_years, cumulative_counts, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'year_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Interactive plotly version
        fig_plotly = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Papers by Year', 'Cumulative Distribution'),
            vertical_spacing=0.12
        )
        
        fig_plotly.add_trace(
            go.Histogram(x=years, nbinsx=min(30, len(set(years))), name='Papers per Year'),
            row=1, col=1
        )
        
        fig_plotly.add_trace(
            go.Scatter(x=sorted_years, y=cumulative_counts, mode='lines+markers', 
                      name='Cumulative Count', fill='tonexty'),
            row=2, col=1
        )
        
        fig_plotly.update_layout(
            title='Paper Publication Timeline Analysis',
            height=700,
            showlegend=True
        )
        
        fig_plotly.write_html(self.output_dir / 'year_distribution_interactive.html')
        
    def plot_source_distribution(self):
        """Plot distribution of papers by source."""
        sources = [p['source'] for p in self.papers]
        source_counts = Counter(sources)
        
        # Create pie chart and bar chart
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))
        
        # Pie chart
        colors = plt.cm.Set3(np.linspace(0, 1, len(source_counts)))
        wedges, texts, autotexts = ax1.pie(source_counts.values(), labels=source_counts.keys(), 
                                          autopct='%1.1f%%', colors=colors, startangle=90)
        ax1.set_title('Distribution of Papers by Source', fontsize=16, fontweight='bold')
        
        # Bar chart
        sources_sorted = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)
        ax2.bar([s[0] for s in sources_sorted], [s[1] for s in sources_sorted], color=colors)
        ax2.set_title('Papers Count by Source', fontsize=16, fontweight='bold')
        ax2.set_xlabel('Source', fontsize=12)
        ax2.set_ylabel('Number of Papers', fontsize=12)
        ax2.tick_params(axis='x', rotation=45)
        
        # Add count labels on bars
        for i, (source, count) in enumerate(sources_sorted):
            ax2.text(i, count + 0.01 * max(source_counts.values()), str(count), 
                    ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'source_distribution.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Interactive version
        fig_plotly = go.Figure()
        fig_plotly.add_trace(go.Bar(
            x=[s[0] for s in sources_sorted],
            y=[s[1] for s in sources_sorted],
            text=[s[1] for s in sources_sorted],
            textposition='auto',
            marker_color=px.colors.qualitative.Set3[:len(sources_sorted)]
        ))
        
        fig_plotly.update_layout(
            title='Distribution of Papers by Source Platform',
            xaxis_title='Source Platform',
            yaxis_title='Number of Papers',
            height=500
        )
        
        fig_plotly.write_html(self.output_dir / 'source_distribution_interactive.html')
        
    def plot_keyword_analysis(self):
        """Analyze and plot keyword occurrences based on boolean combinations."""
        # Combine all text for analysis
        all_texts = []
        for paper in self.papers:
            text = ""
            if paper['title'] and paper['title'] != 'Unknown Title':
                text += paper['title'] + " "
            if paper['abstract']:
                text += paper['abstract'] + " "
            if paper['extracted_text']:
                text += paper['extracted_text'] + " "
            all_texts.append(text.lower())
        
        # Count occurrences for each boolean combination category
        keyword_counts = {}
        paper_matches = defaultdict(set)  # Track which papers match which keywords
        
        for category, boolean_combo in self.boolean_combinations.items():
            # Extract keywords from boolean combination
            keywords = self._extract_keywords_from_boolean(boolean_combo)
            count = 0
            
            for i, text in enumerate(all_texts):
                found_match = False
                for keyword in keywords:
                    if keyword.lower() in text:
                        if not found_match:  # Count each paper only once per category
                            count += 1
                            found_match = True
                        paper_matches[category].add(i)
            
            keyword_counts[category] = count
        
        # Plot keyword frequency
        fig, ax = plt.subplots(figsize=(15, 10))
        
        categories = list(keyword_counts.keys())
        counts = list(keyword_counts.values())
        
        # Sort by count
        sorted_data = sorted(zip(categories, counts), key=lambda x: x[1], reverse=True)
        categories_sorted = [x[0] for x in sorted_data]
        counts_sorted = [x[1] for x in sorted_data]
        
        bars = ax.barh(categories_sorted, counts_sorted, color=plt.cm.viridis(np.linspace(0, 1, len(categories))))
        ax.set_title('Paper Count by Keyword Category', fontsize=16, fontweight='bold')
        ax.set_xlabel('Number of Papers', fontsize=12)
        ax.set_ylabel('Keyword Category', fontsize=12)
        
        # Add count labels
        for bar, count in zip(bars, counts_sorted):
            ax.text(bar.get_width() + 0.01 * max(counts_sorted), bar.get_y() + bar.get_height()/2, 
                   str(count), va='center', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'keyword_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Create intersection analysis
        self._plot_keyword_intersections(paper_matches)
        
        return paper_matches
    
    def _extract_keywords_from_boolean(self, boolean_combo):
        """Extract individual keywords from boolean combination string."""
        # Remove boolean operators and quotes, split by OR
        keywords = []
        parts = boolean_combo.replace('(', '').replace(')', '').split(' OR ')
        
        for part in parts:
            keyword = part.strip().strip('"').strip("'")
            if keyword and len(keyword) > 2:  # Avoid very short terms
                keywords.append(keyword)
        
        return keywords
    
    def _plot_keyword_intersections(self, paper_matches):
        """Plot intersections between different keyword categories."""
        categories = list(paper_matches.keys())
        
        # Calculate intersection matrix
        intersection_matrix = np.zeros((len(categories), len(categories)))
        
        for i, cat1 in enumerate(categories):
            for j, cat2 in enumerate(categories):
                if i <= j:
                    intersection = len(paper_matches[cat1].intersection(paper_matches[cat2]))
                    intersection_matrix[i][j] = intersection
                    intersection_matrix[j][i] = intersection
        
        # Create heatmap
        fig, ax = plt.subplots(figsize=(16, 12))
        
        # Truncate category names for better display
        display_categories = [cat[:30] + '...' if len(cat) > 30 else cat for cat in categories]
        
        sns.heatmap(intersection_matrix, annot=True, fmt='.0f', 
                   xticklabels=display_categories, yticklabels=display_categories,
                   cmap='YlOrRd', ax=ax)
        
        ax.set_title('Keyword Category Intersections (Number of Shared Papers)', 
                    fontsize=16, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.yticks(rotation=0)
        plt.tight_layout()
        plt.savefig(self.output_dir / 'keyword_intersections.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Interactive heatmap
        fig_plotly = go.Figure(data=go.Heatmap(
            z=intersection_matrix,
            x=display_categories,
            y=display_categories,
            colorscale='YlOrRd',
            text=intersection_matrix,
            texttemplate="%{text:.0f}",
            textfont={"size": 10}
        ))
        
        fig_plotly.update_layout(
            title='Interactive Keyword Category Intersection Matrix',
            xaxis_title='Keyword Categories',
            yaxis_title='Keyword Categories',
            height=800,
            width=1000
        )
        
        fig_plotly.write_html(self.output_dir / 'keyword_intersections_interactive.html')
    
    def plot_temporal_trends(self):
        """Plot temporal trends for different keyword categories."""
        # Get paper matches for keywords
        all_texts = []
        years = []
        
        for paper in self.papers:
            if paper['year'] is not None:
                text = ""
                if paper['title'] and paper['title'] != 'Unknown Title':
                    text += paper['title'] + " "
                if paper['abstract']:
                    text += paper['abstract'] + " "
                if paper['extracted_text']:
                    text += paper['extracted_text'] + " "
                all_texts.append(text.lower())
                years.append(paper['year'])
        
        if not years:
            print("No temporal data available")
            return
        
        # Track keyword trends over time
        yearly_keyword_counts = defaultdict(lambda: defaultdict(int))
        
        # Select top 5 most common keyword categories
        keyword_totals = {}
        for category, boolean_combo in list(self.boolean_combinations.items())[:8]:  # Limit to first 8 for readability
            keywords = self._extract_keywords_from_boolean(boolean_combo)
            total_count = 0
            
            for text in all_texts:
                for keyword in keywords:
                    if keyword.lower() in text:
                        total_count += 1
                        break
            keyword_totals[category] = total_count
        
        # Get top categories
        top_categories = sorted(keyword_totals.keys(), key=lambda x: keyword_totals[x], reverse=True)[:5]
        
        # Count by year for top categories
        for i, (text, year) in enumerate(zip(all_texts, years)):
            for category in top_categories:
                if category in self.boolean_combinations:
                    keywords = self._extract_keywords_from_boolean(self.boolean_combinations[category])
                    for keyword in keywords:
                        if keyword.lower() in text:
                            yearly_keyword_counts[year][category] += 1
                            break
        
        # Create temporal plot
        fig, ax = plt.subplots(figsize=(15, 8))
        
        all_years = sorted(set(years))
        colors = plt.cm.tab10(np.linspace(0, 1, len(top_categories)))
        
        for i, category in enumerate(top_categories):
            counts = [yearly_keyword_counts[year][category] for year in all_years]
            ax.plot(all_years, counts, marker='o', label=category[:30], 
                   color=colors[i], linewidth=2, markersize=4)
        
        ax.set_title('Temporal Trends of Top Keyword Categories', fontsize=16, fontweight='bold')
        ax.set_xlabel('Year', fontsize=12)
        ax.set_ylabel('Number of Papers', fontsize=12)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'temporal_trends.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Interactive version
        fig_plotly = go.Figure()
        
        for category in top_categories:
            counts = [yearly_keyword_counts[year][category] for year in all_years]
            fig_plotly.add_trace(go.Scatter(
                x=all_years,
                y=counts,
                mode='lines+markers',
                name=category[:30] + ('...' if len(category) > 30 else ''),
                line=dict(width=3),
                marker=dict(size=6)
            ))
        
        fig_plotly.update_layout(
            title='Interactive Temporal Trends of Keyword Categories',
            xaxis_title='Year',
            yaxis_title='Number of Papers',
            height=600,
            hovermode='x unified'
        )
        
        fig_plotly.write_html(self.output_dir / 'temporal_trends_interactive.html')
    
    def generate_summary_statistics(self):
        """Generate and save summary statistics."""
        stats = {
            'total_papers': len(self.papers),
            'papers_with_year': len([p for p in self.papers if p['year'] is not None]),
            'year_range': None,
            'most_common_source': None,
            'sources_count': len(set(p['source'] for p in self.papers)),
            'papers_with_abstract': len([p for p in self.papers if p['abstract'] and p['abstract'].strip()]),
            'papers_with_extracted_text': len([p for p in self.papers if p['extracted_text'] and p['extracted_text'].strip()])
        }
        
        # Year statistics
        years = [p['year'] for p in self.papers if p['year'] is not None]
        if years:
            stats['year_range'] = f"{min(years)} - {max(years)}"
            stats['mean_year'] = np.mean(years)
            stats['median_year'] = np.median(years)
        
        # Source statistics
        sources = [p['source'] for p in self.papers]
        source_counts = Counter(sources)
        stats['most_common_source'] = source_counts.most_common(1)[0] if source_counts else None
        stats['source_distribution'] = dict(source_counts)
        
        # Save statistics
        with open(self.output_dir / 'summary_statistics.json', 'w') as f:
            json.dump(stats, f, indent=2, default=str)
        
        # Create summary visualization
        self._plot_summary_dashboard(stats)
        
        return stats
    
    def _plot_summary_dashboard(self, stats):
        """Create a summary dashboard."""
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # Total papers
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.text(0.5, 0.5, f"{stats['total_papers']}\nTotal Papers", 
                ha='center', va='center', fontsize=20, fontweight='bold',
                transform=ax1.transAxes)
        ax1.set_xlim(0, 1)
        ax1.set_ylim(0, 1)
        ax1.set_xticks([])
        ax1.set_yticks([])
        ax1.set_title('Dataset Overview', fontweight='bold')
        
        # Papers with year
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.text(0.5, 0.5, f"{stats['papers_with_year']}\nWith Year Info", 
                ha='center', va='center', fontsize=20, fontweight='bold',
                transform=ax2.transAxes)
        ax2.set_xlim(0, 1)
        ax2.set_ylim(0, 1)
        ax2.set_xticks([])
        ax2.set_yticks([])
        ax2.set_title('Temporal Coverage', fontweight='bold')
        
        # Year range
        ax3 = fig.add_subplot(gs[0, 2])
        year_text = stats['year_range'] if stats['year_range'] else 'No Year Data'
        ax3.text(0.5, 0.5, f"{year_text}\nYear Range", 
                ha='center', va='center', fontsize=16, fontweight='bold',
                transform=ax3.transAxes)
        ax3.set_xlim(0, 1)
        ax3.set_ylim(0, 1)
        ax3.set_xticks([])
        ax3.set_yticks([])
        ax3.set_title('Time Span', fontweight='bold')
        
        # Source distribution (top 5)
        ax4 = fig.add_subplot(gs[1, :])
        if 'source_distribution' in stats:
            sources = list(stats['source_distribution'].keys())[:5]
            counts = [stats['source_distribution'][s] for s in sources]
            bars = ax4.bar(sources, counts, color=plt.cm.Set3(np.linspace(0, 1, len(sources))))
            ax4.set_title('Top 5 Sources Distribution', fontsize=14, fontweight='bold')
            ax4.set_ylabel('Number of Papers')
            
            # Add value labels on bars
            for bar, count in zip(bars, counts):
                ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01 * max(counts),
                        str(count), ha='center', va='bottom', fontweight='bold')
        
        # Data completeness
        ax5 = fig.add_subplot(gs[2, 0])
        completeness_data = [
            stats['papers_with_abstract'],
            stats['papers_with_extracted_text'],
            stats['papers_with_year']
        ]
        completeness_labels = ['Abstract', 'Extracted Text', 'Year']
        ax5.pie(completeness_data, labels=completeness_labels, autopct='%1.1f%%', startangle=90)
        ax5.set_title('Data Completeness', fontweight='bold')
        
        # Keyword categories count
        ax6 = fig.add_subplot(gs[2, 1:])
        ax6.text(0.5, 0.5, f"{len(self.boolean_combinations)}\nKeyword Categories\nfor Analysis", 
                ha='center', va='center', fontsize=18, fontweight='bold',
                transform=ax6.transAxes)
        ax6.set_xlim(0, 1)
        ax6.set_ylim(0, 1)
        ax6.set_xticks([])
        ax6.set_yticks([])
        ax6.set_title('Analysis Scope', fontweight='bold')
        
        plt.suptitle('Research Paper Dataset Summary Dashboard', fontsize=24, fontweight='bold', y=0.95)
        plt.savefig(self.output_dir / 'summary_dashboard.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def run_analysis(self):
        """Run the complete analysis pipeline."""
        print("Starting comprehensive paper analysis...")
        
        if not self.load_data():
            return
        
        self.clean_data()
        
        print("Generating visualizations...")
        
        # Generate all plots
        self.plot_year_distribution()
        print("✓ Year distribution plots created")
        
        self.plot_source_distribution()
        print("✓ Source distribution plots created")
        
        self.plot_keyword_analysis()
        print("✓ Keyword analysis plots created")
        
        self.plot_temporal_trends()
        print("✓ Temporal trends plots created")
        
        stats = self.generate_summary_statistics()
        print("✓ Summary statistics and dashboard created")
        
        print(f"\nAnalysis complete! All plots saved to '{self.output_dir}' directory.")
        print(f"Generated files:")
        for file in self.output_dir.glob('*'):
            print(f"  - {file.name}")
        
        return stats

# Example usage
if __name__ == "__main__":
    # Initialize analyzer
    analyzer = PaperAnalyzer('output/obtained_lit.json', 'output/unique_boolean_combinations.json')
    
    # Run complete analysis
    stats = analyzer.run_analysis()
    
    if stats:
        print(f"\nDataset Summary:")
        print(f"Total papers: {stats['total_papers']}")
        print(f"Papers with year: {stats['papers_with_year']}")
        print(f"Year range: {stats.get('year_range', 'N/A')}")
        print(f"Number of sources: {stats['sources_count']}")
        if stats['most_common_source']:
            print(f"Most common source: {stats['most_common_source'][0]} ({stats['most_common_source'][1]} papers)")