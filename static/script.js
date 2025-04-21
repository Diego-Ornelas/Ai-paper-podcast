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

    // Advanced search elements
    const topicSearchBtn = document.getElementById('topic-search-btn');
    const advancedSearchBtn = document.getElementById('advanced-search-btn');
    const topicSearchDiv = document.getElementById('topic-search');
    const advancedSearchDiv = document.getElementById('advanced-search');
    const searchQueryInput = document.getElementById('search-query');
    const advancedSearchButton = document.getElementById('advanced-search-button');
    const advancedSearchLoadingDiv = document.getElementById('advanced-search-loading');
    const advancedSearchErrorDiv = document.getElementById('advanced-search-error');
    const searchCategoriesDiv = document.getElementById('search-categories');
    const categoryTagsDiv = document.getElementById('category-tags');
    const resultsTabsDiv = document.getElementById('results-tabs');
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabPanes = document.querySelectorAll('.tab-pane');

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
    
    audioPlayerContainer.appendChild(audioPlayer);
    document.querySelector('.section:nth-child(3)').appendChild(audioPlayerContainer);

    let selectedTopics = new Set();
    let currentPapers = []; // Store fetched papers data
    let currentScript = ''; // Store current script
    let currentCategories = []; // Store current search categories
    let currentCategorizedResults = {}; // Store current categorized results
    let currentCategoryMap = {}; // Store the category map for debugging

    // --- Search Type Switching ---
    topicSearchBtn.addEventListener('click', () => {
        if (!topicSearchBtn.classList.contains('active')) {
            // Switch search types
            topicSearchBtn.classList.add('active');
            advancedSearchBtn.classList.remove('active');
            topicSearchDiv.style.display = 'block';
            advancedSearchDiv.style.display = 'none';
            
            // Reset search state
            clearResults();
            hideSearchCategories();
        }
    });
    
    advancedSearchBtn.addEventListener('click', () => {
        if (!advancedSearchBtn.classList.contains('active')) {
            // Switch search types
            advancedSearchBtn.classList.add('active');
            topicSearchBtn.classList.remove('active');
            advancedSearchDiv.style.display = 'block';
            topicSearchDiv.style.display = 'none';
            
            // Reset search state
            clearResults();
            hideSearchCategories();
        }
    });

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
            hideSearchCategories();
        }
    });

    // --- Advanced Search ---
    advancedSearchButton.addEventListener('click', async () => {
        const query = searchQueryInput.value.trim();
        
        if (!query) {
            showError(advancedSearchErrorDiv, 'Please enter a search query');
            return;
        }
        
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
            // console.error('Error checking API keys:', error);
        }
        
        // Add click effect
        addClickEffect(advancedSearchButton);
        
        // Clear previous results
        clearResults();
        hideSearchCategories();
        hideError(advancedSearchErrorDiv);
        hideError(paperErrorDiv);
        
        // Scroll to papers section
        document.querySelector('.section:nth-child(2)').scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });
        
        // Show progress indicators instead of simple loading
        const searchProgressDiv = document.getElementById('search-progress');
        const advancedSearchLoadingDiv = document.getElementById('advanced-search-loading');
        advancedSearchLoadingDiv.style.display = 'none';
        searchProgressDiv.style.display = 'block';
        
        // Initialize progress steps
        updateSearchStepStatus('step-categorize', 'pending');
        updateSearchStepStatus('step-collect', 'pending');
        updateSearchStepStatus('step-rank', 'pending');
        updateSearchStepStatus('step-simplify', 'pending');

        // Start the process
        updateSearchStepStatus('step-categorize', 'active');
        
        // DEBUG: Log query being sent for categorization
        console.log('==== CATEGORIZING QUERY: DEBUG ====');
        console.log('Input query being sent to AI for categorization:', query);
        console.log('Waiting for AI response...');
        
        try {
            // Simulate a small delay to show the categorization step
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Start the actual search
            console.log('Sending request to /advanced_search endpoint with query:', query);
            const response = await fetch('/advanced_search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query }),
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                console.error('Advanced search error response:', errorData);
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            // === DEBUG === Log the entire data object received from backend
            console.log("==== DEBUG: FULL BACKEND RESPONSE (data object) ====");
            console.log(JSON.stringify(data, null, 2)); 
            console.log("=====================================================");
            
            // DEBUG: Log AI response for categorization
            console.log('==== AI CATEGORIZATION RESPONSE ====');
            console.log('Raw response from /advanced_search:', data);
            
            if (data.ai_request) {
                console.log('==== AI REQUEST DETAILS ====');
                console.log('Prompt sent to AI:', data.ai_request);
            }
            
            if (data.ai_response) {
                console.log('==== AI RESPONSE DETAILS ====');
                console.log('Raw AI response:', data.ai_response);
            }
            
            console.log('==== CATEGORIZATION RESULTS ====');
            console.log('Selected categories:', data.categories);
            console.log('Category mapping:', data.category_map);
            
            // Mark categorization step as complete - CATEGORIZATION END
            updateSearchStepStatus('step-categorize', 'complete');
            updateSearchStepStatus('step-collect', 'active');
            
            // Simulate a small delay for the collecting papers step
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Store results (Keep as is)
            currentCategories = data.categories || [];
            currentCategorizedResults = data.resultsByCategory || {};
            currentPapers = data.top_results || [];
            currentCategoryMap = data.category_map || {}; // Store the map
            
            // === DEBUG === Log the assigned currentCategorizedResults
            console.log("==== DEBUG: Assigned currentCategorizedResults ====");
            console.log(currentCategorizedResults);
            console.log("===================================================");

            // Mark collection step as complete and activate ranking step
            updateSearchStepStatus('step-collect', 'complete');
            updateSearchStepStatus('step-rank', 'active');
            
            // Display search categories (Pass map for info)
            displaySearchCategories(currentCategories, currentCategoryMap);
            
            // Simulate a small delay for the ranking step
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // Mark ranking as complete and activate filtering step
            updateSearchStepStatus('step-rank', 'complete');
            updateSearchStepStatus('step-filter', 'active');
            
            // Show progress for the filtering step
            const filterStep = document.getElementById('step-filter');
            if (filterStep) {
                const descriptionEl = filterStep.querySelector('.step-description');
                if (descriptionEl) {
                    descriptionEl.textContent = 'Evaluating relevance of papers to your query';
                }
            }
            
            // Simulate a small delay for the filtering step
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // Move to the next step (Filtering is handled on the backend in the search_and_rank_papers function)
            updateSearchStepStatus('step-filter', 'complete');
            updateSearchStepStatus('step-titles', 'active');
            
            // Display papers in tabs (grouped by main category)
            setupResultsTabs(currentCategories, currentCategorizedResults, currentPapers);
            
            // Show results summary (Pass map for info)
            displayResultsSummary(currentCategories, currentCategorizedResults, currentPapers, currentCategoryMap);
            
            // Check if tabs are showing correctly after a short delay
            setTimeout(() => {
                const tabsShown = document.getElementById('results-tabs').style.display === 'block';
                const tablesVisible = document.querySelectorAll('.tab-pane.active .papers-table').length > 0;
                
                const topResultsHaveRelevance = currentPapers && currentPapers.length > 0 && 
                    currentPapers.every(paper => paper.relevance_score !== undefined);
                
                if (!tabsShown || !tablesVisible) {
                    console.warn('Tab display mechanism failed, switching to emergency display');
                    emergencyDisplayResults(currentCategories, currentCategorizedResults, currentPapers);
                }
            }, 500);
            
            // After displaying initial structure, fetch plain titles for all papers
            const allPapers = [...currentPapers];
            // Add papers from categories (avoiding duplicates by ID)
            const processedIds = new Set(currentPapers.map(paper => paper.id));
            
            Object.values(currentCategorizedResults).forEach(categoryPapers => {
                categoryPapers.forEach(paper => {
                    if (!processedIds.has(paper.id)) {
                        allPapers.push(paper);
                        processedIds.add(paper.id);
                    }
                });
            });
            
            // Generate plain English titles
            await fetchAndDisplayPlainTitles(allPapers);
            
            // Mark titles step as complete
            updateSearchStepStatus('step-titles', 'complete');
            
            // Hide progress indicators after a short delay
            setTimeout(() => {
                searchProgressDiv.style.display = 'none';
            }, 1500);
            
            // Add a fallback direct display if needed
            const tabsShown = document.getElementById('results-tabs').style.display === 'block';
            const hasTopResults = currentPapers && currentPapers.length > 0;
            
            console.log('Tabs shown:', tabsShown, 'Has top results:', hasTopResults);
            
            // If tabs aren't showing and we have results, show directly in the papers list
            if (!tabsShown && hasTopResults) {
                console.log('Fallback to direct display in papers-list');
                papersListDiv.innerHTML = '<h3>Fallback Display - Found Papers:</h3>';
                const directTable = createPapersTable(currentPapers);
                directTable.style.opacity = '1';
                papersListDiv.appendChild(directTable);
            }
            
        } catch (error) {
            console.error('Error during advanced search process:', error);
            // Mark current step as error
            document.querySelectorAll('.progress-step.active').forEach(step => {
                updateSearchStepStatus(step.id, 'error');
            });
            showError(paperErrorDiv, `Search error: ${error.message}`);
            currentPapers = [];
            currentCategories = [];
            currentCategorizedResults = {};
        }
    });
    
    // Enter key for search
    searchQueryInput.addEventListener('keyup', (event) => {
        if (event.key === 'Enter') {
            advancedSearchButton.click();
        }
    });
    
    // Tab switching
    document.addEventListener('click', (event) => {
        if (event.target.classList.contains('tab-button')) {
            const tabId = event.target.getAttribute('data-tab');
            
            // Update active tab button
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Update active tab pane
            document.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.remove('active');
            });
            document.getElementById(tabId).classList.add('active');
        }
    });
    
    function displaySearchCategories(categories, categoryMap) {
        if (!categories || categories.length === 0) return;
        
        // Clear previous categories
        categoryTagsDiv.innerHTML = '';
        
        // Add category tags with more detail (now for up to 6 categories)
        categories.forEach(category => {
            const categoryTag = document.createElement('div');
            categoryTag.className = 'category-tag';
            
            // Create a text node for the category name
            const textNode = document.createTextNode(category);
            categoryTag.appendChild(textNode);
            
            // Try to get the arXiv code for this category
            fetch('/get_category_code', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ category }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.code) {
                    const tooltipSpan = document.createElement('span');
                    tooltipSpan.className = 'arxiv-code';
                    tooltipSpan.textContent = data.code;
                    categoryTag.appendChild(tooltipSpan);
                }
            })
            .catch(error => {
                // console.error('Error getting arXiv code:', error);
            });
            
            categoryTagsDiv.appendChild(categoryTag);
        });
        
        // Add an explanation for the categories
        const categoryInfo = document.createElement('div');
        categoryInfo.className = 'category-info';
        categoryInfo.innerHTML = `
            <i class="fas fa-info-circle"></i> 
            Papers are fetched from arXiv based on these ${categories.length} most relevant categories.
        `;
        categoryTagsDiv.appendChild(categoryInfo);
        
        // Show categories section
        searchCategoriesDiv.style.display = 'block';
    }
    
    function hideSearchCategories() {
        searchCategoriesDiv.style.display = 'none';
        resultsTabsDiv.style.display = 'none';
    }
    
    function setupResultsTabs(categories, resultsByCategory, topResults) {
        if (!categories || categories.length !== 3) {
             console.error("Error: Expected exactly 3 main categories for tab setup...", categories);
             return;
        }
        
        // Add debugging for incoming data structure
        console.log("DEBUG - setupResultsTabs input:");
        console.log("Categories:", categories);
        console.log("resultsByCategory structure:", resultsByCategory);
        console.log("topResults.length:", topResults ? topResults.length : 0);
        
        const tabButtonsContainer = document.querySelector('#results-tabs .tabs');
        const tabContentContainer = document.querySelector('#results-tabs .tab-content');
        
        // Clear existing tabs beyond "Top Results"
        tabButtonsContainer.querySelectorAll('.tab-button:not([data-tab="top-results"])').forEach(btn => btn.remove());
        tabContentContainer.querySelectorAll('.tab-pane:not(#top-results)').forEach(pane => pane.remove());

        // Create a set of IDs of papers shown in top results (only for reference)
        const topResultIds = new Set();
        if (topResults && topResults.length > 0) {
            topResults.forEach(paper => {
                if (paper && paper.id) {
                    topResultIds.add(paper.id);
                }
            });
            console.log(`Stored ${topResultIds.size} top result IDs for reference`);
        }
        
        // Ensure "Top Results" tab is active initially
        const topResultsButton = tabButtonsContainer.querySelector('.tab-button[data-tab="top-results"]');
        if (topResultsButton) topResultsButton.classList.add('active');
        const topResultsPane = tabContentContainer.querySelector('#top-results');
        if (topResultsPane) {
            topResultsPane.classList.add('active');
            topResultsPane.innerHTML = ''; // Clear content
        }
        
        // Populate top results tab
        if (topResults && topResults.length > 0) {
            const sortedTopResults = [...topResults].sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
            console.log('Top results sorted by relevance score:', sortedTopResults.map(p => ({id: p.id, score: p.relevance_score})));
            const table = createPapersTable(sortedTopResults);
            if (topResultsPane) topResultsPane.appendChild(table);
            table.style.opacity = '1';
        } else {
            if (topResultsPane) topResultsPane.innerHTML = '<div class="no-results"><i class="fas fa-search"></i><p>No top results found.</p></div>';
        }
        
        // Populate category tabs (now up to 6)
        let hasAnyContent = topResults && topResults.length > 0;
        
        // Handle different data structures from the backend
        // The backend might return resultsByCategory as {by_category: {category1: [...], category2: [...]}}
        // or directly as {category1: [...], category2: [...]}
        let categoryResults = resultsByCategory;
        
        // Check if we need to extract from a nested structure
        if (resultsByCategory && resultsByCategory.by_category && typeof resultsByCategory.by_category === 'object') {
            console.log("DEBUG - Extracting from nested 'by_category' structure");
            categoryResults = resultsByCategory.by_category;
        }
        
        // If resultsByCategory is still not properly structured, try to adapt
        if (!categoryResults || typeof categoryResults !== 'object') {
            console.error("Invalid resultsByCategory structure:", resultsByCategory);
            categoryResults = {};
            categories.forEach(cat => categoryResults[cat] = []);
        }
        
        console.log("DEBUG - Final categoryResults structure:", categoryResults);
        
        categories.forEach((category, index) => {
            const categoryId = `category-${index + 1}`;
            
            // Create tab button
            const button = document.createElement('button');
            button.className = 'tab-button';
            button.textContent = category;
            button.setAttribute('data-tab', categoryId);
            tabButtonsContainer.appendChild(button);
            
            // Create tab pane
            const categoryPane = document.createElement('div');
            categoryPane.id = categoryId;
            categoryPane.className = 'tab-pane';
            tabContentContainer.appendChild(categoryPane);
            
            console.log(`Setting up tab for category: ${category}, pane ID: ${categoryId}`);
            
            // Get papers for this category, handling different possible structures
            let categoryPapers = [];
            
            if (categoryResults[category] && Array.isArray(categoryResults[category])) {
                categoryPapers = categoryResults[category];
            } else {
                console.warn(`No papers array found for category: ${category}`);
            }
            
            // Debug the number of papers found
            console.log(`Category ${category} has ${categoryPapers.length} papers`);
            
            // Mark papers that are also in top results
            categoryPapers.forEach(paper => {
                if (paper && paper.id) {
                    paper.isAlsoInTopResults = topResultIds.has(paper.id);
                }
            });
            
            // Sort by relevance score
            categoryPapers.sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
            
            if (categoryPapers.length > 0) {
                const table = createPapersTable(categoryPapers);
                categoryPane.appendChild(table);
                table.style.opacity = '1';
                hasAnyContent = true;
            } else {
                categoryPane.innerHTML = '<div class="no-results"><i class="fas fa-filter"></i><p>No relevant papers found for this category.</p></div>';
            }
        });
        
        // Show tabs container only if we have some content
        resultsTabsDiv.style.display = hasAnyContent ? 'block' : 'none';
        
        // If no content at all, show a message in the papers list
        if (!hasAnyContent) {
            papersListDiv.innerHTML = '<div class="no-results"><i class="fas fa-exclamation-circle"></i><p>No relevant papers found for your search query. Try different search terms.</p></div>';
        }
    }
    
    function createPapersTable(papers) {
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
        if (papers && papers.length > 0) {
            papers.forEach((paper, index) => {
                if (!paper || !paper.id || !paper.title) {
                    return; // Skip invalid papers
                }
                
                const row = tbody.insertRow();
                row.classList.add('paper-item');
                row.dataset.paperId = paper.id;
                row.dataset.paperIndex = index;
                
                // Add relevance score as a data attribute for sorting/filtering
                if (paper.relevance_score !== undefined) {
                    row.dataset.relevanceScore = paper.relevance_score;
                }
                
                // Mark if paper is also in top results
                if (paper.isAlsoInTopResults) {
                    row.classList.add('in-top-results');
                }
                
                const cell1 = row.insertCell();
                
                // Check if the paper has relevance information
                let relevanceHtml = '';
                if (paper.relevance_explanation && paper.relevance_explanation !== "Not relevant to the query") {
                    relevanceHtml = `
                        <div class="paper-relevance">
                            <div class="relevance-badge ${getRelevanceClass(paper.relevance_score)}">
                                ${paper.relevance_score !== undefined ? paper.relevance_score : 'N/A'}
                            </div>
                            <div class="relevance-explanation">
                                <i class="fas fa-quote-left"></i> ${paper.relevance_explanation}
                            </div>
                        </div>
                    `;
                }
                
                // Add a top result badge if applicable
                let topResultBadge = '';
                if (paper.isAlsoInTopResults) {
                    topResultBadge = '<span class="top-result-badge"><i class="fas fa-star"></i> Top Result</span>';
                }
                
                cell1.innerHTML = `
                    <div class="paper-info">
                        <div class="paper-title-row">
                            <div class="paper-title">${paper.title}</div>
                            ${topResultBadge}
                        </div>
                        <div class="paper-id">ID: ${paper.id}</div>
                        ${relevanceHtml}
                    </div>
                `;
                
                const cell2 = row.insertCell();
                cell2.innerHTML = `
                    <div class="plain-title-container">
                        <div class="plain-title">
                            <div class="plain-title-loading">
                                <i class="fas fa-spinner fa-spin"></i> Generating...
                            </div>
                        </div>
                        <button class="paper-select-button">
                            <i class="fas fa-microphone-alt"></i> Generate Podcast
                        </button>
                    </div>
                `;
                
                // Add event listener for paper selection
                const selectButton = cell2.querySelector('.paper-select-button');
                selectButton.addEventListener('click', () => {
                    handlePaperSelection(index, papers[index]);
                });
            });
        } else {
            console.warn('No papers to display in table');
            const emptyRow = tbody.insertRow();
            const cell = emptyRow.insertCell();
            cell.colSpan = 2;
            cell.innerHTML = '<div class="no-results"><i class="fas fa-search"></i><p>No papers found.</p></div>';
        }
        
        return table;
    }

    // Helper function to get CSS class for relevance badge
    function getRelevanceClass(score) {
        if (score === undefined || score === null) return 'relevance-unknown';
        if (score >= 80) return 'relevance-high';
        if (score >= 50) return 'relevance-medium';
        return 'relevance-low';
    }

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
            // console.error('Error checking API keys:', error);
        }

        // Add click effect
        addClickEffect(fetchButton);
        
        clearResults();
        hideSearchCategories();
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
            row.dataset.paperId = paper.id;
            row.dataset.paperIndex = index;

            const cell1 = row.insertCell();
            cell1.innerHTML = `
                <div class="paper-info">
                    <div class="paper-title">${paper.title}</div>
                    <div class="paper-id">ID: ${paper.id}</div>
                </div>
            `;

            const cell2 = row.insertCell();
            cell2.innerHTML = `
                <div class="plain-title-container">
                    <div class="plain-title">
                        <div class="plain-title-loading">
                            <i class="fas fa-spinner fa-spin"></i> Generating...
                        </div>
                    </div>
                    <button class="paper-select-button">
                        <i class="fas fa-microphone-alt"></i> Generate Podcast
                    </button>
                </div>
            `;
            
            // Add event listener for paper selection
            const selectButton = cell2.querySelector('.paper-select-button');
            selectButton.addEventListener('click', () => {
                handlePaperSelection(index, papers[index]);
            });
        });

        papersListDiv.appendChild(table);
    }

    // --- Plain English Titles ---
    async function fetchAndDisplayPlainTitles(papers) {
        // Show total papers count in the titles step
        const titleStep = document.getElementById('step-titles');
        if (titleStep) {
            const descriptionEl = titleStep.querySelector('.step-description');
            if (descriptionEl) {
                descriptionEl.textContent = `Creating readable titles for ${papers.length} papers`;
            }
        }
        
        let processedCount = 0;
        
        for (let i = 0; i < papers.length; i++) {
            const paper = papers[i];
            
            // Find all rows for this paper (there might be multiple due to categorized tabs)
            const paperRows = document.querySelectorAll(`.paper-item[data-paper-id="${paper.id}"]`);
            
            // Only fetch if we have found rows and the paper doesn't already have a plain title
            if (paperRows.length > 0 && !paper.plain_title) {
                try {
                    // Show AI generation indicator
                    paperRows.forEach(row => {
                        const plainTitleDiv = row.querySelector('.plain-title');
                        plainTitleDiv.innerHTML = `
                            <div class="plain-title-loading">
                                <i class="fas fa-robot fa-spin"></i> AI summarizing title ${i+1}/${papers.length}...
                            </div>
                        `;
                    });
                    
                const response = await fetch('/generate_plain_title', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                        body: JSON.stringify({
                            title: paper.title,
                            abstract: paper.abstract
                        }),
                });
                    
                if (!response.ok) {
                        throw new Error(`HTTP error! status: ${response.status}`);
                }
                    
                const data = await response.json();
                    const plainTitle = data.plain_title;
                    
                    // Save plain title to paper object for later reference
                    paper.plain_title = plainTitle;
                    
                    // Update all rows for this paper
                    paperRows.forEach(row => {
                        const plainTitleDiv = row.querySelector('.plain-title');
                        plainTitleDiv.innerHTML = `<div class="plain-title-text">${plainTitle}</div>`;
                    });
                    
                    // Update progress count
                    processedCount++;
                    
                    // Update the titles step description
                    if (titleStep) {
                        const descriptionEl = titleStep.querySelector('.step-description');
                        if (descriptionEl) {
                            descriptionEl.textContent = `Created ${processedCount}/${papers.length} readable titles`;
                        }
                    }
                    
                } catch (error) {
                    console.error(`Error generating plain title for paper ${paper.id}:`, error);
                    // Update with an error message
                    paperRows.forEach(row => {
                        const plainTitleDiv = row.querySelector('.plain-title');
                        plainTitleDiv.innerHTML = `<div class="plain-title-error">Could not generate title</div>`;
                    });
                    
                    // Still count as processed
                    processedCount++;
                }
            } else if (paperRows.length > 0 && paper.plain_title) {
                // If the paper already has a plain title, just display it
                paperRows.forEach(row => {
                    const plainTitleDiv = row.querySelector('.plain-title');
                    plainTitleDiv.innerHTML = `<div class="plain-title-text">${paper.plain_title}</div>`;
                });
                
                // Count as processed
                processedCount++;
            }
        }
        
        // Update final count when all done
        if (titleStep) {
            const descriptionEl = titleStep.querySelector('.step-description');
            if (descriptionEl) {
                descriptionEl.textContent = `Created ${processedCount}/${papers.length} readable titles`;
            }
        }
    }

    // --- Paper Selection for Podcast Generation ---
    async function handlePaperSelection(index, selectedPaper) {
        if (!selectedPaper) {
            selectedPaper = currentPapers[index]; // Fallback to currentPapers
        }
        
        if (!selectedPaper) {
            showError(podcastErrorDiv, 'Could not find selected paper.');
            return;
        }
        
        // Scroll to podcast section
        document.querySelector('.section:nth-child(3)').scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start' 
        });

        clearPodcastScript();
        hideError(podcastErrorDiv);
        showLoading(podcastLoadingDiv);
        
        // Hide the audio player if visible
        audioPlayerContainer.style.display = 'none';
        
        // Update UI to show which step we're on
        const generationSteps = document.createElement('div');
        generationSteps.className = 'generation-steps';
        generationSteps.innerHTML = `
            <div class="step" id="step-script"><i class="fas fa-file-alt"></i> Generating script...</div>
            <div class="step" id="step-audio"><i class="fas fa-microphone"></i> Converting to audio...</div>
        `;
        
        // Insert steps before loading indicator
        podcastLoadingDiv.insertAdjacentElement('afterbegin', generationSteps);
        
        // Set initial status
        updateStepStatus('step-script', 'active');
        
        try {
            // First step: Generate the podcast script
            const scriptResponse = await fetch('/generate_podcast', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    id: selectedPaper.id, 
                    pdf_link: selectedPaper.pdf_link
                }),
            });

            if (!scriptResponse.ok) {
                const errorData = await scriptResponse.json();
                throw new Error(errorData.error || `HTTP error! status: ${scriptResponse.status}`);
            }

            const scriptData = await scriptResponse.json();
            
            // Store the generated script
            currentScript = scriptData.script;
            
            // Update UI to show script generation is complete
            updateStepStatus('step-script', 'complete');
            updateStepStatus('step-audio', 'active');
            
            // Display the generated script
            displayPodcastScript(currentScript);
            
            // Second step: Convert script to audio
            const audioResponse = await fetch(`/audio/${selectedPaper.id}?script=${encodeURIComponent(currentScript)}`);
            
            if (!audioResponse.ok) {
                    const errorData = await audioResponse.json();
                throw new Error(errorData.error || `HTTP error! status: ${audioResponse.status}`);
            }
            
            // Success - get the audio blob
            const audioBlob = await audioResponse.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            
            // Update the audio player and show it
            audioPlayer.src = audioUrl;
                audioPlayerContainer.style.display = 'block';
                
            // Update UI to show audio generation is complete
            updateStepStatus('step-audio', 'complete');
            
        } catch (error) {
            console.error('Error generating podcast:', error);
            showError(podcastErrorDiv, `Error generating podcast: ${error.message}`);
        } finally {
            hideLoading(podcastLoadingDiv);
        }
        
        function updateStepStatus(stepId, status) {
            const step = document.getElementById(stepId);
            if (!step) return;
            
            // Remove existing status classes
            step.classList.remove('active', 'complete', 'error');
            
            // Add new status class
            step.classList.add(status);
            
            // Update icon
            const icon = step.querySelector('i');
            if (icon) {
                icon.className = ''; // Clear existing classes
                
                switch (status) {
                    case 'active':
                        icon.className = 'fas fa-spinner fa-spin';
                        break;
                    case 'complete':
                        icon.className = 'fas fa-check-circle';
                        break;
                    case 'error':
                        icon.className = 'fas fa-exclamation-circle';
                        break;
                    default:
                        if (stepId === 'step-script') {
                            icon.className = 'fas fa-file-alt';
                        } else if (stepId === 'step-audio') {
                            icon.className = 'fas fa-microphone';
                        }
                }
            }
        }
    }

    // --- Helper Functions ---
    function animateEntrance() {
        // Add a staggered entrance animation to page elements
        document.querySelectorAll('.section').forEach((section, index) => {
            section.style.animationDelay = `${index * 0.1}s`;
            section.classList.add('fade-in');
        });
    }
    
    function addClickEffect(element) {
        element.classList.add('clicked');
        setTimeout(() => {
            element.classList.remove('clicked');
        }, 300);
    }

    function showLoading(element) {
        if (element) {
            element.style.display = 'flex';
        }
    }

    function hideLoading(element) {
        if (element) {
            element.style.display = 'none';
        }
    }

    function showError(element, message) {
        if (element) {
        element.textContent = message;
        element.style.display = 'block';
        }
    }

    function hideError(element) {
        if (element) {
            element.style.display = 'none';
        }
    }

    function clearResults() {
        papersListDiv.innerHTML = '';
        clearPodcastScript();
        hideError(paperErrorDiv);
    }

    function clearPodcastScript() {
        podcastScriptPre.textContent = '';
        hideError(podcastErrorDiv);
        audioPlayerContainer.style.display = 'none';
    }

    function displayPodcastScript(script) {
        // Simple approach - just set the text
        podcastScriptPre.textContent = script;
    }

    // Update search progress step status
    function updateSearchStepStatus(stepId, status) {
        const step = document.getElementById(stepId);
        if (!step) return;
        
        // Remove existing state classes
        step.className = 'progress-step';
        
        // Add new state class
        step.classList.add(status);
        
        // Update the icon based on status
        const icon = step.querySelector('.step-status i');
        if (icon) {
            switch (status) {
                case 'waiting':
                    icon.className = 'fas fa-circle';
                    break;
                case 'active':
                    icon.className = 'fas fa-spinner fa-spin';
                    break;
                case 'complete':
                    icon.className = 'fas fa-check-circle';
                    break;
                case 'error':
                    icon.className = 'fas fa-exclamation-circle';
                    break;
            }
        }
    }
    
    // Display results summary
    function displayResultsSummary(categories, resultsByCategory, topResults) {
        const resultsSummaryDiv = document.getElementById('results-summary');
        const categoryStatsDiv = document.getElementById('category-stats');
        const categoriesCountSpan = document.getElementById('summary-categories-count');
        
        if (!resultsSummaryDiv || !categoryStatsDiv) return;
        
        // Update categories count
        const numCategories = categories.length;
        if (categoriesCountSpan) {
            categoriesCountSpan.textContent = numCategories;
        }
        
        // Clear previous stats
        categoryStatsDiv.innerHTML = '';
        
        // Count unique relevant papers across all categories and top results
        const allPaperIds = new Set();
        const topResultIds = new Set();
        
        if (topResults && topResults.length > 0) {
            topResults.forEach(paper => {
                if (paper && paper.id) {
                    allPaperIds.add(paper.id);
                    topResultIds.add(paper.id);
                }
            });
        }
        
        categories.forEach(category => {
            const papers = resultsByCategory[category] || [];
            papers.forEach(paper => {
                if (paper && paper.id) {
                    allPaperIds.add(paper.id);
                }
            });
        });
        
        const uniquePapersCount = allPaperIds.size;
        console.log(`Summary: Found ${uniquePapersCount} unique relevant papers across ${numCategories} categories.`);

        // Update the summary description
        const summaryDescriptionDiv = document.querySelector('.summary-description');
        if (summaryDescriptionDiv) {
            if (uniquePapersCount > 0) {
                summaryDescriptionDiv.innerHTML = `
                    We analyzed papers from <span id="summary-categories-count">${numCategories}</span> relevant arXiv categories 
                    and found <span class="highlight">${uniquePapersCount}</span> unique papers matching your query.
                    ${topResults && topResults.length > 0 
                        ? ` The top ${topResults.length} papers based on AI relevance ranking are shown in the \'Top Results\' tab.` 
                        : ''}
                `;
            } else {
                summaryDescriptionDiv.innerHTML = `
                    We analyzed papers from <span id="summary-categories-count">${numCategories}</span> relevant arXiv categories 
                    but did not find any relevant papers matching your query. Please try modifying your search terms.
                `;
            }
        }
        
        // Add stats for each category
        categories.forEach(category => {
            const papers = resultsByCategory[category] || [];
            const displayCount = papers.length;
            
            console.log(`Creating stat for category ${category}: ${displayCount} papers`);
            
            const statDiv = document.createElement('div');
            statDiv.className = 'category-stat';
            statDiv.innerHTML = `<i class="fas fa-file-alt"></i> ${category}: ${displayCount} relevant papers`;
            categoryStatsDiv.appendChild(statDiv);
        });
        
        // Add stat for top results (only if they exist)
        if (topResults && topResults.length > 0) {
            const topStatDiv = document.createElement('div');
            topStatDiv.className = 'category-stat highlight-stat';
            topStatDiv.innerHTML = `<i class="fas fa-star"></i> Top Results: ${topResults.length} most relevant papers`;
            categoryStatsDiv.appendChild(topStatDiv);
        }
        
        // Add info about filtering only if we have papers
        if (uniquePapersCount > 0) {
            const filterInfoDiv = document.createElement('div');
            filterInfoDiv.className = 'filter-info';
            filterInfoDiv.innerHTML = `
                <i class="fas fa-filter"></i> Papers were deduplicated, ranked by AI, and filtered for relevance.
            `;
            categoryStatsDiv.appendChild(filterInfoDiv);
        }
        
        // Show the summary
        resultsSummaryDiv.style.display = 'block';
    }

    // Emergency display function that bypasses the tab system
    function emergencyDisplayResults(categories, resultsByCategory, topResults) {
        console.log('EMERGENCY: Using direct display of results');
        
        // Clear previous results
        papersListDiv.innerHTML = '';
        
        // Create a container for the emergency display
        const emergencyContainer = document.createElement('div');
        emergencyContainer.className = 'emergency-results';
        
        // Add a header
        const header = document.createElement('div');
        header.className = 'emergency-header';
        header.innerHTML = `
            <h3>Search Results</h3>
            <p>Displaying results directly due to tab display issues</p>
        `;
        emergencyContainer.appendChild(header);
        
        // Display Top Results
        if (topResults && topResults.length > 0) {
            const topResultsSection = document.createElement('div');
            topResultsSection.className = 'emergency-section';
            topResultsSection.innerHTML = `<h4>Top Results (${topResults.length})</h4>`;
            
            const table = createPapersTable(topResults);
            table.style.opacity = '1';
            topResultsSection.appendChild(table);
            emergencyContainer.appendChild(topResultsSection);
        }
        
        // Display each category's results
        if (categories && categories.length > 0) {
            categories.forEach(category => {
                const categoryPapers = resultsByCategory[category] || [];
                if (categoryPapers.length > 0) {
                    const categorySection = document.createElement('div');
                    categorySection.className = 'emergency-section';
                    categorySection.innerHTML = `<h4>${category} (${categoryPapers.length})</h4>`;
                    
                    const table = createPapersTable(categoryPapers);
                    table.style.opacity = '1';
                    categorySection.appendChild(table);
                    emergencyContainer.appendChild(categorySection);
                }
            });
        }
        
        // Display a message if no results
        if (emergencyContainer.children.length <= 1) {
            emergencyContainer.innerHTML += `
                <div class="no-results">
                    <i class="fas fa-exclamation-circle"></i>
                    <p>No papers found for your search query. Try different search terms.</p>
                </div>
            `;
        }
        
        // Add the emergency container to the page
        papersListDiv.appendChild(emergencyContainer);
        
        // Style for emergency display
        const style = document.createElement('style');
        style.textContent = `
            .emergency-results { margin-top: 20px; }
            .emergency-header { margin-bottom: 20px; }
            .emergency-header h3 { color: #4263eb; margin-bottom: 5px; }
            .emergency-header p { color: #fa5252; }
            .emergency-section { margin-bottom: 30px; }
            .emergency-section h4 { 
                padding: 10px 15px;
                background-color: #f1f3f5;
                border-left: 4px solid #4263eb;
                margin-bottom: 10px;
            }
        `;
        document.head.appendChild(style);
    }
}); 
