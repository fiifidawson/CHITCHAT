import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as pyo
from pathlib import Path
from collections import Counter, defaultdict
import warnings
warnings.filterwarnings('ignore')

# Set up plotting styles
plt.style.use('default')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.alpha'] = 0.3

def load_data(filepath):
    """Load and parse the JSONL file"""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    return data

def create_output_dir(output_dir):
    """Create output directory if it doesn't exist"""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

def flatten_screening_data(data):
    """Flatten the nested screening results for easier analysis"""
    flattened = []
    
    for entry in data:
        if 'screening_results' not in entry:
            continue
            
        sr = entry['screening_results']
        flat_entry = {
            'title': entry.get('title', ''),
            'year': entry.get('original_metadata', {}).get('year', 0),
            'authors': entry.get('original_metadata', {}).get('authors', ''),
            'final_priority': entry.get('final_priority', 'UNKNOWN'),
            'priority_level': sr.get('priority_level', 'UNKNOWN'),
        }
        
        # Publication quality metrics
        if 'publication_quality' in sr:
            pq = sr['publication_quality']
            flat_entry.update({
                'venue_name': pq.get('venue_name', ''),
                'is_top_tier_venue': pq.get('is_top_tier_venue', False),
                'publication_year': pq.get('publication_year', 0),
                'citation_count': pq.get('citation_count', -1),
                'is_recent_promising': pq.get('is_recent_promising', False),
                'full_text_english': pq.get('full_text_english', True)
            })
        
        # Technical scope
        if 'technical_scope' in sr:
            ts = sr['technical_scope']
            flat_entry.update({
                'addresses_llm_data_collection': ts.get('addresses_llm_data_collection', False),
                'addresses_text_corpus_creation': ts.get('addresses_text_corpus_creation', False),
                'addresses_web_scraping_nlp': ts.get('addresses_web_scraping_nlp', False),
                'addresses_multilingual_compilation': ts.get('addresses_multilingual_compilation', False)
            })
        
        # Ethical flags
        if 'ethical_flags' in sr:
            ef = sr['ethical_flags']
            flat_entry.update({
                'focuses_only_on_performance': ef.get('focuses_only_on_performance', False),
                'disregards_ethical_principles': ef.get('disregards_ethical_principles', False),
                'missing_ethical_approval': ef.get('missing_ethical_approval', False),
                'violates_humanitarian_principles': ef.get('violates_humanitarian_principles', False)
            })
        
        # Humanitarian principles
        if 'humanitarian_principles' in sr:
            hp = sr['humanitarian_principles']
            flat_entry.update({
                'humanity_score': hp.get('humanity_score', 0),
                'impartiality_score': hp.get('impartiality_score', 0),
                'independence_score': hp.get('independence_score', 0),
                'neutrality_score': hp.get('neutrality_score', 0)
            })
        
        # Methodology contributions
        if 'methodology_contributions' in sr:
            mc = sr['methodology_contributions']
            flat_entry.update({
                'novel_methodology': mc.get('novel_methodology', False),
                'systematic_evaluation': mc.get('systematic_evaluation', False),
                'reproducible_implementation': mc.get('reproducible_implementation', False)
            })
        
        # Ethical contributions
        if 'ethical_contributions' in sr:
            ec = sr['ethical_contributions']
            flat_entry.update({
                'explicit_framework': ec.get('explicit_framework', False),
                'empirical_bias_analysis': ec.get('empirical_bias_analysis', False),
                'harm_mitigation_strategies': ec.get('harm_mitigation_strategies', False),
                'policy_recommendations': ec.get('policy_recommendations', False),
                'acknowledges_tensions': ec.get('acknowledges_tensions', False)
            })
        
        flattened.append(flat_entry)
    
    return pd.DataFrame(flattened)

