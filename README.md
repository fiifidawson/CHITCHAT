# CHITCHAT
ArCHitectures for  Interpretable &amp;  Transparent  Continuous  Humanitarian  Alignment  in  chatbot  Technologies

## Paper Screening
1. Install: `pip install openai pypdf2 pydantic`
2. Add OpenAI API key with `export OPENAI_API_KEY="your-api-key-here"`
3. Run the script with `python3 paper_screening.py analysis_prompt.txt your_paper.pdf`

or with the new more sophisticated but pricier version:

* Single PDF URL: `python3 analyze_paper.py analysis_prompt.txt https://arxiv.org/pdf/2301.12345.pdf`

* Single arXiv ID: `python3 analyze_paper.py analysis_prompt.txt 2301.12345`

* Single local file: `python3 analyze_paper.py analysis_prompt.txt local_paper.pdf`

* Batch processing from file: `python analyze_paper.py batch analysis_prompt.txt paper_list.txt`