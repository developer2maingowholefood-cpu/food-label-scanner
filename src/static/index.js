let lastResult = null;
const loading = document.getElementById('loading');
const error = document.getElementById('error');
const results = document.getElementById('results');
const imagePreviewContainer = document.getElementById('imagePreviewContainer');
const imagePreview = document.getElementById('imagePreview');
const processBtnGroup = document.getElementById('processBtnGroup'); // Keep for compatibility
const scanProcessBtn = document.getElementById('scanProcessBtn'); // Keep for compatibility
const cameraInput = document.getElementById('cameraInput');
const floatingCameraBtn = document.getElementById('floatingCameraBtn');
const welcomeMessage = document.getElementById('welcomeMessage');
const imageOverlay = document.getElementById('imageOverlay');
const overlayProcessBtn = document.getElementById('overlayProcessBtn');

let selectedFile = null;
let isProcessing = false;

// Modal elements
const ingredientModal = document.getElementById('ingredientModal');
const modalIngredientName = document.getElementById('modalIngredientName');
const modalContent = document.getElementById('modalContent');
const closeModal = document.getElementById('closeModal');

// Ingredient explanation cache to avoid repeated API calls
const explanationCache = new Map();

// Legacy button mode functions - kept for compatibility but hidden
function setScanMode() {
  if (scanProcessBtn) {
    scanProcessBtn.textContent = 'Scan Now';
    scanProcessBtn.onclick = openCameraInput;
    scanProcessBtn.className = 'btn btn-secondary';
  }
}

function setProcessMode() {
  if (scanProcessBtn) {
    scanProcessBtn.textContent = 'Process Now';
    scanProcessBtn.onclick = processImage;
    scanProcessBtn.className = 'btn btn-secondary';
  }
}

function setNewScanMode() {
  if (scanProcessBtn) {
    scanProcessBtn.textContent = '📷 New Scan';
    scanProcessBtn.onclick = startNewScan;
    scanProcessBtn.className = 'btn btn-success';
  }
}

function resetUI() {
  imagePreviewContainer.style.display = 'none';
  imagePreview.src = '';
  if (processBtnGroup) processBtnGroup.style.display = 'none';
  if (scanProcessBtn) scanProcessBtn.style.display = 'block';
  imageOverlay.style.display = 'none';
  imageOverlay.classList.remove('show');
  results.innerHTML = '';
  error.style.display = 'none';
  selectedFile = null;
  isProcessing = false;
  lastResult = null; // Clear last result to prevent mixing
  document.body.classList.remove('processing');
  welcomeMessage.style.display = 'block';
  setScanMode();
}

// Initial state
resetUI();

cameraInput.addEventListener('change', function(e) {
  if (!e.target.files || !e.target.files[0]) return;
  
  // Clear any existing results and state when new image is selected
  results.innerHTML = '';
  error.style.display = 'none';
  lastResult = null;
  
  // Ensure processing class is removed to show buttons
  isProcessing = false;
  document.body.classList.remove('processing');
  
  selectedFile = e.target.files[0];
  welcomeMessage.style.display = 'none';
  const reader = new FileReader();
  reader.onload = function(e) {
    imagePreview.src = e.target.result;
    imagePreviewContainer.style.display = 'block';
    
    // Show overlay with Process Now button
    imageOverlay.style.display = 'flex';
    setTimeout(() => {
      imageOverlay.classList.add('show');
    }, 100); // Small delay for smooth transition
    
    // Keep legacy button logic for compatibility (but hidden)
    if (processBtnGroup) processBtnGroup.style.display = 'none';
    if (scanProcessBtn) scanProcessBtn.style.display = 'none';
    setProcessMode();
  };
  reader.readAsDataURL(selectedFile);
});

