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
    "Artificial Intelligence": "cs.AI",
    "Machine Learning": "cs.LG",
    "Quantum Physics": "quant-ph",
    "Astrophysics": "astro-ph",
    "Condensed Matter": "cond-mat",
    "High Energy Physics": "hep-ph"
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

# --- Flask Routes ---

@app.route('/')
def index():
    """Renders the main page with topic selection."""
    return render_template('index.html', topics=TOPICS, api_keys_configured=api_keys_configured)

@app.route('/search_papers', methods=['POST'])
def search_papers():
    """Handles paper search requests."""
    data = request.get_json()
    selected_topics = data.get('topics', [])
    print(f"Searching for topics: {selected_topics}")

    if not selected_topics:
        return jsonify({'error': 'No topics selected'}), 400

    # Map display names back to category codes
    category_codes = [TOPICS.get(topic) for topic in selected_topics if TOPICS.get(topic)]

    if not category_codes:
        return jsonify({'error': 'Invalid topics selected'}), 400

    papers = fetch_arxiv_papers(category_codes)

    if not papers:
         # Return empty list instead of error to allow frontend to handle 'no results'
         return jsonify([])
         # return jsonify({'error': 'Could not fetch papers from ArXiv or no papers found.'}), 500

    # Shuffle results for variety on refresh
    random.shuffle(papers)

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

if __name__ == '__main__':
    app.run(debug=True, port=5001) # Set debug=False in production 