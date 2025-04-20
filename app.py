import os
import time
import requests
import random
import google.generativeai as genai
import openai
from flask import Flask, render_template, request, jsonify, Response
from lxml import etree
from dotenv import load_dotenv
import base64
import io

load_dotenv()

app = Flask(__name__)

# Check if API keys are set
gemini_api_key = os.getenv("GEMINI_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
api_keys_configured = bool(gemini_api_key) and bool(openai_api_key)

# Configure Gemini API only if key is present
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)

# ArXiv API base URL
ARXIV_API_URL = "http://export.arxiv.org/api/query"

# Predefined topics (using arXiv categories)
# Find more categories at: https://arxiv.org/category_taxonomy
TOPICS = {
    # Computer Science
    "Artificial Intelligence": "cs.AI",
    "Computation and Language": "cs.CL",
    "Computer Vision": "cs.CV",
    "Machine Learning": "cs.LG",
    "Cryptography and Security": "cs.CR",
    "Data Structures and Algorithms": "cs.DS",
    "Networking and Internet Architecture": "cs.NI",
    "Software Engineering": "cs.SE",
    "Programming Languages": "cs.PL",
    
    # Mathematics
    "Algebraic Geometry": "math.AG",
    "Combinatorics": "math.CO",
    "Differential Geometry": "math.DG",
    "Number Theory": "math.NT",
    "Probability": "math.PR",
    "Statistics Theory": "math.ST",
    "Operator Algebras": "math.OA",
    "Optimization and Control": "math.OC",
    
    # Physics
    "Astrophysics": "astro-ph",
    "Condensed Matter": "cond-mat",
    "General Relativity and Quantum Cosmology": "gr-qc",
    "High Energy Physics - Experiment": "hep-ex",
    "High Energy Physics - Theory": "hep-th",
    "Nuclear Theory": "nucl-th",
    "Optics": "physics.optics",
    "Plasma Physics": "physics.plasm-ph",
    
    # Quantitative Biology
    "Biomolecules": "q-bio.BM",
    "Molecular Networks": "q-bio.MN",
    "Neurons and Cognition": "q-bio.NC",
    "Subcellular Processes": "q-bio.SC",
    "Tissues and Organs": "q-bio.TO",
    
    # Quantitative Finance
    "Computational Finance": "q-fin.CP",
    "General Finance": "q-fin.GN",
    "Portfolio Management": "q-fin.PM",
    "Risk Management": "q-fin.RM",
    "Statistical Finance": "q-fin.ST",
    "Trading and Market Microstructure": "q-fin.TR",
    
    # Statistics
    "Statistics Applications": "stat.AP",
    "Statistics Computation": "stat.CO",
    "Statistics Machine Learning": "stat.ML",
    "Statistics Methodology": "stat.ME",
    "Statistics Theory": "stat.TH",
    
    # Electrical Engineering and Systems Science
    "Audio and Speech Processing": "eess.AS",
    "Image and Video Processing": "eess.IV",
    "Signal Processing": "eess.SP",
    "Systems and Control": "eess.SY",
    
    # Economics
    "Econometrics": "econ.EM",
    "General Economics": "econ.GN",
    "Theoretical Economics": "econ.TH"
}

# Group categories by their main discipline for better organization
CATEGORY_GROUPS = {
    "Computer Science": ["cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.CR", "cs.DS", "cs.NI", "cs.SE", "cs.PL"],
    "Mathematics": ["math.AG", "math.CO", "math.DG", "math.NT", "math.PR", "math.ST", "math.OA", "math.OC"],
    "Physics": ["astro-ph", "cond-mat", "gr-qc", "hep-ex", "hep-th", "nucl-th", "physics.optics", "physics.plasm-ph"],
    "Quantitative Biology": ["q-bio.BM", "q-bio.MN", "q-bio.NC", "q-bio.SC", "q-bio.TO"],
    "Quantitative Finance": ["q-fin.CP", "q-fin.GN", "q-fin.PM", "q-fin.RM", "q-fin.ST", "q-fin.TR"],
    "Statistics": ["stat.AP", "stat.CO", "stat.ML", "stat.ME", "stat.TH"],
    "Electrical Engineering": ["eess.AS", "eess.IV", "eess.SP", "eess.SY"],
    "Economics": ["econ.EM", "econ.GN", "econ.TH"]
}

# Read the podcast prompt from file
PROMPT_FILE = "podcast_prompt.txt"
GENERATION_PROMPT = ""
try:
    with open(PROMPT_FILE, 'r') as f:
        GENERATION_PROMPT = f.read()
except FileNotFoundError:
    print(f"Error: Prompt file '{PROMPT_FILE}' not found. Using default prompt.")
    # Fallback prompt in case file is missing
    GENERATION_PROMPT = (
        "You are a podcast host explaining complex academic papers in a simple, engaging way. "
        "Analyze the provided PDF document, which is an academic paper. "
        "Generate a podcast script that explains the key findings, methodology, and significance of this paper in plain English. "
        "The script should be structured like a conversational podcast episode, approximately 30 minutes long when spoken. "
        "Include an introduction, main explanation sections, and a concluding summary. Make it accessible to a general audience interested in the topic, avoiding excessive jargon."
        "\n\nStart the podcast script now:"
    )

# --- Helper Functions ---

def fetch_arxiv_papers(categories, max_results=20):
    """Fetches papers from arXiv API based on categories."""
    if not categories:
        return []

    # Join multiple categories with OR
    query = " OR ".join([f"cat:{cat}" for cat in categories])

    params = {
        'search_query': query,
        'sortBy': 'submittedDate', # Get newer papers
        'sortOrder': 'descending',
        'start': random.randint(0, 50), # Get a random page for variety
        'max_results': max_results
    }

    try:
        # Add a delay as per arXiv API recommendations
        time.sleep(1) # Shorter delay for interactive use, increase if hitting limits

        response = requests.get(ARXIV_API_URL, params=params)
        response.raise_for_status() # Raise an exception for bad status codes

        root = etree.fromstring(response.content)
        # Atom namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        papers = []
        for entry in root.xpath('//atom:entry', namespaces=ns):
            paper_id_raw = entry.xpath('./atom:id/text()', namespaces=ns)[0]
            # Extract the core ID (e.g., 'http://arxiv.org/abs/2301.12345v1' -> '2301.12345')
            paper_id = paper_id_raw.split('/abs/')[-1].split('v')[0]
            title = entry.xpath('./atom:title/text()', namespaces=ns)[0].strip().replace('\n', ' ')
            # Extract abstract (summary)
            abstract = entry.xpath('./atom:summary/text()', namespaces=ns)[0].strip().replace('\n', ' ')

            # Find the PDF link
            pdf_link = None
            links = entry.xpath('./atom:link', namespaces=ns)
            for link in links:
                if link.xpath('@title', namespaces=ns) and link.xpath('@title', namespaces=ns)[0] == 'pdf':
                    pdf_link = link.xpath('@href', namespaces=ns)[0]
                    break

            if pdf_link:
                papers.append({'id': paper_id, 'title': title, 'pdf_link': pdf_link, 'abstract': abstract})

        return papers

    except requests.exceptions.RequestException as e:
        print(f"ArXiv API request failed: {e}")
        return []
    except etree.XMLSyntaxError as e:
        print(f"Failed to parse ArXiv response: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during ArXiv fetch: {e}")
        return []