function processImage() {
  if (!selectedFile || isProcessing) return;
  
  console.log('Starting processImage - hiding overlay');
  
  // Add processing class to body for CSS control
  document.body.classList.add('processing');
  
  // Hide overlay and legacy buttons during processing
  imageOverlay.style.display = 'none';
  imageOverlay.classList.remove('show');
  if (processBtnGroup) processBtnGroup.style.display = 'none';
  if (scanProcessBtn) scanProcessBtn.style.display = 'none';
  imagePreviewContainer.style.display = 'none';
  
  // Set processing flag
  isProcessing = true;
  
  // Show loading and hide other elements
  loading.style.display = 'block';
  welcomeMessage.style.display = 'none';
  
  // Animate progress steps
  let currentStep = 0;
  const steps = document.querySelectorAll('.step');
  const stepInterval = setInterval(() => {
    if (currentStep > 0) {
      steps[currentStep - 1].classList.remove('active');
    }
    if (currentStep < steps.length) {
      steps[currentStep].classList.add('active');
      currentStep++;
    } else {
      clearInterval(stepInterval);
    }
  }, 1000);
  
  const formData = new FormData();
  formData.append('image', selectedFile, selectedFile.name);
  fetch('/process', {
    method: 'POST',
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    clearInterval(stepInterval);
    loading.style.display = 'none';
    isProcessing = false;
    document.body.classList.remove('processing');
    
    if (data.error) {
      if (data.error === 'not_food_product') {
        showNotFoodProductMessage(data.message, data.description);
      } else if (typeof data.error === 'string') {
        showError(data.error);
      } else {
        showError(data.error.message || 'An error occurred');
      }
      welcomeMessage.style.display = 'block';
    } else {
      lastResult = data;
      displayResults(data);
    }
  })
  .catch(err => {
    clearInterval(stepInterval);
    loading.style.display = 'none';
    isProcessing = false;
    document.body.classList.remove('processing');
    showError('Error processing image: ' + err.message);
    welcomeMessage.style.display = 'block';
  });
}