def plot_priority_distribution(df, output_dir):
    """Create priority level distribution plots"""
    # Static plot
    plt.figure(figsize=(12, 6))
    
    plt.subplot(1, 2, 1)
    priority_counts = df['final_priority'].value_counts()
    colors = sns.color_palette("viridis", len(priority_counts))
    plt.pie(priority_counts.values, labels=priority_counts.index, autopct='%1.1f%%', 
            colors=colors, startangle=90)
    plt.title('Final Priority Distribution', fontsize=14, fontweight='bold')
    
    plt.subplot(1, 2, 2)
    priority_level_counts = df['priority_level'].value_counts()
    sns.barplot(x=priority_level_counts.index, y=priority_level_counts.values, 
                palette="viridis")
    plt.title('Screening Priority Level Distribution', fontsize=14, fontweight='bold')
    plt.xlabel('Priority Level')
    plt.ylabel('Count')
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/priority_distribution.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # Interactive plot
    fig = make_subplots(rows=1, cols=2, 
                       specs=[[{"type": "pie"}, {"type": "bar"}]],
                       subplot_titles=('Final Priority Distribution', 
                                     'Screening Priority Level Distribution'))
    
    fig.add_trace(go.Pie(labels=priority_counts.index, values=priority_counts.values,
                        name="Final Priority"), row=1, col=1)
    
    fig.add_trace(go.Bar(x=priority_level_counts.index, y=priority_level_counts.values,
                        name="Priority Level", 
                        marker=dict(color=px.colors.qualitative.Set3[:len(priority_level_counts)])), 
                        row=1, col=2)
    
    fig.update_layout(title_text="Priority Analysis Dashboard", showlegend=False)
    fig.write_html(f'{output_dir}/priority_distribution_interactive.html')

