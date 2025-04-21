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

def download_pdf(pdf_url, paper_id):
    """Downloads a PDF from a URL and saves it temporarily."""
    try:
        response = requests.get(pdf_url, stream=True)
        response.raise_for_status()
        filepath = f"{paper_id}.pdf"
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Successfully downloaded {filepath}")
        return filepath
    except requests.exceptions.RequestException as e:
        print(f"Failed to download PDF from {pdf_url}: {e}")
        return None
    except Exception as e:
        print(f"An error occurred during PDF download: {e}")
        return None

def generate_podcast_script(pdf_path):
    """Sends PDF to Gemini API and generates a podcast script."""
    try:
        print(f"Uploading {pdf_path} to Gemini...")
        # Upload the file
        # Note: File API is in preview, usage might change.
        # Ensure your API key has File API access enabled.
        pdf_file = genai.upload_file(path=pdf_path)
        print(f"Uploaded file display name: {pdf_file.display_name}")

        # Wait for the file to be processed
        while pdf_file.state.name == "PROCESSING":
            print('.', end='', flush=True)
            time.sleep(5)
            pdf_file = genai.get_file(pdf_file.name)

        if pdf_file.state.name != "ACTIVE":
            print(f"\nFile processing failed: {pdf_file.state.name}")
            return f"Error: File processing failed ({pdf_file.state.name})"

        print("\nFile processed successfully. Generating script...")

        # Create the prompt - now read from file (or fallback)
        prompt = GENERATION_PROMPT # Use the prompt loaded from the file

        # Generate content using Gemini 1.5 Pro (or Flash for speed/cost)
        model = genai.GenerativeModel(model_name="gemini-2.5-pro-preview-03-25") # Or "gemini-1.5-flash-latest"
        response = model.generate_content([prompt, pdf_file], request_options={"timeout": 600}) # Increased timeout for potentially long generation

        # Clean up the uploaded file after use
        print(f"Deleting uploaded file: {pdf_file.name}")
        genai.delete_file(pdf_file.name)

        # Clean up the local file
        try:
            os.remove(pdf_path)
            print(f"Deleted local file: {pdf_path}")
        except OSError as e:
            print(f"Error deleting local file {pdf_path}: {e}")

        return response.text

    except Exception as e:
        print(f"An error occurred during Gemini processing: {e}")
        # Clean up local file even if Gemini fails
        if os.path.exists(pdf_path):
             try:
                 os.remove(pdf_path)
                 print(f"Deleted local file after error: {pdf_path}")
             except OSError as err:
                 print(f"Error deleting local file {pdf_path} after error: {err}")
        return f"Error generating podcast script: {e}"