function downloadJSON() {
  if (!lastResult) return;
  const dataStr = JSON.stringify(lastResult, null, 2);
  const blob = new Blob([dataStr], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'scan_results.json';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function showNewScanButton() {
  const newScanHtml = `
    <div class="new-scan-section">
      <p class="mb-2" style="color: #6c757d; font-weight: 500;">Scan complete! Ready for another?</p>
      <button class="btn-new-scan" onclick="startNewScan()">
        📷 New Scan
      </button>
    </div>
  `;
  results.insertAdjacentHTML('beforeend', newScanHtml);
}

function startNewScan() {
  resetUI();
  openCameraInput();
}

function displayResults(data) {
  // Convert button to New Scan mode after displaying results
  processBtnGroup.style.display = 'flex';
  setNewScanMode();
  
  let tokens = data.raw_content 
      ? data.raw_content.split(',').map(t => t.trim()).filter(t => t.length > 0)
      : [];
  
  // Clean up tokens to remove JSON formatting artifacts
  tokens = tokens.map(token => {
    return token
      .replace(/[{}"\[\]]/g, '') // Remove JSON artifacts
      .replace(/^ingredients\s*:\s*/i, '') // Remove "ingredients:" prefix
      .replace(/^\w+\s*:\s*/i, '') // Remove any other property names
      .trim()
      .replace(/^["']|["']$/g, ''); // Remove quotes
  }).filter(token => token.length > 0 && !token.match(/^[,\s]*$/));
  const flaggedCount = data.recommendation && data.recommendation.flagged_tokens 
    ? data.recommendation.flagged_tokens.length 
    : 0;
  const totalTokens = tokens.length;
  const percentage = totalTokens > 0 ? ((flaggedCount / totalTokens) * 100).toFixed(2) : 0;
  
  let html = '';
  
  // Combined Scan & Recommendation Card
  html += `
    <div class="tabbed-result-card">
      <div class="tab-header">
        <button class="tab-button active" onclick="switchScanTab('scan', event)">
          Scan
        </button>
        <button class="tab-button" onclick="switchScanTab('recommendation', event)">
          Recommendation
        </button>
      </div>
      
      <div class="tab-content">
        <div id="scan-tab" class="tab-pane active">
          <div class="image-section">
            <div class="scanned-image-container">
              <img src="${imagePreview.src}" alt="Scanned Food Label" class="scanned-image">
            </div>
          </div>
        </div>
        
        <div id="recommendation-tab" class="tab-pane">
          ${data.recommendation ? `
            <div class="recommendation-section">
              <div class="recommendation ${data.recommendation.flag.toLowerCase()}">
                <div class="recommendation-header">
                  <h3>${data.recommendation.flag}</h3>
                  <span>${data.recommendation.flag === 'NoGo' ? '⚠️' : '✅'}</span>
                </div>
                ${data.recommendation.flagged_tokens && data.recommendation.flagged_tokens.length > 0 ? `
                  <div class="flagged-ingredients">
                    <p><strong>Concerning ingredients:</strong></p>
                    <div class="flagged-ingredients-scroll">
                      ${data.recommendation.flagged_tokens.map((token, index) => `
                        <div class="flagged-ingredient-item">
                          <span class="ingredient-flag-number">${index + 1}</span>
                          <span class="ingredient-flag-text">${token}</span>
                        </div>
                      `).join('')}
                    </div>
                  </div>
                ` : ``}
              </div>
            </div>
          ` : '<div class="no-recommendation">No recommendation available</div>'}
        </div>
      </div>
    </div>
  `;
  
  // Tabbed Analysis & Comment Card
  html += `
    <div class="tabbed-result-card">
      <div class="tab-header">
        <button class="tab-button active" onclick="switchAnalysisTab('ingredients', event)">
          Ingredients
        </button>
        <button class="tab-button" onclick="switchAnalysisTab('comments', event)">
          Comments
        </button>
      </div>
      
      <div class="tab-content">        
        <div id="ingredients-tab" class="tab-pane active">
          <div class="ingredients-section">
            <div class="ingredient-list-scroll">
              <div class="ingredient-list">
                ${tokens.map((token, index) => {
                  // Check if this specific ingredient is flagged
                  const isFlagged = data.recommendation && data.recommendation.flagged_tokens && 
                    data.recommendation.flagged_tokens.some(flaggedToken => 
                      token.toLowerCase().includes(flaggedToken.toLowerCase()) || 
                      flaggedToken.toLowerCase().includes(token.toLowerCase())
                    );
                  return `
                    <div class="ingredient-item">
                      <span class="ingredient-number ${isFlagged ? 'nogo' : 'healthy'}">${index + 1}</span>
                      <span class="ingredient-text">${token}</span>
                    </div>
                  `;
                }).join('')}
              </div>
            </div>
          </div>
        </div>
        
        <div id="comments-tab" class="tab-pane">
          <div class="comment-section">
            <div class="form-group">
              <textarea id="scanComment" class="form-control" placeholder="Add your thoughts about this scan..." rows="4" style="border-radius: 8px; border: 1px solid #ddd; padding: 0.75rem;" oninput="autoSaveComment()"></textarea>
            </div>
            <div id="commentStatus" class="mt-2 text-center" style="display: none;"></div>
          </div>
        </div>
      </div>
    </div>
  `;
  
  results.innerHTML = html;
  
  // Add click handlers to ingredient items
  addIngredientClickHandlers();
}


// Separate function for Scan/Recommendation tabs
function switchScanTab(tabName, event) {
  // Get the parent card to limit scope
  const parentCard = event.target.closest('.tabbed-result-card');
  
  // Remove active class from scan tab buttons only
  const scanTabButtons = parentCard.querySelectorAll('.tab-header .tab-button');
  scanTabButtons.forEach(button => button.classList.remove('active'));
  
  // Remove active class from scan tab panes only
  const scanTabPanes = parentCard.querySelectorAll('.tab-pane');
  scanTabPanes.forEach(pane => pane.classList.remove('active'));
  
  // Add active class to clicked tab button
  if (event && event.target) {
    event.target.classList.add('active');
  }
  
  // Show corresponding tab pane
  const targetTab = document.getElementById(`${tabName}-tab`);
  if (targetTab) {
    targetTab.classList.add('active');
  }
}

// Separate function for Details/Ingredients/Comments tabs
function switchAnalysisTab(tabName, event) {
  // Get the parent card to limit scope
  const parentCard = event.target.closest('.tabbed-result-card');
  
  // Remove active class from analysis tab buttons only
  const analysisTabButtons = parentCard.querySelectorAll('.tab-header .tab-button');
  analysisTabButtons.forEach(button => button.classList.remove('active'));
  
  // Remove active class from analysis tab panes only
  const analysisTabPanes = parentCard.querySelectorAll('.tab-pane');
  analysisTabPanes.forEach(pane => pane.classList.remove('active'));
  
  // Add active class to clicked tab button
  if (event && event.target) {
    event.target.classList.add('active');
  }
  
  // Show corresponding tab pane
  const targetTab = document.getElementById(`${tabName}-tab`);
  if (targetTab) {
    targetTab.classList.add('active');
  }
}

// Legacy function for backward compatibility (scan detail page)
function switchTab(tabName, event) {
  // Remove active class from all tab buttons in the same parent
  const parentCard = event.target.closest('.tabbed-result-card');
  const tabButtons = parentCard.querySelectorAll('.tab-header .tab-button');
  tabButtons.forEach(button => button.classList.remove('active'));
  
  // Remove active class from all tab panes in the same parent
  const tabPanes = parentCard.querySelectorAll('.tab-pane');
  tabPanes.forEach(pane => pane.classList.remove('active'));
  
  // Add active class to clicked tab button
  if (event && event.target) {
    event.target.classList.add('active');
  }
  
  // Show corresponding tab pane
  const targetTab = document.getElementById(`${tabName}-tab`);
  if (targetTab) {
    targetTab.classList.add('active');
  }
}

function showError(message) {
  error.textContent = message;
  error.style.display = 'block';
}

function showNotFoodProductMessage(title, description) {
  // Hide error div and show the message in results instead
  error.style.display = 'none';
  
  const notFoodProductHtml = `
    <div class="result-card">
      <div class="not-food-product-message">
        <div class="not-food-icon">
          🍽️
        </div>
        <h3 class="not-food-title">${title}</h3>
        <p class="not-food-description">${description}</p>
        <div class="not-food-action">
          <button class="btn-try-again" onclick="startNewScan()">
            📷 Try Again
          </button>
        </div>
      </div>
    </div>
  `;
  
  results.innerHTML = notFoodProductHtml;
}

function openCameraInput() {
  // Clear any existing results before opening camera
  results.innerHTML = '';
  error.style.display = 'none';
  lastResult = null;
  
  // Reset processing state in case user was in middle of a scan
  isProcessing = false;
  document.body.classList.remove('processing');
  
  cameraInput.click();
}

if (floatingCameraBtn) {
  floatingCameraBtn.addEventListener('click', openCameraInput);
}

// Add event listener for overlay Process Now button
if (overlayProcessBtn) {
  overlayProcessBtn.addEventListener('click', processImage);
}

// Modal functionality
function showIngredientModal(ingredientName) {
  modalIngredientName.textContent = ingredientName;
  
  // Show loading state
  modalContent.innerHTML = `
    <div class="ingredient-loading">
      <div class="ingredient-loading-spinner"></div>
      <span>Getting explanation...</span>
    </div>
  `;
  
  ingredientModal.style.display = 'block';
  
  // Check cache first
  if (explanationCache.has(ingredientName.toLowerCase())) {
    const cachedExplanation = explanationCache.get(ingredientName.toLowerCase());
    modalContent.innerHTML = `<p class="ingredient-explanation">${cachedExplanation}</p>`;
    return;
  }
  
  // Fetch explanation from API
  fetch('/api/ingredient-explanation', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ ingredient: ingredientName })
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      modalContent.innerHTML = `<div class="ingredient-error">Unable to get explanation: ${data.error}</div>`;
    } else {
      const explanation = data.explanation;
      explanationCache.set(ingredientName.toLowerCase(), explanation);
      modalContent.innerHTML = `<p class="ingredient-explanation">${explanation}</p>`;
    }
  })
  .catch(error => {
    console.error('Error fetching ingredient explanation:', error);
    modalContent.innerHTML = `<div class="ingredient-error">Unable to get explanation. Please try again.</div>`;
  });
}

function hideIngredientModal() {
  ingredientModal.style.display = 'none';
}

// Close modal when clicking the close button
closeModal.addEventListener('click', hideIngredientModal);

// Close modal when clicking outside the modal content
ingredientModal.addEventListener('click', function(event) {
  if (event.target === ingredientModal) {
    hideIngredientModal();
  }
});

// Close modal with Escape key
document.addEventListener('keydown', function(event) {
  if (event.key === 'Escape' && ingredientModal.style.display === 'block') {
    hideIngredientModal();
  }
});

// Add click handlers to ingredient items (will be called after results are displayed)
function addIngredientClickHandlers() {
  // Handle main scan interface ingredients
  document.querySelectorAll('.flagged-ingredient-item').forEach(item => {
    item.addEventListener('click', function() {
      const ingredientText = this.querySelector('.ingredient-flag-text').textContent.trim();
      showIngredientModal(ingredientText);
    });
  });
  
  // Handle dashboard ingredients (if on dashboard page)
  document.querySelectorAll('.dashboard-flagged-ingredient-item').forEach(item => {
    item.addEventListener('click', function() {
      const ingredientText = this.querySelector('.dashboard-ingredient-flag-text').textContent.trim();
      showIngredientModal(ingredientText);
    });
  });
}

// Auto-save comment with debouncing
let commentSaveTimeout;
function autoSaveComment() {
  const commentText = document.getElementById('scanComment').value.trim();
  const statusDiv = document.getElementById('commentStatus');
  
  // Clear previous timeout
  if (commentSaveTimeout) {
    clearTimeout(commentSaveTimeout);
  }
  
  // Don't save if empty or no scan data
  if (!commentText || !lastResult || !lastResult.scan_id) {
    return;
  }
  
  // Show typing status
  statusDiv.innerHTML = '<small class="text-muted">Typing...</small>';
  statusDiv.style.display = 'block';
  
  // Debounce the save operation (wait 1 second after user stops typing)
  commentSaveTimeout = setTimeout(() => {
    saveScanCommentInternal(commentText, statusDiv);
  }, 1000);
}

// Internal save function
function saveScanCommentInternal(commentText, statusDiv) {
  statusDiv.innerHTML = '<small class="text-info">Saving...</small>';
  
  fetch('/api/save-comment', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      scan_id: lastResult.scan_id,
      comment: commentText
    })
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      statusDiv.innerHTML = '<small class="text-success">✓ Saved</small>';
      // Hide status after 2 seconds
      setTimeout(() => {
        statusDiv.style.display = 'none';
      }, 2000);
    } else {
      throw new Error(data.error || 'Failed to save comment');
    }
  })
  .catch(error => {
    console.error('Error saving comment:', error);
    statusDiv.innerHTML = '<small class="text-danger">Save failed</small>';
    // Hide status after 3 seconds
    setTimeout(() => {
      statusDiv.style.display = 'none';
    }, 3000);
  });
}