def plot_publication_analysis(df, output_dir):
    """Create publication quality analysis plots"""
    # Year distribution
    plt.figure(figsize=(15, 10))
    
    plt.subplot(2, 2, 1)
    valid_years = df[df['publication_year'] > 0]
    if len(valid_years) > 0:
        year_counts = valid_years['publication_year'].value_counts().sort_index()
        plt.plot(year_counts.index, year_counts.values, marker='o', linewidth=2, markersize=6)
        plt.title('Publications by Year', fontsize=14, fontweight='bold')
        plt.xlabel('Year')
        plt.ylabel('Number of Publications')
        plt.grid(True, alpha=0.3)
    else:
        plt.text(0.5, 0.5, 'No valid publication years', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title('Publications by Year', fontsize=14, fontweight='bold')
    
    plt.subplot(2, 2, 2)
    top_tier_counts = df['is_top_tier_venue'].value_counts()
    colors = ['#ff9999', '#66b3ff']
    labels = ['Non-Top Tier', 'Top Tier'] if True in top_tier_counts.index else ['Non-Top Tier']
    values = [top_tier_counts.get(False, 0), top_tier_counts.get(True, 0)]
    if values[1] == 0:  # If no True values
        labels = ['Non-Top Tier']
        values = [values[0]]
        colors = ['#ff9999']
    plt.pie(values, labels=labels, autopct='%1.1f%%', colors=colors[:len(values)], startangle=90)
    plt.title('Top Tier Venue Distribution', fontsize=14, fontweight='bold')
    
    plt.subplot(2, 2, 3)
    english_counts = df['full_text_english'].value_counts()
    english_labels = []
    english_values = []
    if False in english_counts.index:
        english_labels.append('Non-English')
        english_values.append(english_counts[False])
    if True in english_counts.index:
        english_labels.append('English')
        english_values.append(english_counts[True])
    
    if english_values:
        sns.barplot(x=english_labels, y=english_values, palette="coolwarm")
        plt.title('Full Text Language Distribution', fontsize=14, fontweight='bold')
        plt.ylabel('Count')
    else:
        plt.text(0.5, 0.5, 'No language data', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title('Full Text Language Distribution', fontsize=14, fontweight='bold')
    
    plt.subplot(2, 2, 4)
    promising_counts = df['is_recent_promising'].value_counts()
    promising_labels = []
    promising_values = []
    if False in promising_counts.index:
        promising_labels.append('Not Promising')
        promising_values.append(promising_counts[False])
    if True in promising_counts.index:
        promising_labels.append('Recent & Promising')
        promising_values.append(promising_counts[True])
    
    if promising_values:
        sns.barplot(x=promising_labels, y=promising_values, palette="plasma")
        plt.title('Recent Promising Papers', fontsize=14, fontweight='bold')
        plt.ylabel('Count')
    else:
        plt.text(0.5, 0.5, 'No promising data', ha='center', va='center', transform=plt.gca().transAxes)
        plt.title('Recent Promising Papers', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/publication_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # Interactive timeline
    year_data = df[df['publication_year'] > 0].copy()
    if len(year_data) > 0:
        fig = px.histogram(year_data, x='publication_year', 
                          color='final_priority',
                          title='Publication Timeline by Priority',
                          labels={'publication_year': 'Publication Year', 'count': 'Number of Papers'})
        fig.update_layout(bargap=0.1)
        fig.write_html(f'{output_dir}/publication_timeline_interactive.html')
    else:
        # Create empty plot with message
        fig = go.Figure()
        fig.add_annotation(text="No valid publication year data available", 
                          xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        fig.update_layout(title='Publication Timeline by Priority')
        fig.write_html(f'{output_dir}/publication_timeline_interactive.html')

def plot_technical_scope_analysis(df, output_dir):
    """Analyze technical scope coverage"""
    tech_cols = ['addresses_llm_data_collection', 'addresses_text_corpus_creation', 
                'addresses_web_scraping_nlp', 'addresses_multilingual_compilation']
    
    # Calculate technical scope coverage
    tech_data = df[tech_cols].sum().sort_values(ascending=True)
    
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 1, 1)
    colors = sns.color_palette("rocket", len(tech_data))
    bars = plt.barh(range(len(tech_data)), tech_data.values, color=colors)
    plt.yticks(range(len(tech_data)), [col.replace('addresses_', '').replace('_', ' ').title() 
                                      for col in tech_data.index])
    plt.title('Technical Scope Coverage', fontsize=16, fontweight='bold')
    plt.xlabel('Number of Papers')
    
    # Add value labels on bars
    for i, bar in enumerate(bars):
        plt.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, 
                str(int(tech_data.values[i])), va='center')
    
    plt.subplot(2, 1, 2)
    # Technical scope heatmap by priority
    tech_priority = df.groupby('final_priority')[tech_cols].mean()
    sns.heatmap(tech_priority.T, annot=True, cmap='YlOrRd', fmt='.2f', cbar_kws={'label': 'Proportion'})
    plt.title('Technical Scope by Priority Level', fontsize=14, fontweight='bold')
    plt.ylabel('Technical Areas')
    plt.xlabel('Priority Level')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/technical_scope_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # Interactive sunburst chart
    tech_summary = []
    for idx, row in df.iterrows():
        for col in tech_cols:
            if row[col]:
                tech_summary.append({
                    'area': col.replace('addresses_', '').replace('_', ' ').title(),
                    'priority': row['final_priority'],
                    'value': 1
                })
    
    if tech_summary:
        tech_df = pd.DataFrame(tech_summary)
        fig = px.sunburst(tech_df, path=['area', 'priority'], values='value',
                         title='Technical Scope Distribution by Priority')
        fig.write_html(f'{output_dir}/technical_scope_sunburst.html')

def plot_humanitarian_scores(df, output_dir):
    """Analyze humanitarian principle scores"""
    human_cols = ['humanity_score', 'impartiality_score', 'independence_score', 'neutrality_score']
    
    plt.figure(figsize=(15, 10))
    
    # Score distributions
    plt.subplot(2, 2, 1)
    df[human_cols].boxplot()
    plt.title('Humanitarian Scores Distribution', fontsize=14, fontweight='bold')
    plt.ylabel('Score')
    plt.xticks(rotation=45)
    
    # Correlation heatmap
    plt.subplot(2, 2, 2)
    corr_matrix = df[human_cols].corr()
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', center=0, 
                square=True, fmt='.2f')
    plt.title('Humanitarian Scores Correlation', fontsize=14, fontweight='bold')
    
    # Average scores by priority
    plt.subplot(2, 2, 3)
    priority_scores = df.groupby('final_priority')[human_cols].mean()
    priority_scores.plot(kind='bar', ax=plt.gca())
    plt.title('Average Humanitarian Scores by Priority', fontsize=14, fontweight='bold')
    plt.ylabel('Average Score')
    plt.xlabel('Priority Level')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.xticks(rotation=45)
    
    # Total humanitarian score
    plt.subplot(2, 2, 4)
    df['total_humanitarian_score'] = df[human_cols].sum(axis=1)
    sns.histplot(df['total_humanitarian_score'], kde=True, bins=20)
    plt.title('Total Humanitarian Score Distribution', fontsize=14, fontweight='bold')
    plt.xlabel('Total Score')
    plt.ylabel('Frequency')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/humanitarian_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # Interactive radar chart
    avg_scores = df[human_cols].mean()
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=avg_scores.values,
        theta=avg_scores.index,
        fill='toself',
        name='Average Scores'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, max(avg_scores.values) * 1.1]
            )),
        showlegend=True,
        title="Average Humanitarian Principle Scores"
    )
    
    fig.write_html(f'{output_dir}/humanitarian_radar.html')