def process_with_gpt4o_mini_tts(script):
    """Takes the Gemini-generated script and processes it with OpenAI TTS.
    Handles long scripts by breaking them into chunks if needed and processes in parallel."""
    try:
        # Configure OpenAI API
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables.")
        
        openai.api_key = openai_api_key
        
        # Check if script is too long (OpenAI TTS has a 4096 character limit)
        MAX_CHUNK_SIZE = 4000  # Reduced from 15000 to stay under OpenAI's 4096 limit
        
        if len(script) <= MAX_CHUNK_SIZE:
            # Process normally for shorter scripts
            print(f"Processing script with {len(script)} characters")
            response = openai.audio.speech.create(
                model="tts-1",  # or "tts-1-hd" for higher quality
                voice="alloy",  # alloy, echo, fable, onyx, nova, or shimmer
                input=script
            )
            return response.content
        else:
            # For longer scripts, we need to chunk and combine
            print(f"Script is {len(script)} characters - chunking into smaller segments")
            
            # Split at sentence boundaries to avoid cutting mid-sentence
            import re
            sentences = re.split(r'(?<=[.!?])\s+', script)
            chunks = []
            current_chunk = ""
            
            # Build chunks of appropriate size
            for sentence in sentences:
                # First check if single sentence is too long (rare but possible)
                if len(sentence) > MAX_CHUNK_SIZE:
                    print(f"Warning: Found extra long sentence ({len(sentence)} chars), splitting further")
                    # Split very long sentence at commas or other natural breaks
                    sub_sentences = re.split(r'(?<=[,;:])\s+', sentence)
                    for sub in sub_sentences:
                        if len(current_chunk) + len(sub) < MAX_CHUNK_SIZE:
                            current_chunk += sub + " "
                        else:
                            if current_chunk:  # Add the complete chunk
                                chunks.append(current_chunk.strip())
                            current_chunk = sub + " "  # Start a new chunk
                else:
                    # Normal sentence processing
                    if len(current_chunk) + len(sentence) < MAX_CHUNK_SIZE:
                        current_chunk += sentence + " "
                    else:
                        if current_chunk:  # Add the complete chunk
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + " "  # Start a new chunk
            
            # Add the last chunk if it's not empty
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            print(f"Split script into {len(chunks)} chunks for processing")
            for i, chunk in enumerate(chunks):
                print(f"Chunk {i+1} length: {len(chunk)} characters")
            
            # Process each chunk in parallel and combine the audio files
            import io
            import asyncio
            import concurrent.futures
            from pydub import AudioSegment
            
            # Define a function to process a single chunk and return (index, audio_content)
            def process_chunk(chunk_data):
                index, chunk_text = chunk_data
                print(f"Processing chunk {index+1}/{len(chunks)} - {len(chunk_text)} characters")
                try:
                    response = openai.audio.speech.create(
                        model="tts-1",
                        voice="alloy",
                        input=chunk_text
                    )
                    return (index, response.content)
                except Exception as chunk_error:
                    print(f"Error processing chunk {index+1}: {chunk_error}")
                    raise ValueError(f"Error processing audio chunk {index+1}: {str(chunk_error)}")
            
            # Process all chunks in parallel using a thread pool
            chunk_results = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(chunks))) as executor:
                # Submit all chunks to the executor
                future_to_index = {
                    executor.submit(process_chunk, (i, chunk)): i 
                    for i, chunk in enumerate(chunks)
                }
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_index):
                    index = future_to_index[future]
                    try:
                        result = future.result()
                        chunk_results.append(result)
                        print(f"Chunk {index+1}/{len(chunks)} completed")
                    except Exception as exc:
                        print(f"Chunk {index+1} generated an exception: {exc}")
                        raise
            
            # Sort results by index to maintain correct order
            chunk_results.sort(key=lambda x: x[0])
            
            # Combine audio chunks in the correct order
            combined_audio = None
            for _, audio_content in chunk_results:
                chunk_audio = AudioSegment.from_file(io.BytesIO(audio_content), format="mp3")
                if combined_audio is None:
                    combined_audio = chunk_audio
                else:
                    combined_audio += chunk_audio
            
            # Convert back to bytes
            buffer = io.BytesIO()
            combined_audio.export(buffer, format="mp3")
            return buffer.getvalue()
        
    except ImportError:
        print("Error: pydub library not installed. Install with 'pip install pydub'")
        return None
    except Exception as e:
        print(f"Error processing with OpenAI TTS: {e}")
        # Include more detailed error info
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def categorize_search_query(query):
    """Maps a search query to 3 main arXiv categories and 3 subcategories for each main category.
       Attempts to return a validated map, falling back to defaults if necessary.
    
    Args:
        query (str): The user's search query
        
    Returns:
        dict: A dictionary with categories, category_map, and debugging info
    """
    print(f"--- Starting categorization for query: '{query}' ---")
    default_map = {
        "Computer Science": ["cs.AI", "cs.NI", "cs.CR"], 
        "Mathematics": ["math.NT", "math.CO", "math.OC"], 
        "Physics": ["hep-th", "cond-mat", "physics.optics"]
    }
    
    # Return object with debugging info
    result = {
        "category_map": default_map,
        "ai_request": None,
        "ai_response": None
    }
    
    try:
        if not gemini_api_key:
            print("Error: Gemini API key not configured. Using default categories.")
            return result
        
        model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")
        
        main_category_names = list(CATEGORY_GROUPS.keys())
        all_subcategory_details = [f"{name} ({code})" for name, code in TOPICS.items()]
        
        # Construct the prompt for categorization
        prompt = f"""
You are an arXiv paper category expert helping classify a research query.

THE USER'S QUERY: "{query}"

Your task:
1. Based on the query, identify the top 3 most relevant main categories from this list:
{main_category_names}

2. For each selected main category, choose THREE most relevant subcategories.
Available subcategories and their codes: 
{all_subcategory_details}

3. Make sure the subcategories you select for each main category are actually in that main category.
Here are the main categories and their subcategories:
{CATEGORY_GROUPS}

RETURN YOUR ANSWER AS A JSON OBJECT ONLY with this exact format:
{{
  "Computer Science": ["cs.AI", "cs.NI", "cs.CR"],
  "Mathematics": ["math.NT", "math.CO", "math.OC"],
  "Physics": ["hep-th", "cond-mat", "physics.optics"]
}}

Where each key is one of the main categories, and each value is an array of THREE specific subcategory codes (e.g., "cs.AI") that belong to that main category.
"""
        
        # Store the prompt for debugging
        result["ai_request"] = prompt
        
        print("Sending categorization prompt to Gemini...")
        response = model.generate_content(prompt)
        print("Received response from Gemini")
        
        # Store the raw response for debugging
        result["ai_response"] = response.text
        
        try:
            # Parse the JSON response
            import json
            import re
            
            # Try to extract JSON from the response 
            # (sometimes the model includes it in backticks or with other text)
            response_text = response.text
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                category_map = json.loads(json_str)
                print(f"Parsed category map: {category_map}")
                
                # Validate the response format
                if not isinstance(category_map, dict) or len(category_map) != 3:
                    print(f"Error: Invalid format from AI. Expected dict with 3 entries, got: {type(category_map)} with {len(category_map)} entries")
                    result["category_map"] = default_map
                    return result
                
                # Validate the main categories
                main_cats_valid = all(main_cat in CATEGORY_GROUPS for main_cat in category_map.keys())
                if not main_cats_valid:
                    print(f"Error: Invalid main categories in AI response: {category_map.keys()}")
                    result["category_map"] = default_map
                    return result
                
                # Validate the subcategory codes
                validated_map = {}
                for main_cat, subcat_codes in category_map.items():
                    # Check if we got a list of subcategories
                    if not isinstance(subcat_codes, list):
                        print(f"Warning: Expected list of subcategory codes for {main_cat}, got {type(subcat_codes)}. Converting to list.")
                        # If AI returned a single string instead of a list, convert it
                        if isinstance(subcat_codes, str):
                            subcat_codes = [subcat_codes]
                        else:
                            # Use default subcategories for this main category
                            subcat_codes = default_map.get(main_cat, [])[:3]
                    
                    # Ensure we have exactly 3 subcategories
                    if len(subcat_codes) != 3:
                        print(f"Warning: Expected 3 subcategory codes for {main_cat}, got {len(subcat_codes)}. Adjusting list.")
                        # If too few, add default subcategories
                        if len(subcat_codes) < 3:
                            main_cat_defaults = default_map.get(main_cat, [])[:(3-len(subcat_codes))]
                            # Add defaults ensuring no duplicates
                            for default_code in main_cat_defaults:
                                if default_code not in subcat_codes:
                                    subcat_codes.append(default_code)
                        # If too many, truncate
                        subcat_codes = subcat_codes[:3]
                    
                    # Validate each subcategory code
                    valid_subcodes = []
                    for subcat_code in subcat_codes:
                        if subcat_code not in CATEGORY_GROUPS.get(main_cat, []):
                            print(f"Warning: Subcategory code '{subcat_code}' is not in main category '{main_cat}'. Fixing.")
                            # Find a replacement subcategory
                            available_codes = [code for code in CATEGORY_GROUPS.get(main_cat, []) if code not in valid_subcodes]
                            if available_codes:
                                replacement_code = available_codes[0]
                                valid_subcodes.append(replacement_code)
                            else:
                                print(f"Error: No more valid subcategories for {main_cat}")
                        else:
                            valid_subcodes.append(subcat_code)
                    
                    # Ensure we still have 3 subcategories after validation
                    while len(valid_subcodes) < 3:
                        available_codes = [code for code in CATEGORY_GROUPS.get(main_cat, []) if code not in valid_subcodes]
                        if available_codes:
                            valid_subcodes.append(available_codes[0])
                        else:
                            # Duplicate a code if necessary (unlikely scenario)
                            valid_subcodes.append(valid_subcodes[0])
                    
                    validated_map[main_cat] = valid_subcodes[:3]
                
                result["category_map"] = validated_map
                return result
            else:
                print(f"Error: Could not extract JSON from AI response: {response_text}")
                result["category_map"] = default_map
                return result
                
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse AI response as JSON: {e}. Raw response: {response.text}")
            result["category_map"] = default_map
            return result
        except Exception as e:
            print(f"Error during response parsing: {e}")
            result["category_map"] = default_map
            return result
            
    except Exception as e:
        print(f"Error during AI categorization: {e}")
        result["category_map"] = default_map
        return result