// Save scan comment function
function saveScanComment() {
  const commentText = document.getElementById('scanComment').value.trim();
  const saveBtn = document.getElementById('saveCommentBtn');
  const statusDiv = document.getElementById('commentStatus');
  
  if (!commentText) {
    statusDiv.innerHTML = '<small class="text-warning">Please enter a comment first</small>';
    statusDiv.style.display = 'block';
    return;
  }
  
  if (!lastResult || !lastResult.scan_id) {
    statusDiv.innerHTML = '<small class="text-danger">No scan data available to save comment</small>';
    statusDiv.style.display = 'block';
    return;
  }
  
  // Show saving state
  saveBtn.innerHTML = '💾 Saving...';
  saveBtn.disabled = true;
  statusDiv.style.display = 'none';
  
  // Send comment to server
  fetch('/api/save-comment', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      scan_id: lastResult.scan_id,
      comment: commentText
    })
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      statusDiv.innerHTML = '<small class="text-success">✅ Comment saved successfully!</small>';
      statusDiv.style.display = 'block';
      saveBtn.innerHTML = '✅ Saved';
      
      // Reset button after 2 seconds
      setTimeout(() => {
        saveBtn.innerHTML = '💾 Save Comment';
        saveBtn.disabled = false;
        document.getElementById('scanComment').value = '';
        statusDiv.style.display = 'none';
      }, 2000);
    } else {
      throw new Error(data.error || 'Failed to save comment');
    }
  })
  .catch(error => {
    console.error('Error saving comment:', error);
    statusDiv.innerHTML = '<small class="text-danger">❌ Failed to save comment</small>';
    statusDiv.style.display = 'block';
    saveBtn.innerHTML = '💾 Save Comment';
    saveBtn.disabled = false;
  });
} 