def plot_methodology_contributions(df, output_dir):
    """Analyze methodology and ethical contributions"""
    method_cols = ['novel_methodology', 'systematic_evaluation', 'reproducible_implementation']
    ethical_cols = ['explicit_framework', 'empirical_bias_analysis', 'harm_mitigation_strategies', 
                   'policy_recommendations', 'acknowledges_tensions']
    
    plt.figure(figsize=(16, 12))
    
    # Methodology contributions
    plt.subplot(3, 2, 1)
    method_counts = df[method_cols].sum()
    sns.barplot(x=method_counts.index, y=method_counts.values, palette="viridis")
    plt.title('Methodology Contributions', fontsize=14, fontweight='bold')
    plt.ylabel('Count')
    plt.xticks(rotation=45, ha='right')
    
    # Ethical contributions
    plt.subplot(3, 2, 2)
    ethical_counts = df[ethical_cols].sum()
    sns.barplot(x=range(len(ethical_counts)), y=ethical_counts.values, palette="plasma")
    plt.title('Ethical Contributions', fontsize=14, fontweight='bold')
    plt.ylabel('Count')
    plt.xticks(range(len(ethical_counts)), 
               [col.replace('_', ' ').title() for col in ethical_counts.index], 
               rotation=45, ha='right')
    
    # Contribution scores by priority
    plt.subplot(3, 2, 3)
    df['method_score'] = df[method_cols].sum(axis=1)
    method_by_priority = df.groupby('final_priority')['method_score'].mean()
    sns.barplot(x=method_by_priority.index, y=method_by_priority.values, palette="coolwarm")
    plt.title('Average Methodology Score by Priority', fontsize=14, fontweight='bold')
    plt.ylabel('Average Score')
    plt.xticks(rotation=45)
    
    plt.subplot(3, 2, 4)
    df['ethical_score'] = df[ethical_cols].sum(axis=1)
    ethical_by_priority = df.groupby('final_priority')['ethical_score'].mean()
    sns.barplot(x=ethical_by_priority.index, y=ethical_by_priority.values, palette="coolwarm")
    plt.title('Average Ethical Score by Priority', fontsize=14, fontweight='bold')
    plt.ylabel('Average Score')
    plt.xticks(rotation=45)
    
    # Combined contribution analysis
    plt.subplot(3, 1, 3)
    df['total_contribution_score'] = df['method_score'] + df['ethical_score']
    sns.scatterplot(data=df, x='method_score', y='ethical_score', 
                   hue='final_priority', size='total_contribution_score',
                   sizes=(50, 200), alpha=0.7)
    plt.title('Methodology vs Ethical Contributions', fontsize=14, fontweight='bold')
    plt.xlabel('Methodology Score')
    plt.ylabel('Ethical Score')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/contributions_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # Interactive bubble chart
    fig = px.scatter(df, x='method_score', y='ethical_score', 
                    color='final_priority', size='total_contribution_score',
                    hover_data=['title'], 
                    title='Methodology vs Ethical Contributions (Interactive)')
    fig.write_html(f'{output_dir}/contributions_bubble.html')

