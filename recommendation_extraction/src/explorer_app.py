import streamlit as st
import pandas as pd
import sys
import os
from itertools import combinations
from collections import Counter

# --- Page Configuration ---
st.set_page_config(
    page_title="Trade-Off Recommendation Explorer",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Constants for Stage Sorting ---
# Define a logical order for known AI development stages to ensure the slider feels linear
# This helps map the "linear process" request to standard AI lifecycles
STAGE_ORDER_PRIORITY = [
    "Business Understanding", "Problem Definition",
    "Design", "Data Collection", "Data Preparation", "Preprocessing",
    "Model Development", "Modelling", "Training",
    "Evaluation", "Testing", "Validation",
    "Deployment", "Operation", "Monitoring", "Maintenance",
    "Retirement"
]


@st.cache_data
def load_data():
    df = None
    # logic to load file from command line or default for testing
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
            except Exception as e:
                st.error(f"Error reading the file: {e}")
                return pd.DataFrame(), pd.DataFrame()
        else:
            st.error(f"Error: File not found at '{file_path}'")
            return pd.DataFrame(), pd.DataFrame()
    else:
        st.warning("Please provide the path to a tradeoff recommendation CSV file as a command-line argument.")
        st.info("Example usage: `streamlit run app.py -- <path_to_your_file.csv>`")
        return pd.DataFrame(), pd.DataFrame()

    # --- Data Preprocessing ---
    # Convert string representations of lists to actual lists
    try:
        # Safe evaluation of columns containing lists
        cols_to_eval = ['stages', 'harms', 'conflicted_ethical_obligation']
        for col in cols_to_eval:
            if col in df.columns:
                # Handle potential NaN values by converting them to empty string lists for safety before eval
                df[col] = df[col].fillna("[]").apply(lambda x: eval(x) if isinstance(x, str) else x)

        # Explode stages and harms for granular filtering
        # Note: We do NOT explode conflicted_ethical_obligation, as we need to check if the *list* contains both items
        df_exploded = df.explode('stages').explode('harms')

        # Drop rows where essential data is missing
        df_exploded = df_exploded.dropna(subset=['stages', 'harms', 'conflicted_ethical_obligation'])

        return df, df_exploded

    except Exception as e:
        st.error(f"Error processing data structure: {e}")
        return pd.DataFrame(), pd.DataFrame()


df, df_exploded = load_data()

# Stop execution if data didn't load
if df.empty:
    st.stop()

# --- Conflict Frequency Analysis ---
# Calculate which pairs appear together most often to help the user choose
all_pairs = []
for oblig_list in df['conflicted_ethical_obligation']:
    # Ensure we only count unique items per row to avoid self-pairing if data is dirty
    unique_obligs = sorted(list(set(oblig_list)))
    if len(unique_obligs) >= 2:
        # Generate all possible pairs of 2 from the list
        pairs = list(combinations(unique_obligs, 2))
        all_pairs.extend(pairs)

pair_counts = Counter(all_pairs)

# Create a DataFrame for the visualization
if pair_counts:
    conflict_stats_df = pd.DataFrame(pair_counts.items(), columns=['Pair', 'Count'])
    conflict_stats_df[['Obligation A', 'Obligation B']] = pd.DataFrame(conflict_stats_df['Pair'].tolist(),
                                                                       index=conflict_stats_df.index)
    conflict_stats_df = conflict_stats_df[['Obligation A', 'Obligation B', 'Count']]
    conflict_stats_df = conflict_stats_df.sort_values(by='Count', ascending=False).reset_index(drop=True)
else:
    conflict_stats_df = pd.DataFrame(columns=['Obligation A', 'Obligation B', 'Count'])

# --- App Title and Description ---
st.title('Ethical Trade-offs Recommendation Explorer 🧭')
st.markdown("""
This interactive tool helps you explore recommendations for AI ethics trade-offs. 
**Select two conflicting ethical obligations** below to see recommendations relevant to that specific tension.
""")

# --- Sidebar Filters ---
st.sidebar.header('Define the Conflict')

# NEW: Top Conflicts Explorer
with st.sidebar.expander("📊 View Most Common Conflicts", expanded=False):
    st.markdown("These pairs appear most frequently in the dataset:")
    st.dataframe(
        conflict_stats_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Count": st.column_config.ProgressColumn(
                "Freq",
                help="Number of recommendations for this pair",
                format="%d",
                min_value=0,
                max_value=int(conflict_stats_df['Count'].max()) if not conflict_stats_df.empty else 10,
            ),
        }
    )

# 1. Ethical Obligations Selectors
# Flatten the list of all obligations to get unique values for the dropdowns
all_obligations = sorted(list(set([item for sublist in df['conflicted_ethical_obligation'] for item in sublist])))

col_sidebar_1, col_sidebar_2 = st.sidebar.columns(2)

with col_sidebar_1:
    obligation_a = st.selectbox(
        '1. Obligation A:',
        options=all_obligations,
        index=0 if len(all_obligations) > 0 else None
    )

