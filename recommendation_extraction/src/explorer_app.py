import streamlit as st
import pandas as pd
import sys
import os

# --- Page Configuration ---
# Set the page configuration for a wider layout and a title
st.set_page_config(
    page_title="Trade-Off Recommendation Explorer",
    layout="wide",
    initial_sidebar_state="expanded",
)

@st.cache_data  # Cache the data to improve performance
def load_data():
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        # Check if the file exists
        if os.path.exists(file_path):
            try:
                # Read the CSV file into a pandas DataFrame
                df = pd.read_csv(file_path)
            except Exception as e:
                st.error(f"Error reading the file: {e}")
        else:
            st.error(f"Error: File not found at '{file_path}'")
    else:
        st.warning("Please provide the path to a tradeoff recomandation CSV file as a command-line argument.")
        st.info("Example usage: `streamlit run app.py -- <path_to_your_file.csv>`")

    df['stages'] = df['stages'].apply(eval)
    df['harms'] = df['harms'].apply(eval)
    df_exploded = df.explode('stages').explode('harms')
    df_exploded = df_exploded.dropna(subset=['stages', 'harms'])
    return df, df_exploded


df, df_exploded = load_data()

# --- App Title and Description ---
st.title('Ethical Trade-offs Recommendation Explorer 🧭')
st.markdown("""
This interactive tool helps you explore recommendations for common AI ethics trade-offs.
Use the filters in the sidebar to select a **trade-off**, **development stage**, and **type of harm**
to see the relevant recommendations.
""")

# --- Sidebar Filters ---
st.sidebar.header('Filter Options')

# 1. Trade-Off Name Selector
trade_off_list = sorted(df['trade_off_name'].unique())
selected_trade_off = st.sidebar.selectbox(
    '1. Select a Trade-Off:',
    options=trade_off_list
)

# Filter the dataframe based on the selected trade-off first
filtered_df = df_exploded[df_exploded['trade_off_name'] == selected_trade_off]

# 2. Stage Selector
# Get unique stages available for the selected trade-off
available_stages = sorted(filtered_df['stages'].unique())
selected_stage = st.sidebar.selectbox(
    '2. Select a Development Stage:',
    options=['All'] + available_stages
)

# 3. Harm Selector
# Get unique harms available for the selected trade-off
available_harms = sorted(filtered_df['harms'].unique())
selected_harm = st.sidebar.selectbox(
    '3. Select a Type of Harm:',
    options=['All'] + available_harms
)

# --- Filtering Logic ---
# Apply stage and harm filters
if selected_stage != 'All':
    filtered_df = filtered_df[filtered_df['stages'] == selected_stage]

if selected_harm != 'All':
    filtered_df = filtered_df[filtered_df['harms'] == selected_harm]

# Drop duplicates to show each unique recommendation only once
final_recommendations = filtered_df.drop_duplicates(
    subset=['recommendation'])

# --- Display Results ---
st.markdown("---")
st.header(f"📜 Recommendations for '{selected_trade_off}'")

if final_recommendations.size > 0:
    score_cols = [
        'humanity_relevance_score',
        'neutrality_relevance_score',
        'independence_relevance_score',
        'impartiality_relevance_score'
    ]
    # Calculate the score by multiplying the values in the score columns
    final_recommendations['composite_score'] = final_recommendations[score_cols].prod(axis=1)

    # Sort the DataFrame by the new score in descending order (highest score first)
    final_recommendations = final_recommendations.sort_values(
        by='composite_score', ascending=False
    )

    st.info(f"Found **{len(final_recommendations)}** recommendation(s) matching your criteria.")
    # Iterate through the filtered, unique recommendations and display them
    for index, row in final_recommendations.iterrows():
        # Get the original full lists of stages and harms for context
        original_row = df[df['recommendation'] == row['recommendation']].iloc[0]

        with st.container(border=True):
            st.markdown(f"**Recommendation:**")
            st.success(row['recommendation'])

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f"**Trade-Off Description:**")
                st.write(f"{original_row['description']}")
            with col2:
                st.markdown(f"**Recommendation Details:**")
                st.write(f"{original_row['recommendation_desc']}")
            with col3:
                st.markdown(f"**Relevant Humanitarian Principles:**")
                for principle in ['humanity', 'neutrality', 'independence', 'impartiality']:
                    if original_row[f'{principle}_relevance_score'] > 2:
                        st.write(f"*{principle}*")
                        st.write(f"{original_row[f'{principle}_relevance_desc']}")
            with col4:
                st.markdown(f"**✅ Applicable Stages:**")
                st.write(f"`{original_row['stages']}`")
                st.markdown(f"**⚠️ Associated Harms:**")
                st.write(f"`{original_row['harms']}`")
                st.markdown(f"**Source**")
                st.write(f"{original_row['url']}")
else:
    st.warning("No recommendations found for the selected criteria. Please try a different combination.")

# Display the raw data in an expander
with st.expander("Show Raw Data"):
    st.dataframe(df)