def plot_comprehensive_dashboard(df, output_dir):
    """Create a comprehensive interactive dashboard"""
    fig = make_subplots(
        rows=3, cols=2,
        specs=[[{"type": "pie"}, {"type": "bar"}],
               [{"type": "scatter"}, {"type": "heatmap"}],
               [{"type": "bar"}, {"type": "histogram"}]],
        subplot_titles=('Priority Distribution', 'Publications by Year',
                       'Methodology vs Ethics', 'Technical Coverage Heatmap',
                       'Top Venues', 'Humanitarian Score Distribution'),
        vertical_spacing=0.12
    )
    
    # Priority pie chart
    priority_counts = df['final_priority'].value_counts()
    fig.add_trace(go.Pie(labels=priority_counts.index, values=priority_counts.values,
                        name="Priority"), row=1, col=1)
    
    # Publications by year
    year_counts = df[df['publication_year'] > 0]['publication_year'].value_counts().sort_index()
    if len(year_counts) > 0:
        fig.add_trace(go.Bar(x=year_counts.index, y=year_counts.values,
                            name="Publications", 
                            marker=dict(color='lightblue')), row=1, col=2)
    
    # Methodology vs Ethics scatter
    fig.add_trace(go.Scatter(x=df['method_score'], y=df['ethical_score'],
                           mode='markers', 
                           marker=dict(size=8, opacity=0.6),
                           name="Papers"), row=2, col=1)
    
    # Technical coverage heatmap
    tech_cols = ['addresses_llm_data_collection', 'addresses_text_corpus_creation', 
                'addresses_web_scraping_nlp', 'addresses_multilingual_compilation']
    tech_priority = df.groupby('final_priority')[tech_cols].mean()
    
    fig.add_trace(go.Heatmap(z=tech_priority.values, 
                           x=tech_priority.columns,
                           y=tech_priority.index,
                           colorscale='Viridis'), row=2, col=2)
    
    # Top venues (handle empty venue names)
    top_venues = df[df['venue_name'].str.len() > 0]['venue_name'].value_counts().head(10)
    if len(top_venues) > 0:
        fig.add_trace(go.Bar(x=top_venues.values, y=top_venues.index,
                            orientation='h', name="Venues",
                            marker=dict(color='lightcoral')), row=3, col=1)
    
    # Humanitarian scores
    human_cols = ['humanity_score', 'impartiality_score', 'independence_score', 'neutrality_score']
    df['total_humanitarian'] = df[human_cols].sum(axis=1)
    fig.add_trace(go.Histogram(x=df['total_humanitarian'], nbinsx=20,
                              name="Humanitarian Scores"), row=3, col=2)
    
    fig.update_layout(height=1200, showlegend=False, 
                     title_text="Research Paper Screening Comprehensive Dashboard")
    fig.write_html(f'{output_dir}/comprehensive_dashboard.html')

