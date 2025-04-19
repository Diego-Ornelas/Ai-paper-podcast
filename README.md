# AI Paper Podcast Generator

Transform complex academic papers into engaging podcast episodes with AI.

## Prerequisites

- Docker and Docker Compose
- OpenAI API key
- Google Gemini API key

## Setup Instructions

1. Clone this repository:
   ```
   git clone <repository-url>
   cd AI-podcast
   ```

2. Set up your environment variables:
   ```
   cp .env-example .env
   ```
   
   Edit the `.env` file and add your API keys:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```

3. Build and start the application with Docker Compose:
   ```
   docker-compose up --build
   ```

4. Access the application at http://localhost:5000

## Using the Application

1. Select one or more research topics
2. Choose a paper from the list of fetched papers
3. Generate a podcast script using Gemini AI
4. Generate audio for the script using OpenAI's TTS

## Features

### Automatic Script Chunking for Audio Generation

The application automatically handles long podcast scripts by:
- Splitting text at natural boundaries (sentences, commas, etc.)
- Processing each chunk separately to stay within OpenAI's TTS character limits
- Seamlessly joining the audio segments into a single file

This allows for generating audio from podcasts of any length without manual intervention.

## Troubleshooting

### Audio Generation Issues

If you encounter issues with audio generation:

1. Make sure your OpenAI API key has access to the TTS API
2. Check that ffmpeg is installed correctly in the Docker container
3. Verify your script isn't using formatting that OpenAI TTS can't process

### API Key Issues

If your API keys aren't working:

1. Verify they are correctly set in the `.env` file
2. Ensure the keys have sufficient quota/credits remaining
3. Check that the API keys have the necessary permissions

## License

[Specify your license information here] 