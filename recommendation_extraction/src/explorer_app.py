import sys

import streamlit as st
import pandas as pd
import numpy as np
import ast
import os
from openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity

# --- CONFIGURATION ---
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


# --- 1. DATA LOADING ---
@st.cache_data
def load_data():
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                embedding_cols = ['objective_embedding', 'environment_embedding', 'beneficiary_embedding']
                for col in embedding_cols:
                    if col in df.columns and isinstance(df[col].iloc[0], str):
                        df[col] = df[col].apply(ast.literal_eval)

                if 'recommendations' in df.columns and isinstance(df['recommendations'].iloc[0], str):
                    df['recommendations'] = df['recommendations'].apply(ast.literal_eval)

                return df
            except Exception as e:
                st.error(f"Error reading the file: {e}")
                return pd.DataFrame()
        else:
            st.error(f"Error: File not found at '{file_path}'")
            return pd.DataFrame()
    else:
        st.warning("Please provide the path to a tradeoff recommendation CSV file as a command-line argument.")
        st.info("Example usage: `streamlit run app.py -- <path_to_your_file.csv>`")
        return pd.DataFrame()


# --- 2. EMBEDDINGS & SCORING ---
def get_embedding(text, model="text-embedding-3-small"):
    if not text: return np.zeros(1536)
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=model).data[0].embedding


def calculate_semantic_scores(df, u_obj, u_env, u_ben):
    def get_sim(col, user_vec):
        matrix = np.vstack(col.values)
        return cosine_similarity(matrix, np.array(user_vec).reshape(1, -1)).flatten()

    s_obj = np.maximum(get_sim(df['objective_embedding'], u_obj), 0)
    s_env = np.maximum(get_sim(df['environment_embedding'], u_env), 0)
    s_ben = np.maximum(get_sim(df['beneficiary_embedding'], u_ben), 0)
    return (s_obj * s_env * s_ben)


# --- 3. UI HELPERS ---
def principle_badge(score):
    if score == 3:
        return "🔴 **3 (High): Central Conflict**"
    elif score == 2:
        return "🟡 **2 (Medium): Secondary Factor**"
    elif score == 1:
        return "🔵 **1 (Low): Tangential**"
    return "N/A"


# --- 4. MAIN UI ---
def main():
    st.set_page_config(page_title="Humanitarian Ethical Tradeoff Explorer", layout="wide")
    st.title("🛡️ Humanitarian Ethical Tradeoff Explorer")
    st.markdown("Find precedents for ethical dilemmas in humanitarian technology design.")

    df = load_data()
    if df.empty: return

    # --- SIDEBAR INPUTS ---
    with st.sidebar:
        st.header("Search Parameters")
        input_obj = st.text_area("1. Your Objectives", placeholder="e.g., Biometric registration for aid distribution")
        input_env = st.text_area("2. Your Environment", placeholder="e.g., Conflict zone, limited connectivity")
        input_ben = st.text_area("3. Your Beneficiaries", placeholder="e.g., Internally displaced persons (IDPs)")

        top_n = st.slider("Number of top matches", min_value=1, max_value=100, value=30)
        search_btn = st.button("Search Precedents", type="primary")

        st.divider()
        st.header("Export Results")
        export_placeholder = st.empty()  # Placeholder for the download button

    if search_btn:
        if input_obj and input_env and input_ben:
            with st.spinner("Analyzing semantic closeness..."):
                u_obj_emb = get_embedding(input_obj)
                u_env_emb = get_embedding(input_env)
                u_ben_emb = get_embedding(input_ben)

                df['semantic_score'] = calculate_semantic_scores(df, u_obj_emb, u_env_emb, u_ben_emb)
                results = df.nlargest(top_n, 'semantic_score').copy()

            # --- RENDER DOWNLOAD BUTTON ---
            # Remove embedding columns before export to keep CSV clean
            export_df = results.drop(
                columns=['objective_embedding', 'environment_embedding', 'beneficiary_embedding', 'semantic_score'],
                errors='ignore')
            csv = export_df.to_csv(index=False).encode('utf-8')

            export_placeholder.download_button(
                label="📥 Download Top Matches as CSV",
                data=csv,
                file_name=f"humanitarian_tradeoffs_top_{top_n}.csv",
                mime="text/csv",
            )

            st.subheader(f"Found {len(results)} Relevant Tradeoffs")

            for i, (idx, row) in enumerate(results.iterrows()):
                with st.container(border=True):
                    # --- HEADER: Tradeoff & SOURCE PAPER ---
                    st.header(f"{i + 1}. Tradeoff: {row.get('name', 'Unnamed Tradeoff')}")
                    st.markdown(f"📖 **Source Paper:** *{row.get('title')}*")
                    st.caption(f"**Authors:** {row.get('authors')} | **Year:** {row.get('year')}")

                    st.markdown("---")

                    # --- ORIGINAL SYSTEM CONTEXT ---
                    st.markdown("#### 🔍 Original System Context")
                    cx1, cx2, cx3 = st.columns(3)
                    cx1.info(f"**Objective:**\n{row.get('objective', 'N/A')}")
                    cx2.info(f"**Environment:**\n{row.get('environment', 'N/A')}")
                    cx3.info(f"**Beneficiary:**\n{row.get('beneficiary', 'N/A')}")

                    # --- THE DILEMMA & HARMS ---
                    st.markdown("---")
                    c_desc, c_harms = st.columns([2, 1])
                    with c_desc:
                        st.markdown(f"#### ⚖️ The Dilemma\n{row.get('description', 'No description.')}")
                    with c_harms:
                        st.error(f"⚠️ **Targeted Harms & Risks**\n\n{row.get('harms', 'Unspecified risks.')}")

                    # --- PRINCIPLE RELEVANCE ---
                    st.markdown("#### Humanitarian Principle Relevance")
                    p1, p2, p3, p4 = st.columns(4)
                    p1.markdown(f"**Humanity**\n{principle_badge(row.get('humanity_relevance_score'))}")
                    p2.markdown(f"**Neutrality**\n{principle_badge(row.get('neutrality_relevance_score'))}")
                    p3.markdown(f"**Independence**\n{principle_badge(row.get('independence_relevance_score'))}")
                    p4.markdown(f"**Impartiality**\n{principle_badge(row.get('impartiality_relevance_score'))}")

                    # --- RECOMMENDATIONS ---
                    st.markdown("---")
                    recs = row.get('recommendations', [])
                    if recs:
                        st.markdown("#### ✅ Actionable Recommendations")
                        try:
                            sorted_recs = sorted(recs, key=lambda x: x.get('rating', {}).get('final_score', 0),
                                                 reverse=True)
                        except:
                            sorted_recs = recs

                        for r in sorted_recs:
                            with st.container():
                                st.markdown(f"**{r.get('name')}**")
                                st.write(r.get('description', ''))
                                stages = r.get('stages', [])
                                if stages:
                                    st.caption(
                                        f"**Applicable Stages:** {', '.join(stages) if isinstance(stages, list) else stages}")
                                st.markdown(" ")

                    if 'url' in row and pd.notna(row['url']):
                        st.link_button("📄 Read Full Paper", row['url'])

        else:
            st.warning("Please provide information for all three search fields.")


if __name__ == "__main__":
    main()