def generate_summary_stats(df, output_dir):
    """Generate summary statistics"""
    # Handle potential missing or invalid data
    valid_years = df[df['publication_year'] > 0]
    year_range = f"{valid_years['publication_year'].min()} - {valid_years['publication_year'].max()}" if len(valid_years) > 0 else "No valid years"
    
    summary = {
        'total_papers': len(df),
        'priority_distribution': df['final_priority'].value_counts().to_dict(),
        'year_range': year_range,
        'top_tier_percentage': (df['is_top_tier_venue'].sum() / len(df) * 100) if len(df) > 0 else 0,
        'english_percentage': (df['full_text_english'].sum() / len(df) * 100) if len(df) > 0 else 0,
        'recent_promising_percentage': (df['is_recent_promising'].sum() / len(df) * 100) if len(df) > 0 else 0,
        'avg_humanitarian_scores': df[['humanity_score', 'impartiality_score', 
                                      'independence_score', 'neutrality_score']].mean().to_dict(),
        'technical_coverage': df[['addresses_llm_data_collection', 'addresses_text_corpus_creation', 
                                 'addresses_web_scraping_nlp', 'addresses_multilingual_compilation']].sum().to_dict()
    }
    
    with open(f'{output_dir}/summary_statistics.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Create a summary report
    report = f"""
# Research Paper Screening Analysis Summary

## Dataset Overview
- **Total Papers**: {summary['total_papers']:,}
- **Year Range**: {summary['year_range']}
- **Top Tier Venues**: {summary['top_tier_percentage']:.1f}%
- **English Full Text**: {summary['english_percentage']:.1f}%
- **Recent & Promising**: {summary['recent_promising_percentage']:.1f}%

## Priority Distribution
"""
    for priority, count in summary['priority_distribution'].items():
        percentage = (count / summary['total_papers']) * 100 if summary['total_papers'] > 0 else 0
        report += f"- **{priority}**: {count:,} papers ({percentage:.1f}%)\n"
    
    report += "\n## Technical Scope Coverage\n"
    for tech, count in summary['technical_coverage'].items():
        percentage = (count / summary['total_papers']) * 100 if summary['total_papers'] > 0 else 0
        tech_clean = tech.replace('addresses_', '').replace('_', ' ').title()
        report += f"- **{tech_clean}**: {count:,} papers ({percentage:.1f}%)\n"
    
    report += "\n## Average Humanitarian Principle Scores\n"
    for principle, score in summary['avg_humanitarian_scores'].items():
        if pd.notna(score):  # Check if score is not NaN
            principle_clean = principle.replace('_score', '').title()
            report += f"- **{principle_clean}**: {score:.2f}\n"
    
    with open(f'{output_dir}/analysis_report.md', 'w') as f:
        f.write(report)
    
    print("Summary Statistics:")
    print(f"Total papers analyzed: {summary['total_papers']:,}")
    print(f"Priority distribution: {summary['priority_distribution']}")
    print("Analysis complete! Check the plots directory for visualizations.")

def main():
    # Configuration
    input_file = "output/screening_results_20250811_100939.jsonl"
    output_dir = "plots/openai_analysis"
    
    # Create output directory
    create_output_dir(output_dir)
    
    # Load and process data
    print("Loading data...")
    raw_data = load_data(input_file)
    df = flatten_screening_data(raw_data)
    
    if df.empty:
        print("No data found or unable to parse the file.")
        return
    
    print(f"Loaded {len(df)} papers for analysis.")
    
    # Add derived columns
    method_cols = ['novel_methodology', 'systematic_evaluation', 'reproducible_implementation']
    ethical_cols = ['explicit_framework', 'empirical_bias_analysis', 'harm_mitigation_strategies', 
                   'policy_recommendations', 'acknowledges_tensions']
    human_cols = ['humanity_score', 'impartiality_score', 'independence_score', 'neutrality_score']
    
    df['method_score'] = df[method_cols].sum(axis=1)
    df['ethical_score'] = df[ethical_cols].sum(axis=1)
    df['total_humanitarian_score'] = df[human_cols].sum(axis=1)
    
    # Generate all plots
    print("Creating visualizations...")
    
    plot_priority_distribution(df, output_dir)
    print("✓ Priority distribution plots created")
    
    plot_publication_analysis(df, output_dir)
    print("✓ Publication analysis plots created")
    
    plot_technical_scope_analysis(df, output_dir)
    print("✓ Technical scope analysis plots created")
    
    plot_humanitarian_scores(df, output_dir)
    print("✓ Humanitarian scores analysis plots created")
    
    plot_methodology_contributions(df, output_dir)
    print("✓ Methodology and contributions analysis plots created")
    
    plot_comprehensive_dashboard(df, output_dir)
    print("✓ Comprehensive dashboard created")
    
    generate_summary_stats(df, output_dir)
    print("✓ Summary statistics and report generated")
    
    print(f"\nAll plots and analysis saved to: {output_dir}/")
    print("Open the HTML files in your browser for interactive visualizations!")

if __name__ == "__main__":
    main()