def search_and_rank_papers(query, category_map, papers_per_category=10):
    """Searches papers for main categories AND specific subcategories, deduplicates, ranks, filters,
       and groups results by main category.
    
    Args:
        query (str): The user's search query
        category_map (dict): Dictionary mapping 3 main categories to their chosen subcategory codes.
        papers_per_category (int): Number of papers to fetch PER FETCH operation (10 per subcategory).
        
    Returns:
        dict: Dictionary containing results grouped by main category and top overall results.
              Returns None if input is invalid.
    """
    if not category_map or len(category_map) != 3:
        print("Error: Invalid category_map provided to search_and_rank_papers.")
        return None

    # === DEBUG === Print the category map
    print("\n====== DEBUG: CATEGORY MAP ======")
    for main_cat, subcats in category_map.items():
        print(f"{main_cat}: {subcats}")
    print("=================================\n")

    all_fetched_papers = []
    # Store papers by category and subcategory to track their origin
    fetched_by_subcategory = {}  # To track the specific subcategory of each paper
    fetched_by_main_category_temp = {main_cat: [] for main_cat in category_map.keys()}
    main_categories_list = list(category_map.keys())
    
    print(f"Starting paper fetch for 3 main categories and their subcategories...")
    
    # --- Step 1: Fetch papers for each subcategory --- 
    for main_cat, subcategory_codes in category_map.items():
        print(f"Processing main category: {main_cat}")
        
        # Fetch papers for each specific subcategory
        for subcat_code in subcategory_codes:
            print(f"Fetching {papers_per_category} papers for subcategory: {subcat_code}")
            specific_papers = fetch_arxiv_papers([subcat_code], max_results=papers_per_category)
            
            # Tag each paper with its origin category
            for paper in specific_papers:
                paper['origin_category'] = main_cat
                paper['origin_subcategory'] = subcat_code
            
            all_fetched_papers.extend(specific_papers)
            fetched_by_main_category_temp[main_cat].extend(specific_papers)
            
            # Store by subcategory for more detailed tracking
            if subcat_code not in fetched_by_subcategory:
                fetched_by_subcategory[subcat_code] = []
            fetched_by_subcategory[subcat_code].extend(specific_papers)
            
            print(f" -> Found {len(specific_papers)} papers for {subcat_code}")
        
        # Fetch papers for the main category (using all its subcategory codes)
        main_cat_codes = CATEGORY_GROUPS.get(main_cat, [])
        if main_cat_codes:
            print(f"Fetching {papers_per_category} papers for main category: {main_cat} (using all codes)")
            main_cat_papers = fetch_arxiv_papers(main_cat_codes, max_results=papers_per_category)
            
            # Tag each paper with its origin category
            for paper in main_cat_papers:
                paper['origin_category'] = main_cat
                paper['origin_subcategory'] = 'general'  # General category fetch
            
            all_fetched_papers.extend(main_cat_papers)
            fetched_by_main_category_temp[main_cat].extend(main_cat_papers)
            print(f" -> Found {len(main_cat_papers)} papers for main category {main_cat}")
        else:
            print(f"Warning: No subcategory codes found defined for main category {main_cat}")

    # === DEBUG === Print all fetched papers by category
    print("\n====== DEBUG: FETCHED PAPERS BY CATEGORY ======")
    for main_cat, papers in fetched_by_main_category_temp.items():
        paper_ids = [p.get('id', 'unknown') for p in papers]
        print(f"{main_cat}: {len(papers)} papers - IDs: {paper_ids[:5]}{'...' if len(paper_ids) > 5 else ''}")
    print("==============================================\n")

    # --- Step 2: Deduplicate ALL fetched papers --- 
    unique_papers_dict = {}
    for paper in all_fetched_papers:
        # Ensure paper has an ID before adding
        if paper and paper.get('id'):
            # If paper already exists, keep the one with more specific subcategory origin
            if paper['id'] in unique_papers_dict:
                existing = unique_papers_dict[paper['id']]
                # Prefer papers from specific subcategories over general category fetches
                if existing.get('origin_subcategory') == 'general' and paper.get('origin_subcategory') != 'general':
                    unique_papers_dict[paper['id']] = paper
            else:
                unique_papers_dict[paper['id']] = paper
        else:
            print(f"Warning: Skipping paper with missing ID during deduplication: {paper}")

    all_unique_papers = list(unique_papers_dict.values())
    print(f"Total papers fetched (before dedupe): {len(all_fetched_papers)}, Unique papers: {len(all_unique_papers)}")
    
    # === DEBUG === Check unique papers by category
    unique_by_category = {main_cat: [] for main_cat in main_categories_list}
    for paper in all_unique_papers:
        cat = paper.get('origin_category')
        if cat in unique_by_category:
            unique_by_category[cat].append(paper)
    
    print("\n====== DEBUG: UNIQUE PAPERS BY CATEGORY ======")
    for main_cat, papers in unique_by_category.items():
        paper_ids = [p.get('id', 'unknown') for p in papers]
        print(f"{main_cat}: {len(papers)} unique papers - IDs: {paper_ids[:5]}{'...' if len(paper_ids) > 5 else ''}")
    print("===============================================\n")

    # --- Step 3: Rank unique papers --- 
    if not all_unique_papers:
        print("No unique papers found to rank.")
        return {"by_category": {main_cat: [] for main_cat in main_categories_list}, "top_results": []}
        
    ranked_papers = rank_papers_by_relevance(query, all_unique_papers)
    
    # === DEBUG === Check rankings
    print("\n====== DEBUG: RELEVANCE RANKING ======")
    ranked_papers.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    for i, paper in enumerate(ranked_papers[:10]):  # Just show top 10
        print(f"Rank {i+1}: ID {paper.get('id')}, Score {paper.get('relevance_score')}, Category {paper.get('origin_category')}")
    print("======================================\n")
    
    # --- Step 4: Filter ranked papers --- 
    filtered_papers = filter_papers_by_relevance(ranked_papers, query)
    print(f"Papers remaining after relevance filtering: {len(filtered_papers)}")
    
    # === DEBUG === Check filtered papers
    print("\n====== DEBUG: AFTER FILTERING ======")
    filtered_papers.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    print(f"Total filtered papers: {len(filtered_papers)}")
    for i, paper in enumerate(filtered_papers):
        print(f"  - Paper {i+1}: ID {paper.get('id')}, Score {paper.get('relevance_score')}, Origin Category: {paper.get('origin_category')}, Origin Subcategory: {paper.get('origin_subcategory')}")
    print("====================================\n")

    # --- Step 5: Re-organize filtered papers under MAIN categories --- 
    # Group by the origin_category tag we added during fetching
    filtered_by_main_category_final = {main_cat: [] for main_cat in main_categories_list}
    
    # === DEBUG === Track assignment of papers to categories
    assignment_counts = {main_cat: 0 for main_cat in main_categories_list}
    papers_without_category = []
    
    print("\n====== DEBUG: ATTEMPTING CATEGORY ASSIGNMENT (Step 5) ======")
    for paper in filtered_papers:
        main_cat = paper.get('origin_category')
        paper_id = paper.get('id', 'Unknown ID')
        print(f"  Processing Paper ID: {paper_id}, Origin Category Tag: '{main_cat}'") # LOG EACH PAPER'S TAG
        
        if main_cat and main_cat in filtered_by_main_category_final:
            # Add paper to its original category
            filtered_by_main_category_final[main_cat].append(paper)
            assignment_counts[main_cat] += 1
            print(f"    -> Assigned to '{main_cat}'") # LOG SUCCESSFUL ASSIGNMENT
        else:
            print(f"    -> Problem: Origin category '{main_cat}' is missing or invalid. Trying fallback...")
            # If no origin category or invalid category, try to infer from subcategory
            subcat = paper.get('origin_subcategory')
            if subcat and subcat != 'general':
                print(f"      Trying to infer from subcategory: '{subcat}'")
                # Try to find which main category this subcategory belongs to
                assigned = False
                for cat, subcats in CATEGORY_GROUPS.items():
                    if subcat in subcats and cat in filtered_by_main_category_final:
                        filtered_by_main_category_final[cat].append(paper)
                        assignment_counts[cat] += 1
                        assigned = True
                        print(f"        -> Assigned to '{cat}' via subcategory fallback")
                        break
                if not assigned:
                    print(f"        -> Fallback failed: Subcategory '{subcat}' didn't map to a valid main category.")
                    papers_without_category.append(paper)
            else:
                print(f"      -> Fallback failed: No valid subcategory ('{subcat}') to infer from.")
                papers_without_category.append(paper)
    print("=============================================================\n")
    
    # === DEBUG === Check assignment results (already added)
    print("\n====== DEBUG: CATEGORY ASSIGNMENT COUNTS ======")
    for cat, count in assignment_counts.items():
        print(f"{cat}: Assigned {count} papers")
    if papers_without_category:
        print(f"Papers without category assignment: {len(papers_without_category)}")
        for paper in papers_without_category:
            print(f"  - ID {paper.get('id')}, Origin: {paper.get('origin_category', 'None')}, Subcategory: {paper.get('origin_subcategory', 'None')}")
    print("=============================================\n")
    
    # === EMERGENCY FIX === If papers are missing categories, try harder to assign them
    if papers_without_category:
        print("Applying emergency fix for category assignment...")
        for paper in papers_without_category:
            # Get all main categories in our map
            main_cats = list(category_map.keys())
            if main_cats:
                # Just assign to first category as a fallback
                target_cat = main_cats[0]
                filtered_by_main_category_final[target_cat].append(paper)
                print(f"Assigned paper {paper.get('id')} to {target_cat} as emergency fallback")
    
    # Sort papers in each category by relevance score
    for main_cat in main_categories_list:
        filtered_by_main_category_final[main_cat].sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        print(f"Main category '{main_cat}' has {len(filtered_by_main_category_final[main_cat])} relevant papers assigned.")

    # --- Step 6: Determine Top Results (from all filtered papers) --- 
    # Sort all filtered papers by relevance score
    filtered_papers.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    top_results = filtered_papers[:10]
    print(f"Top results identified: {len(top_results)} papers")
    
    # === DEBUG === Check final output
    print("\n====== DEBUG: FINAL RESULT SUMMARY ======")
    print(f"Top results: {len(top_results)} papers")
    for main_cat, papers in filtered_by_main_category_final.items():
        print(f"{main_cat}: {len(papers)} papers")
    
    # Check for papers that are in top results but not in any category
    top_ids = {p.get('id') for p in top_results}
    category_ids = set()
    for main_cat, papers in filtered_by_main_category_final.items():
        category_ids.update({p.get('id') for p in papers})
    
    missing_from_categories = top_ids - category_ids
    if missing_from_categories:
        print(f"WARNING: Found {len(missing_from_categories)} papers that are in top results but not in any category!")
        for paper_id in missing_from_categories:
            paper = next((p for p in top_results if p.get('id') == paper_id), None)
            if paper:
                print(f"  - ID {paper_id}, Origin: {paper.get('origin_category', 'None')}, Subcategory: {paper.get('origin_subcategory', 'None')}")
    print("========================================\n")

    # --- Step 7: Return Results --- 
    return {
        "by_category": filtered_by_main_category_final, 
        "top_results": top_results
    }

