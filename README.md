# Intelligence Hub (US)

Executive-grade OSINT + Market Signals for Insights.

## Deploy (Render Free)
1) Push this repo to GitHub or GitLab.
2) Create new Web Service on Render → connect repo.
3) Autodetect "Python". Confirm build/start commands from `render.yaml` or copy:
   - Build: `pip install -r requirements.txt`
   - Start: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
4) Once live (https), copy the URL.

## Embed in Google Sites
Sites → Insert → Embed → paste your Render URL → Insert.
Set the frame to "Large" and enable borderless.

## Notes
- All data is real: Reuters/AP/NPR/CNBC RSS; SEC/FTC/FDA/FCC; TSA; Google Trends; Yahoo Finance.
- Caching via diskcache. Sentiment = VADER (fast). Entities = spaCy `en_core_web_sm`.
- Topic clustering uses TF-IDF + KMeans (lightweight). You can later switch to BERTopic.
