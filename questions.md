# which type of chunking are you using?
# Why instead of storing the chunked data inside the vector database is less useful than our current approach i.e in-memory LangGraph state.

# Vector Database will help when:- 
1. Search similar chunk
2.ask questions over old pdfs
3.Avoid reprocessing the same chunks


# Improving Performace
1.Cache chunk results:-
Store hash of chunk text + detection result. If same chunk appears again, do not call Gemini again.

2.Batch Gemini calls:-
Send multiple chunks in one Gemini request instead of one request per chunk.

3.Parallelize Gemini calls:-
Run confidential/abusive chunk checks concurrently with rate-limit control.

# Why you have used sqlite database?

# Whic evaluation metric it is using?
Ans:- Operational / LLM usage metrics

# 1. our current PII detection is regex based.Presidio would be stronger because it combines recognizers and NLP-based detection.

# 2. Detoxify Pre-trained model for abusive content testing
Detoxify is a pre-trained NLP model built on top of Transformer architectures for detecting:
Toxicity_threshold = 0.65

# Q: Suppose user wants to upload a file of size greater than 200MB, so how can we achieve this??
Ans:- 1.By allowing Streamlit to accept a 1GB upload
      2. Make the app process a 1 GB PDF safely