with col_sidebar_2:
    # Default the second box to the second item if available, to encourage different selections
    default_index_b = 1 if len(all_obligations) > 1 else 0
    obligation_b = st.selectbox(
        '2. Obligation B:',
        options=all_obligations,
        index=default_index_b
    )


# --- Primary Filtering Logic (The Intersection) ---
# We filter for rows where the 'conflicted_ethical_obligation' list contains BOTH A and B
def has_both_obligations(row_obligations, ob_a, ob_b):
    return (ob_a in row_obligations) and (ob_b in row_obligations)


# Apply the filter
filtered_df = df_exploded[df_exploded['conflicted_ethical_obligation'].apply(
    lambda x: has_both_obligations(x, obligation_a, obligation_b)
)]

# --- Secondary Filters (Stage & Harm) ---
st.sidebar.header('Filter Context')

# 2. Stage Selector (SLIDER Implementation)
# Get available stages
raw_stages = filtered_df['stages'].unique().tolist() if not filtered_df.empty else []


# Sort logic: Priority list -> Alphabetical for others
def stage_sort_key(stage_name):
    # Case-insensitive matching attempt
    upper_stage = stage_name.upper()
    for i, priority_stage in enumerate(STAGE_ORDER_PRIORITY):
        if priority_stage.upper() in upper_stage:
            return i
    return len(STAGE_ORDER_PRIORITY) + 1  # Put unknown stages at the end


# Sort the stages based on the logical lifecycle order
available_stages = sorted(raw_stages, key=lambda x: (stage_sort_key(x), x))

# Use a select_slider for the "Linear Process" feel
if available_stages:
    selected_stage = st.sidebar.select_slider(
        '3. Development Process Stage:',
        options=['All'] + available_stages,
        value='All',
        help="Slide to filter recommendations by specific steps in the AI lifecycle."
    )
else:
    selected_stage = 'All'
    st.sidebar.write("No stages available for this selection.")

# 3. Harm Selector
available_harms = sorted(filtered_df['harms'].unique()) if not filtered_df.empty else []
selected_harm = st.sidebar.selectbox(
    '4. Select Type of Harm:',
    options=['All'] + available_harms
)

# Apply Stage and Harm filters
if selected_stage != 'All':
    filtered_df = filtered_df[filtered_df['stages'] == selected_stage]

if selected_harm != 'All':
    filtered_df = filtered_df[filtered_df['harms'] == selected_harm]

# Drop duplicates to show each unique recommendation only once
final_recommendations = filtered_df.drop_duplicates(subset=['recommendation'])

# --- Display Results ---
st.markdown("---")

# Dynamic Header based on selection
st.header(f"📜 Recommendations: {obligation_a} vs. {obligation_b}")

if final_recommendations.size > 0:

    # Check if 'recommendation_score' column exists before sorting
    if 'recommendation_score' in final_recommendations.columns:
        # Sort by recommendation_score as requested
        final_recommendations = final_recommendations.sort_values(by='recommendation_score', ascending=False)

    st.info(f"Found **{len(final_recommendations)}** recommendation(s) for this ethical conflict.")

    # Iterate through recommendations
    for index, row in final_recommendations.iterrows():
        original_data = df[df['recommendation'] == row['recommendation']].iloc[0]

        with st.container(border=True):
            st.subheader(row['recommendation'])

            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"**Conflict Context:**")
                st.write(f"{original_data.get('description', 'No description available')}")

                st.markdown(f"**Implementation Details:**")
                st.write(f"{original_data.get('recommendation_desc', '')}")

            with col2:
                st.markdown("**Properties:**")
                st.caption(f"**Source:** {original_data['title']}, {original_data['authors']}, {original_data['year']}")
                st.caption(f"**Stages:** {', '.join(original_data['stages'])}")
                st.caption(f"**Harms:** {', '.join(original_data['harms'])}")

                obs = original_data.get('conflicted_ethical_obligation', [])
                st.caption(f"**Obligations:** {', '.join(obs)}")

            # Expansion for Principles
            with st.expander("View Humanitarian Principles Relevance"):
                p_cols = st.columns(4)
                principles = ['humanity', 'neutrality', 'independence', 'impartiality']
                for idx, principle in enumerate(principles):
                    score_key = f'{principle}_relevance_score'
                    desc_key = f'{principle}_relevance_desc'

                    if score_key in original_data and original_data[score_key] > 0:
                        with p_cols[idx]:
                            st.markdown(f"**{principle.title()}**")
                            # Assuming relevance scores are still useful to display, even if not used for main sort
                            score = original_data[score_key]
                            st.progress(score / 5.0 if score <= 5 else 1.0)
                            st.caption(original_data.get(desc_key, ''))

            if 'url' in original_data and pd.notna(original_data['url']):
                st.link_button("Go to Source", original_data['url'])

else:
    st.warning(f"""
    No recommendations found specifically for the conflict between **{obligation_a}** and **{obligation_b}**. 

    This usually means this specific pair of obligations does not appear together in the 'conflicted_ethical_obligation' column for any row in the dataset.
    """)

# --- Raw Data Expander ---
with st.expander("Show Raw Data"):
    st.dataframe(df)