def fetch_arxiv_papers_by_keyword(keyword, max_results=10):
    """Fetches papers from arXiv API based on a keyword search."""
    params = {
        'search_query': f'all:{keyword}',
        'sortBy': 'relevance',
        'sortOrder': 'descending',
        'max_results': max_results
    }
    
    try:
        # Add a delay as per arXiv API recommendations
        time.sleep(1)
        
        response = requests.get(ARXIV_API_URL, params=params)
        response.raise_for_status()
        
        root = etree.fromstring(response.content)
        # Atom namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        papers = []
        for entry in root.xpath('//atom:entry', namespaces=ns):
            paper_id_raw = entry.xpath('./atom:id/text()', namespaces=ns)[0]
            # Extract the core ID
            paper_id = paper_id_raw.split('/abs/')[-1].split('v')[0]
            title = entry.xpath('./atom:title/text()', namespaces=ns)[0].strip().replace('\n', ' ')
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
    except Exception as e:
        print(f"Error fetching papers by keyword: {e}")
        return []

def rank_papers_by_relevance(query, papers):
    """Ranks papers based on their relevance to the query."""
    try:
        # Configure Gemini API
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        
        print(f"Ranking {len(papers)} papers for relevance to query: {query}")
        
        # Create a ranking prompt
        ranking_prompt = f"""
        You are an AI research assistant helping to find relevant papers for a user's query.
        
        USER QUERY: {query}
        
        I will provide you with research paper titles and abstracts. For each paper,
        assign a relevance score from 0-100 based on how well it addresses the query.
        
        Papers with direct relevance to the query should receive high scores (70-100).
        Papers with some relevance should receive medium scores (40-70).
        Papers with minimal relevance should receive low scores (0-40).
        
        Provide the score for each paper and a brief one-sentence explanation.
        """
        
        # Build a combined papers text for the prompt
        papers_text = ""
        for i, paper in enumerate(papers):
            papers_text += f"\nPAPER {i+1}:\nTitle: {paper['title']}\nAbstract: {paper['abstract']}\n"
        
        # Complete model call with papers text included
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        full_prompt = ranking_prompt + papers_text
        
        # Add a closing instruction
        full_prompt += "\n\nFor each paper, respond with the paper number, score, and a brief explanation in this format:\nPAPER 1: score (e.g., 85) - explanation"
        
        response = model.generate_content(full_prompt)
        response_text = response.text
        
        # Parse the response
        import re
        paper_scores = []
        
        # Extract scores using regex
        pattern = r"PAPER (\d+):?\s*(\d+)\s*-\s*(.*?)(?=PAPER \d+:|$)"
        matches = re.findall(pattern, response_text, re.DOTALL)
        
        # Build a dictionary mapping paper index to score and explanation
        scores_dict = {}
        for match in matches:
            paper_index = int(match[0]) - 1  # Convert to 0-based index
            score = int(match[1])
            explanation = match[2].strip()
            scores_dict[paper_index] = {"score": score, "explanation": explanation}
        
        # Assign scores to papers, default to 0 if not found
        for i, paper in enumerate(papers):
            if i in scores_dict:
                paper["relevance_score"] = scores_dict[i]["score"]
                paper["relevance_explanation"] = scores_dict[i]["explanation"]
            else:
                paper["relevance_score"] = 0
                paper["relevance_explanation"] = "No explanation provided by AI"
        
        # Sort papers by score in descending order
        ranked_papers = sorted(papers, key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        # Create top results (all papers for now, will be filtered in frontend)
        return ranked_papers
        
    except Exception as e:
        print(f"Error in paper ranking: {e}")
        # Return unranked papers as fallback
        for paper in papers:
            paper["relevance_score"] = 50  # Default middle score
            paper["relevance_explanation"] = "Ranking unavailable"
        return papers

def filter_papers_by_relevance(papers, query):
    """
    Filters papers using Gemini 2.0 Flash to determine relevance.
    Returns only papers deemed relevant with explanations.
    """
    try:
        # Configure Gemini API
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables.")
        
        print(f"Filtering {len(papers)} papers for relevance to: {query}")
        filtered_papers = []
        
        # Process papers in batches to avoid very long prompts
        batch_size = 5
        for i in range(0, len(papers), batch_size):
            batch = papers[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1} with {len(batch)} papers")
            
            # Create a filtering prompt
            filter_prompt = f"""
            You are an AI research assistant helping to find truly relevant papers for a user's query.
            
            USER QUERY: {query}
            
            For each paper, determine if it is relevant to the query. If it is relevant, explain in 2 sentences why.
            If it is NOT relevant, simply respond with "no".
            
            Be strict about relevance - only papers that directly address aspects of the query should be considered relevant.
            """
            
            # Build the papers text for this batch
            papers_text = ""
            for j, paper in enumerate(batch):
                papers_text += f"\nPAPER {j+1}:\nTitle: {paper['title']}\nAbstract: {paper['abstract']}\n"
            
            # Call Gemini with the combined prompt
            model = genai.GenerativeModel(model_name="gemini-2.0-flash")
            full_prompt = filter_prompt + papers_text
            
            # Add specific formatting instructions
            full_prompt += "\n\nFor each paper, respond in this format:\nPAPER 1: [your 2-sentence explanation why it's relevant OR just 'no']"
            
            response = model.generate_content(full_prompt)
            response_text = response.text
            
            # Parse the response
            import re
            
            # Extract relevance judgments using regex
            pattern = r"PAPER (\d+):?\s*(.*?)(?=PAPER \d+:|$)"
            matches = re.findall(pattern, response_text, re.DOTALL)
            
            # Process each paper in the batch
            for match in matches:
                paper_index_in_batch = int(match[0]) - 1
                if paper_index_in_batch < len(batch):
                    explanation = match[1].strip()
                    
                    # Determine if paper is relevant
                    is_relevant = explanation.lower() != "no"
                    
                    # Add relevance info to the paper
                    paper = batch[paper_index_in_batch]
                    paper["is_relevant"] = is_relevant
                    paper["relevance_explanation"] = explanation if is_relevant else "Not relevant to the query"
                    
                    # Add to filtered list if relevant
                    if is_relevant:
                        filtered_papers.append(paper)
        
        print(f"Filtering complete: {len(filtered_papers)} out of {len(papers)} papers deemed relevant")
        return filtered_papers
        
    except Exception as e:
        print(f"Error in paper filtering: {e}")
        # Return all papers as fallback with a default relevance
        for paper in papers:
            paper["is_relevant"] = True
            paper["relevance_explanation"] = "Filtering unavailable due to error"
        return papers

# --- Flask Routes ---

@app.route('/')
def index():
    """Renders the main page with topic selection."""
    # Get the main category names from the CATEGORY_GROUPS dictionary keys
    main_categories = list(CATEGORY_GROUPS.keys())
    return render_template('index.html', topics=main_categories, api_keys_configured=api_keys_configured)

@app.route('/search_papers', methods=['POST'])
def search_papers():
    """Handles paper search requests based on main categories."""
    data = request.get_json()
    selected_main_topics = data.get('topics', [])
    print(f"Searching for main topics: {selected_main_topics}")

    if not selected_main_topics:
        return jsonify({'error': 'No topics selected'}), 400

    # Map selected main category names to their list of arXiv codes
    category_codes_to_search = []
    for main_topic in selected_main_topics:
        codes = CATEGORY_GROUPS.get(main_topic)
        if codes:
            category_codes_to_search.extend(codes)
        else:
            print(f"Warning: Could not find arXiv codes for main topic: {main_topic}")

    # Remove duplicates if a subcategory belongs to multiple selected main topics (unlikely but possible)
    category_codes_to_search = list(set(category_codes_to_search))

    if not category_codes_to_search:
        print("Error: No valid arXiv codes found for selected topics.")
        return jsonify({'error': 'Invalid topics selected or no codes found'}), 400

    print(f"Mapped main topics to arXiv codes: {category_codes_to_search}")
    papers = fetch_arxiv_papers(category_codes_to_search)

    if not papers:
         # Return empty list instead of error to allow frontend to handle 'no results'
         print("No papers found for the selected category codes.")
         return jsonify([])

    # Shuffle results for variety on refresh
    random.shuffle(papers)
    print(f"Found {len(papers)} papers for the selected main topics.")

    return jsonify(papers)

@app.route('/generate_plain_title', methods=['POST'])
def generate_plain_title():
    """Generates a plain English title using Gemini Flash."""
    data = request.get_json()
    original_title = data.get('title')
    abstract = data.get('abstract')

    if not original_title or not abstract:
        return jsonify({'error': 'Missing original title or abstract'}), 400

    try:
        # Use Gemini 1.5 Flash for faster, cheaper title generation
        model = genai.GenerativeModel(model_name="gemini-1.5-flash-latest")

        prompt = (
            f"You are an expert science communicator tasked with creating engaging titles for the public.\n"
            f"Based on the following academic paper's title and abstract, generate a short, catchy, and easy-to-understand 'plain English' title. "
            f"Focus on the core idea or key finding. Avoid jargon. Make it sound intriguing.\n\n"
            f"Original Title: {original_title}\n\n"
            f"Abstract: {abstract}\n\n"
            f"Generate ONLY the plain English title:"
        )

        # Lower timeout for faster title generation
        response = model.generate_content(prompt, request_options={"timeout": 60})

        plain_title = response.text.strip().replace('"', '') # Remove potential quotes
        return jsonify({'plain_title': plain_title})

    except Exception as e:
        print(f"An error occurred during plain title generation: {e}")
        # Return a default or error indicator title instead of failing the whole request
        return jsonify({'plain_title': "Could not generate title."})

@app.route('/generate_podcast', methods=['POST'])
def generate_podcast():
    """Generate podcast script from a PDF."""
    try:
        # Check if API keys are configured
        if not api_keys_configured:
            return jsonify({'error': 'API keys not configured. Please set your API keys first.'}), 400
            
        data = request.json
        paper_id = data.get('id')
        pdf_url = data.get('pdf_link')
        
        if not paper_id or not pdf_url:
            return jsonify({'error': 'Missing paper ID or PDF link'}), 400
        
        # Create temp_data directory if it doesn't exist
        os.makedirs('temp_data', exist_ok=True)
        
        # Download the PDF
        pdf_path = download_pdf(pdf_url, f"temp_data/{paper_id}")
        if not pdf_path:
            return jsonify({'error': 'Failed to download PDF'}), 500
            
        # Generate podcast script
        script = generate_podcast_script(pdf_path)
        
        # Store for audio generation
        temp_script_path = f"temp_data/{paper_id}_script.txt"
        with open(temp_script_path, 'w') as f:
            f.write(script)
            
        return jsonify({'script': script, 'paper_id': paper_id})
        
    except Exception as e:
        print(f"Error in generate_podcast: {e}")
        return jsonify({'error': f'Failed to generate podcast - {str(e)}'}), 500

@app.route('/audio/<paper_id>', methods=['GET'])
def get_audio(paper_id):
    """Streams the generated audio file."""
    print(f"Audio endpoint called for paper_id: {paper_id}")
    try:
        # Get the script from a previous generation
        script_data = request.args.get('script')
        if not script_data:
            print("Error: No script provided in request")
            return jsonify({'error': 'No script provided'}), 400
        
        print(f"Script length: {len(script_data)} characters. Processing with TTS...")
        
        # Process with OpenAI TTS
        audio_content = process_with_gpt4o_mini_tts(script_data)
        if not audio_content:
            print("Error: Failed to generate audio content")
            return jsonify({'error': 'Failed to generate audio - check server logs for details'}), 500
        
        print(f"Audio generated successfully. Content length: {len(audio_content)} bytes")
        
        # Return the audio as a streaming response
        return Response(
            io.BytesIO(audio_content),
            mimetype='audio/mpeg',
            headers={'Content-Disposition': f'attachment; filename={paper_id}.mp3'}
        )
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error serving audio: {e}")
        print(f"Traceback: {error_traceback}")
        
        # Provide more specific error messages
        error_message = str(e)
        if "API key" in error_message.lower():
            return jsonify({'error': 'Failed to generate audio - API key issue'}), 500
        elif "rate limit" in error_message.lower():
            return jsonify({'error': 'Failed to generate audio - rate limit exceeded'}), 429
        elif "content policy" in error_message.lower():
            return jsonify({'error': 'Failed to generate audio - content policy violation'}), 400
        else:
            return jsonify({'error': f'Failed to generate audio - {str(e)}'}), 500

@app.route('/check_api_keys', methods=['GET'])
def check_api_keys():
    """Check if API keys are configured."""
    return jsonify({
        'gemini_configured': bool(os.getenv("GEMINI_API_KEY")),
        'openai_configured': bool(os.getenv("OPENAI_API_KEY")),
        'all_configured': api_keys_configured
    })

@app.route('/save_api_keys', methods=['POST'])
def save_api_keys():
    """Save API keys to .env file."""
    try:
        data = request.json
        gemini_key = data.get('gemini_api_key')
        openai_key = data.get('openai_api_key')
        
        if not gemini_key or not openai_key:
            return jsonify({'success': False, 'error': 'Both API keys are required'}), 400
        
        # Read existing .env content if it exists
        env_content = ""
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                env_content = f.read()
        
        # Update or add Gemini API key
        if "GEMINI_API_KEY=" in env_content:
            env_content = '\n'.join([line if not line.startswith("GEMINI_API_KEY=") else f"GEMINI_API_KEY={gemini_key}" 
                                    for line in env_content.split('\n')])
        else:
            env_content += f"\nGEMINI_API_KEY={gemini_key}"
        
        # Update or add OpenAI API key
        if "OPENAI_API_KEY=" in env_content:
            env_content = '\n'.join([line if not line.startswith("OPENAI_API_KEY=") else f"OPENAI_API_KEY={openai_key}" 
                                    for line in env_content.split('\n')])
        else:
            env_content += f"\nOPENAI_API_KEY={openai_key}"
        
        # Write updated content to .env file
        with open('.env', 'w') as f:
            f.write(env_content.strip())
        
        # Update runtime environment variables
        os.environ["GEMINI_API_KEY"] = gemini_key
        os.environ["OPENAI_API_KEY"] = openai_key
        
        # Configure APIs with new keys
        genai.configure(api_key=gemini_key)
        openai.api_key = openai_key
        
        # Update the application state
        global api_keys_configured
        api_keys_configured = True
        
        return jsonify({'success': True, 'reload': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/advanced_search', methods=['POST'])
def advanced_search():
    """Handles advanced search queries based on natural language input."""
    data = request.get_json()
    query = data.get('query', '')
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    try:
        # First categorize the query to get relevant arXiv categories
        categorization_result = categorize_search_query(query)
        category_map = categorization_result["category_map"]
        
        # Get the main categories from the category map
        main_categories = list(category_map.keys())
        
        # Use the category map to search and rank papers
        search_results = search_and_rank_papers(query, category_map)
        
        # === DEBUG === Print the search_results structure *immediately* after return
        print("\n====== DEBUG: STRUCTURE FROM search_and_rank_papers ======")
        print(f"search_results keys: {list(search_results.keys())}")
        if "by_category" in search_results:
            print("Contents of search_results['by_category']:")
            for cat, papers in search_results["by_category"].items():
                print(f"  - {cat}: {len(papers)} papers (IDs: {[p.get('id') for p in papers[:3]]}...)")
        else:
            print("'by_category' key is MISSING in search_results")
        if "top_results" in search_results:
            print(f"Contents of search_results['top_results']: {len(search_results['top_results'])} papers")
            print(f"  - Top IDs: {[p.get('id') for p in search_results['top_results'][:5]]}...")
        else:
            print("'top_results' key is MISSING in search_results")
        print("============================================================\n")
        
        # Restructure the response to make it more explicit for the frontend
        response_data = {
            "categories": main_categories,
            "category_map": category_map,
            "resultsByCategory": {}, # Initialize as empty
            "top_results": search_results.get("top_results", []),
            "ai_request": categorization_result.get("ai_request"),
            "ai_response": categorization_result.get("ai_response")
        }
        
        # Extract papers by category from the nested structure
        if "by_category" in search_results and isinstance(search_results["by_category"], dict):
            response_data["resultsByCategory"] = search_results["by_category"]
            print("DEBUG: Successfully assigned search_results['by_category'] to response_data['resultsByCategory']")
        else:
            print("DEBUG: Failed to assign 'by_category' from search_results. It might be missing or not a dictionary.")

        # === DEBUG === Check the state *before* the emergency fix
        print("\n====== DEBUG: BEFORE EMERGENCY FIX ======")
        category_paper_count_before = sum(len(papers) for papers in response_data["resultsByCategory"].values())
        top_results_count_before = len(response_data["top_results"])
        print(f"Category paper count: {category_paper_count_before}")
        print(f"Top results count: {top_results_count_before}")
        for cat, papers in response_data["resultsByCategory"].items():
             print(f"  - {cat}: {len(papers)} papers")
        print("=======================================\n")

        # Emergency fix: If papers are in top results but none in categories, duplicate them
        if top_results_count_before > 0 and category_paper_count_before == 0:
            print("*** APPLYING EMERGENCY FIX: Duplicating top results to categories ***")
            # Ensure category keys exist in the dictionary
            for cat in main_categories:
                if cat not in response_data["resultsByCategory"]:
                    response_data["resultsByCategory"][cat] = []
                    print(f"  - Created empty list for category: {cat}")
            
            # Distribute top results among the categories based on their origin
            assigned_in_fix = 0
            for paper in response_data["top_results"]:
                category = paper.get("origin_category")
                print(f"  - Processing Top Paper ID: {paper.get('id')}, Origin Category: {category}")
                
                # Check if the origin category is valid and exists in our map
                if category and category in response_data["resultsByCategory"]:
                    response_data["resultsByCategory"][category].append(paper)
                    print(f"    - Assigned paper {paper.get('id')} to its origin category: {category}")
                    assigned_in_fix += 1
                else:
                    # If no valid category, assign to the first category as fallback
                    if main_categories:
                        fallback_category = main_categories[0]
                        response_data["resultsByCategory"][fallback_category].append(paper)
                        print(f"    - Assigned paper {paper.get('id')} to fallback category: {fallback_category}")
                        assigned_in_fix += 1
                    else:
                         print(f"    - Could not assign paper {paper.get('id')}: No valid categories available.")
            
            # Log the updated counts
            category_paper_count_after = sum(len(papers) for papers in response_data["resultsByCategory"].values())
            print(f"  - Total papers assigned in fix: {assigned_in_fix}")
            print(f"  - Category paper count after fix: {category_paper_count_after}")
            print("*** EMERGENCY FIX COMPLETE ***\n")
        
        # === DEBUG === Final check of the structure being sent
        print("\n====== DEBUG: FINAL RESPONSE DATA STRUCTURE ======")
        print(f"Keys: {list(response_data.keys())}")
        print(f"categories: {response_data.get('categories')}")
        print(f"top_results count: {len(response_data.get('top_results', []))}")
        print("resultsByCategory details:")
        for cat, papers in response_data.get("resultsByCategory", {}).items():
            print(f"  - {cat}: {len(papers)} papers")
        print("================================================\n")
        
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        print(f"Error during advanced search: {e}")
        print(traceback.format_exc()) # Print full traceback
        return jsonify({"error": f"Search failed: {str(e)}"}), 500

@app.route('/filter_papers', methods=['POST'])
def filter_papers():
    """Endpoint to filter papers for relevance using Gemini."""
    try:
        data = request.get_json()
        papers = data.get('papers', [])
        query = data.get('query', '')
        
        if not papers:
            return jsonify({'error': 'No papers provided for filtering'}), 400
            
        if not query:
            return jsonify({'error': 'No query provided for filtering'}), 400
            
        # Check if API keys are configured
        if not api_keys_configured:
            return jsonify({'error': 'API keys not configured. Please set your API keys first.'}), 400
            
        # Filter papers for relevance
        filtered_papers = filter_papers_by_relevance(papers, query)
        
        # Return the filtered papers
        return jsonify({
            'filtered_papers': filtered_papers
        })
        
    except Exception as e:
        print(f"Error in paper filtering: {e}")
        return jsonify({'error': f'Filtering failed - {str(e)}'}), 500

@app.route('/get_category_code', methods=['POST'])
def get_category_code():
    """Returns the arXiv code for a given category name."""
    try:
        data = request.get_json()
        category = data.get('category', '')
        
        if not category:
            return jsonify({'error': 'No category provided'}), 400
            
        # Direct lookup
        code = TOPICS.get(category)
        if code:
            return jsonify({'code': code})
            
        # Fuzzy matching
        import difflib
        category_display_names = list(TOPICS.keys())
        matches = difflib.get_close_matches(category, category_display_names, n=1, cutoff=0.7)
        if matches:
            matched_category = matches[0]
            code = TOPICS.get(matched_category)
            if code:
                return jsonify({'code': code, 'matched_category': matched_category})
        
        # No match found
        return jsonify({'code': None})
        
    except Exception as e:
        print(f"Error getting category code: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001) # Set debug=False in production
