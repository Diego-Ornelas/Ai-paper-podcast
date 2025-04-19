document.addEventListener('DOMContentLoaded', () => {
    const topicsDiv = document.getElementById('topics');
    const fetchButton = document.getElementById('fetch-button');
    const papersListDiv = document.getElementById('papers-list');
    const podcastScriptPre = document.getElementById('podcast-script');
    const papersLoadingDiv = document.getElementById('papers-loading');
    const podcastLoadingDiv = document.getElementById('podcast-loading');
    const topicErrorDiv = document.getElementById('topic-error');
    const paperErrorDiv = document.getElementById('paper-error');
    const podcastErrorDiv = document.getElementById('podcast-error');

    // API Keys Modal Elements
    const apiKeysModal = document.getElementById('api-keys-modal');
    const apiKeysForm = document.getElementById('api-keys-form');
    const geminiApiKeyInput = document.getElementById('gemini-api-key');
    const openaiApiKeyInput = document.getElementById('openai-api-key');
    const saveApiKeysButton = document.getElementById('save-api-keys');
    const configureLaterButton = document.getElementById('configure-later');
    const showApiConfigButton = document.getElementById('show-api-config');
    const apiKeysErrorDiv = document.getElementById('api-keys-error');
    const apiKeysSuccessDiv = document.getElementById('api-keys-success');

    // Add audio player elements
    const audioPlayerContainer = document.createElement('div');
    audioPlayerContainer.id = 'audio-player-container';
    audioPlayerContainer.style.display = 'none';
    
    const audioPlayer = document.createElement('audio');
    audioPlayer.id = 'audio-player';
    audioPlayer.controls = true;
    audioPlayer.style.width = '100%';
    
    const generateAudioButton = document.createElement('button');
    generateAudioButton.id = 'generate-audio-button';
    generateAudioButton.innerHTML = '<i class="fas fa-headphones"></i> Generate Audio';
    generateAudioButton.style.display = 'none';
    
    audioPlayerContainer.appendChild(audioPlayer);
    document.querySelector('.section:nth-child(3)').appendChild(generateAudioButton);
    document.querySelector('.section:nth-child(3)').appendChild(audioPlayerContainer);

    let selectedTopics = new Set();
    let currentPapers = []; // Store fetched papers data
    let currentScript = ''; // Store current script

    // --- API Keys Configuration ---
    // Show modal when the floating button is clicked
    if (showApiConfigButton) {
        showApiConfigButton.addEventListener('click', () => {
            apiKeysModal.style.display = 'flex';
        });
    }
    
    // Hide modal when "Configure Later" is clicked
    if (configureLaterButton) {
        configureLaterButton.addEventListener('click', () => {
            apiKeysModal.style.display = 'none';
            // Show the floating button to allow configuration later
            showApiConfigButton.style.display = 'flex';
        });
    }
    
    // Handle form submission
    if (apiKeysForm) {
        apiKeysForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            
            const geminiApiKey = geminiApiKeyInput.value.trim();
            const openaiApiKey = openaiApiKeyInput.value.trim();
            
            if (!geminiApiKey || !openaiApiKey) {
                showApiKeysError('Both API keys are required');
                return;
            }
            
            try {
                const response = await fetch('/save_api_keys', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        gemini_api_key: geminiApiKey,
                        openai_api_key: openaiApiKey
                    }),
                });
                
                const data = await response.json();
                
                if (response.ok && data.success) {
                    // Show success message
                    hideApiKeysError();
                    showApiKeysSuccess();
                    
                    // After 2 seconds, either reload the page or just hide the modal
                    setTimeout(() => {
                        if (data.reload) {
                            // Reload the page to reflect updated API key configuration
                            window.location.reload();
                        } else {
                            apiKeysModal.style.display = 'none';
                            // Hide the floating button after successful configuration
                            showApiConfigButton.style.display = 'none';
                            // Reset the form
                            apiKeysForm.reset();
                            // Hide success message
                            hideApiKeysSuccess();
                        }
                    }, 2000);
                } else {
                    showApiKeysError(data.error || 'Failed to save API keys');
                }
            } catch (error) {
                console.error('Error saving API keys:', error);
                showApiKeysError('Network error, please try again');
            }
        });
    }
    
    function showApiKeysError(message) {
        apiKeysErrorDiv.textContent = message;
        apiKeysErrorDiv.style.display = 'block';
    }
    
    function hideApiKeysError() {
        apiKeysErrorDiv.style.display = 'none';
    }
    
    function showApiKeysSuccess() {
        apiKeysSuccessDiv.style.display = 'block';
    }
    
    function hideApiKeysSuccess() {
        apiKeysSuccessDiv.style.display = 'none';
    }

    // Initial animation
    animateEntrance();

    // --- Topic Selection ---
    topicsDiv.addEventListener('click', (event) => {
        if (event.target.classList.contains('topic-button')) {
            const topic = event.target.dataset.topic;
            
            // Add a click effect
            addClickEffect(event.target);
            
            event.target.classList.toggle('selected');
            if (selectedTopics.has(topic)) {
                selectedTopics.delete(topic);
            } else {
                selectedTopics.add(topic);
            }
            fetchButton.disabled = selectedTopics.size === 0;
            
            // Visual feedback on fetch button
            if (selectedTopics.size > 0) {
                fetchButton.classList.add('active');
            } else {
                fetchButton.classList.remove('active');
            }
            
            // Clear previous results when topics change
            clearResults();
        }
    });

    // --- Fetch Papers ---
    fetchButton.addEventListener('click', async () => {
        if (selectedTopics.size === 0) return;

        // First check if API keys are configured
        try {
            const apiResponse = await fetch('/check_api_keys');
            const apiData = await apiResponse.json();
            
            if (!apiData.all_configured) {
                // Show API keys modal if keys aren't configured
                apiKeysModal.style.display = 'flex';
                return;
            }
        } catch (error) {
            console.error('Error checking API keys:', error);
        }

        // Add click effect
        addClickEffect(fetchButton);
        
        clearResults();
        showLoading(papersLoadingDiv);
        hideError(topicErrorDiv);
        hideError(paperErrorDiv);
        
        // Scroll to papers section
        document.querySelector('.section:nth-child(2)').scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });

        try {
            const response = await fetch('/search_papers', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ topics: Array.from(selectedTopics) }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            currentPapers = await response.json(); // Store paper data
            displayPapers(currentPapers);

            // After displaying initial structure, fetch plain titles
            fetchAndDisplayPlainTitles(currentPapers);

        } catch (error) {
            console.error('Error fetching papers:', error);
            showError(paperErrorDiv, `Error fetching papers: ${error.message}`);
            currentPapers = []; // Clear stored papers on error
            displayPapers([]); // Clear display
        } finally {
            hideLoading(papersLoadingDiv);
        }
    });

    // --- Display Papers ---
    function displayPapers(papers) {
        papersListDiv.innerHTML = ''; // Clear previous list
        if (papers.length === 0) {
            // Handle case where ArXiv search returns no results
            const noResults = document.createElement('div');
            noResults.className = 'no-results';
            noResults.innerHTML = '<i class="fas fa-search"></i><p>No papers found for the selected topics.</p>';
            papersListDiv.appendChild(noResults);
            return;
        }

        const table = document.createElement('table');
        table.classList.add('papers-table');
        const thead = table.createTHead();
        const headerRow = thead.insertRow();
        const th1 = document.createElement('th');
        th1.textContent = 'Original Title';
        headerRow.appendChild(th1);
        const th2 = document.createElement('th');
        th2.textContent = 'Plain English Title';
        headerRow.appendChild(th2);

        const tbody = table.createTBody();
        papers.forEach((paper, index) => {
            const row = tbody.insertRow();
            row.classList.add('paper-item');
            row.dataset.index = index; // Store index to retrieve full paper data on click

            const cell1 = row.insertCell();
            cell1.textContent = paper.title;
            cell1.classList.add('original-title-cell');

            const cell2 = row.insertCell();
            cell2.id = `plain-title-${index}`; // Unique ID for updating later
            cell2.classList.add('plain-title-cell');
            cell2.innerHTML = '<span class="plain-title-loading"><i class="fas fa-spinner fa-spin"></i> Generating...</span>'; // Loading indicator

            // Add click listener to the row
            row.addEventListener('click', () => handlePaperSelection(index));
        });

        papersListDiv.appendChild(table);
        
        // Reveal animation
        setTimeout(() => {
            table.style.opacity = '1';
        }, 100);
    }

    // --- Fetch and Display Plain Titles (Asynchronously) ---
    async function fetchAndDisplayPlainTitles(papers) {
        papers.forEach(async (paper, index) => {
            const plainTitleCell = document.getElementById(`plain-title-${index}`);
            try {
                const response = await fetch('/generate_plain_title', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ title: paper.title, abstract: paper.abstract }),
                });
                if (!response.ok) {
                    // Don't throw, just show error in the cell
                    console.error(`HTTP error fetching plain title for index ${index}: ${response.status}`);
                    if (plainTitleCell) plainTitleCell.innerHTML = '<i class="fas fa-exclamation-circle"></i> Error';
                    return;
                }
                const data = await response.json();
                if (plainTitleCell) {
                    // Fade in animation
                    plainTitleCell.style.opacity = '0';
                    plainTitleCell.textContent = data.plain_title || 'Could not generate';
                    setTimeout(() => {
                        plainTitleCell.style.opacity = '1';
                    }, 100);
                }
            } catch (error) {
                console.error(`Error generating plain title for index ${index}:`, error);
                if (plainTitleCell) plainTitleCell.innerHTML = '<i class="fas fa-exclamation-circle"></i> Error';
            }
        });
    }

    // --- Select Paper & Generate Podcast ---
    async function handlePaperSelection(selectedPaperIndex) {
        const selectedPaper = currentPapers[selectedPaperIndex];

        if (!selectedPaper) return;

        // First check if API keys are configured
        try {
            const apiResponse = await fetch('/check_api_keys');
            const apiData = await apiResponse.json();
            
            if (!apiData.all_configured) {
                // Show API keys modal if keys aren't configured
                apiKeysModal.style.display = 'flex';
                return;
            }
        } catch (error) {
            console.error('Error checking API keys:', error);
        }

        // Highlight selected row (optional)
        document.querySelectorAll('.paper-item.selected').forEach(row => row.classList.remove('selected'));
        const selectedRow = papersListDiv.querySelector(`tr[data-index="${selectedPaperIndex}"]`);
        if (selectedRow) {
            selectedRow.classList.add('selected');
            
            // Add pulse animation to the selected row
            selectedRow.classList.add('pulse');
            setTimeout(() => {
                selectedRow.classList.remove('pulse');
            }, 700);
        }

        clearPodcastScript();
        showLoading(podcastLoadingDiv);
        hideError(podcastErrorDiv);
        
        // Hide audio player and button when generating new script
        audioPlayerContainer.style.display = 'none';
        generateAudioButton.style.display = 'none';
        
        // Scroll to podcast section
        document.querySelector('.section:nth-child(3)').scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });

        try {
            const response = await fetch('/generate_podcast', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    id: selectedPaper.id, 
                    pdf_link: selectedPaper.pdf_link,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            displayPodcastScript(data.script);
            currentScript = data.script;
            
            // Show generate audio button
            generateAudioButton.style.display = 'block';
            
        } catch (error) {
            console.error('Error generating podcast:', error);
            showError(podcastErrorDiv, `Error: ${error.message}`);
        } finally {
            hideLoading(podcastLoadingDiv);
        }
    }

    // --- Generate Audio from Script ---
    generateAudioButton.addEventListener('click', async () => {
        if (!currentScript) {
            showError(podcastErrorDiv, 'No script available to generate audio');
            return;
        }
        
        // Add click effect
        addClickEffect(generateAudioButton);
        
        // Show loading state
        generateAudioButton.disabled = true;
        generateAudioButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating Audio...';
        
        try {
            const selectedPaper = document.querySelector('.paper-item.selected');
            const paperIndex = selectedPaper ? selectedPaper.dataset.index : null;
            const paperId = paperIndex !== null ? currentPapers[paperIndex].id : 'podcast';
            
            console.log(`Requesting audio for paper ID: ${paperId}`);
            
            // Construct a URL with the current script as a parameter
            const url = `/audio/${paperId}?script=${encodeURIComponent(currentScript)}`;
            console.log(`Request URL created: ${url.substring(0, 50)}...`); // Log partial URL for privacy
            
            // Create a fetch request to check for errors before setting audio source
            const response = await fetch(url);
            
            if (!response.ok) {
                // Try to get error message from response
                let errorMessage;
                try {
                    const errorData = await response.json();
                    errorMessage = errorData.error || `Server error: ${response.status}`;
                } catch (e) {
                    errorMessage = `HTTP error! status: ${response.status}`;
                }
                throw new Error(errorMessage);
            }
            
            // Get the audio data as blob
            const audioBlob = await response.blob();
            console.log(`Audio received: ${audioBlob.size} bytes, type: ${audioBlob.type}`);
            
            // Create object URL from blob
            const audioUrl = URL.createObjectURL(audioBlob);
            
            // Set the audio source to the blob URL
            audioPlayer.src = audioUrl;
            
            // Show the audio player container
            audioPlayerContainer.style.display = 'block';
            
            // Make sure the audio player loads correctly
            audioPlayer.load();
            
            // Automatically play the audio when it's ready
            audioPlayer.addEventListener('canplaythrough', () => {
                console.log('Audio ready to play');
                audioPlayer.play().catch(e => {
                    console.error('Error playing audio:', e);
                    showError(podcastErrorDiv, `Error playing audio: ${e.message}`);
                });
            }, { once: true });
            
        } catch (error) {
            console.error('Error generating audio:', error);
            showError(podcastErrorDiv, `Error generating audio: ${error.message}`);
        } finally {
            // Reset button state
            generateAudioButton.disabled = false;
            generateAudioButton.innerHTML = '<i class="fas fa-headphones"></i> Generate Audio';
        }
    });

    // --- Animation Functions ---
    function animateEntrance() {
        const sections = document.querySelectorAll('.section');
        sections.forEach((section, index) => {
            section.style.opacity = '0';
            section.style.transform = 'translateY(20px)';
            setTimeout(() => {
                section.style.opacity = '1';
                section.style.transform = 'translateY(0)';
            }, 100 + (index * 150));
        });
    }
    
    function addClickEffect(element) {
        element.classList.add('click-effect');
        setTimeout(() => {
            element.classList.remove('click-effect');
        }, 300);
    }

    // --- Utility Functions ---
    function showLoading(element) {
        element.style.opacity = '0';
        element.style.display = 'block';
        setTimeout(() => {
            element.style.opacity = '1';
        }, 10);
    }

    function hideLoading(element) {
        element.style.opacity = '0';
        setTimeout(() => {
            element.style.display = 'none';
        }, 300);
    }

    function showError(element, message) {
        element.textContent = message;
        element.style.opacity = '0';
        element.style.display = 'block';
        setTimeout(() => {
            element.style.opacity = '1';
        }, 10);
    }

    function hideError(element) {
        element.style.opacity = '0';
        setTimeout(() => {
            element.style.display = 'none';
        }, 300);
    }

    function clearResults() {
        papersListDiv.innerHTML = '';
        clearPodcastScript();
        hideError(paperErrorDiv);
        hideError(podcastErrorDiv);
    }

    function clearPodcastScript() {
        podcastScriptPre.textContent = '';
        currentScript = '';
        audioPlayerContainer.style.display = 'none';
        generateAudioButton.style.display = 'none';
        audioPlayer.src = '';
    }

    function displayPodcastScript(script) {
        // Fade in the podcast script
        podcastScriptPre.style.opacity = '0';
        podcastScriptPre.textContent = script;
        setTimeout(() => {
            podcastScriptPre.style.opacity = '1';
        }, 300);
    }
}); 