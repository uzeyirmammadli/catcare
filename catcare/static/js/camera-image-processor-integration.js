/**
 * Camera Image Processor Integration
 * Integrates camera capture with advanced image processing capabilities
 * Provides real-time processing preview and batch upload functionality
 */

class CameraImageProcessorIntegration {
    constructor(cameraCapture, imageProcessor, batchUploadManager, adaptiveProcessor, options = {}) {
        this.cameraCapture = cameraCapture;
        this.imageProcessor = imageProcessor;
        this.batchUploadManager = batchUploadManager;
        this.adaptiveProcessor = adaptiveProcessor;
        
        this.options = {
            // Processing options
            enableRealTimeProcessing: true,
            enableProcessingPreview: true,
            enableBatchCapture: true,
            
            // UI options
            showProcessingOptions: true,
            showCompressionLevel: true,
            showThumbnailGeneration: true,
            
            // Performance options
            previewUpdateInterval: 500, // ms
            maxPreviewSize: 300, // pixels
            
            ...options
        };
        
        // State management
        this.isProcessingEnabled = true;
        this.processingOptions = {};
        this.capturedMedia = [];
        this.processingQueue = [];
        
        // UI elements
        this.processingControls = null;
        this.processingPreview = null;
        this.batchProgress = null;
        
        // Initialize integration
        this._initializeIntegration();
    }

    /**
     * Initialize the integration between camera and processing components
     */
    _initializeIntegration() {
        // Set up event listeners for camera events
        this._setupCameraEventListeners();
        
        // Set up adaptive processing callbacks
        this._setupAdaptiveProcessing();
        
        // Set up batch upload callbacks
        this._setupBatchUploadCallbacks();
        
        // Initialize processing options from adaptive processor
        this._updateProcessingOptions();
    }

    /**
     * Enhance camera interface with processing options
     * @param {HTMLElement} container - Camera container element
     */
    enhanceCameraInterface(container) {
        if (!container) return;
        
        // Add processing controls to camera interface
        if (this.options.showProcessingOptions) {
            this._addProcessingControls(container);
        }
        
        // Add processing preview area
        if (this.options.enableProcessingPreview) {
            this._addProcessingPreview(container);
        }
        
        // Add batch progress indicator
        if (this.options.enableBatchCapture) {
            this._addBatchProgressIndicator(container);
        }
        
        // Update interface based on adaptive settings
        this._updateInterfaceForAdaptiveSettings();
    }

    /**
     * Process captured photo with real-time feedback
     * @param {Blob} photoBlob - Captured photo blob
     * @returns {Promise<Object>} Processing result
     */
    async processPhoto(photoBlob) {
        if (!this.isProcessingEnabled) {
            return { original: photoBlob, processed: photoBlob };
        }
        
        try {
            // Show processing indicator
            this._showProcessingIndicator('photo');
            
            // Get optimal processing settings
            const processingSettings = this.adaptiveProcessor.getOptimalSettings(this.processingOptions);
            
            // Create file object from blob
            const file = new File([photoBlob], `photo_${Date.now()}.jpg`, { type: 'image/jpeg' });
            
            // Process the image
            const result = await this.imageProcessor.processImage(file, processingSettings);
            
            // Update processing preview
            if (this.options.enableProcessingPreview) {
                this._updateProcessingPreview(result);
            }
            
            // Record performance for adaptive processing
            this.adaptiveProcessor.recordProcessingPerformance({
                processingTime: result.metadata.processingTime,
                originalSize: result.metadata.originalSize,
                compressionRatio: result.metadata.compressionRatio
            });
            
            // Hide processing indicator
            this._hideProcessingIndicator();
            
            return result;
            
        } catch (error) {
            console.error('Photo processing failed:', error);
            this._hideProcessingIndicator();
            this._showProcessingError(error);
            
            // Return original if processing fails
            return { original: photoBlob, processed: photoBlob, error: error.message };
        }
    }

    /**
     * Start batch capture mode with processing
     * @param {HTMLElement} container - Camera container
     */
    async startBatchCapture(container) {
        if (!this.options.enableBatchCapture) return;
        
        try {
            // Initialize batch capture UI
            this._initializeBatchCaptureUI(container);
            
            // Set up batch capture event listeners
            this._setupBatchCaptureListeners();
            
            // Show batch capture controls
            this._showBatchCaptureControls(container);
            
        } catch (error) {
            console.error('Batch capture initialization failed:', error);
            this._showError('Failed to initialize batch capture');
        }
    }

    /**
     * Upload captured media using batch upload manager
     * @param {Array} mediaItems - Array of captured media items
     * @param {Object} uploadOptions - Upload options
     */
    async uploadCapturedMedia(mediaItems, uploadOptions = {}) {
        if (!mediaItems || mediaItems.length === 0) return;
        
        try {
            // Convert media items to files
            const files = await this._convertMediaToFiles(mediaItems);
            
            // Set up batch upload callbacks
            this.batchUploadManager.setCallbacks({
                onProgress: (progress) => this._updateBatchProgress(progress),
                onFileComplete: (result) => this._onFileUploadComplete(result),
                onBatchComplete: (result) => this._onBatchUploadComplete(result),
                onError: (error) => this._onUploadError(error)
            });
            
            // Start batch upload with processing
            const result = await this.batchUploadManager.processBatch(files, {
                ...uploadOptions,
                ...this.adaptiveProcessor.getOptimalSettings()
            });
            
            return result;
            
        } catch (error) {
            console.error('Batch upload failed:', error);
            this._showError('Batch upload failed: ' + error.message);
            throw error;
        }
    }

    /**
     * Get processing options UI
     * @returns {HTMLElement} Processing options element
     */
    getProcessingOptionsUI() {
        const optionsContainer = document.createElement('div');
        optionsContainer.className = 'processing-options bg-white p-4 rounded-lg shadow-md mb-4';
        
        optionsContainer.innerHTML = `
            <h3 class="text-lg font-semibold mb-3">Processing Options</h3>
            
            <!-- Compression Level -->
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-2">
                    Compression Level
                </label>
                <div class="flex items-center space-x-4">
                    <input type="range" 
                           id="compressionLevel" 
                           min="0.3" 
                           max="1.0" 
                           step="0.1" 
                           value="0.8"
                           class="flex-1">
                    <span id="compressionValue" class="text-sm text-gray-600">80%</span>
                </div>
                <p class="text-xs text-gray-500 mt-1">Higher values = better quality, larger files</p>
            </div>
            
            <!-- Thumbnail Generation -->
            <div class="mb-4">
                <label class="flex items-center">
                    <input type="checkbox" 
                           id="enableThumbnails" 
                           checked
                           class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50">
                    <span class="ml-2 text-sm text-gray-700">Generate thumbnails</span>
                </label>
            </div>
            
            <!-- Real-time Processing -->
            <div class="mb-4">
                <label class="flex items-center">
                    <input type="checkbox" 
                           id="enableRealTimeProcessing" 
                           checked
                           class="rounded border-gray-300 text-blue-600 shadow-sm focus:border-blue-300 focus:ring focus:ring-blue-200 focus:ring-opacity-50">
                    <span class="ml-2 text-sm text-gray-700">Real-time processing</span>
                </label>
            </div>
            
            <!-- Adaptive Settings Info -->
            <div class="bg-blue-50 p-3 rounded-md">
                <h4 class="text-sm font-medium text-blue-800 mb-1">Adaptive Settings</h4>
                <p id="adaptiveSettingsInfo" class="text-xs text-blue-600"></p>
            </div>
        `;
        
        // Set up event listeners for options
        this._setupProcessingOptionsListeners(optionsContainer);
        
        return optionsContainer;
    }

    // Private methods

    _setupCameraEventListeners() {
        // Listen for photo captured events
        document.addEventListener('photo:captured', async (event) => {
            const media = event.detail.media;
            
            if (this.isProcessingEnabled) {
                try {
                    const processedResult = await this.processPhoto(media.blob);
                    
                    // Update the captured media with processed version
                    media.processedBlob = processedResult.processed;
                    media.thumbnail = processedResult.thumbnail;
                    media.metadata = processedResult.metadata;
                    
                    // Emit processed photo event
                    const processedEvent = new CustomEvent('photo:processed', {
                        detail: { media, processedResult }
                    });
                    document.dispatchEvent(processedEvent);
                    
                } catch (error) {
                    console.error('Photo processing failed:', error);
                }
            }
        });
        
        // Listen for video captured events
        document.addEventListener('video:captured', async (event) => {
            const media = event.detail.media;
            
            // For now, videos are not processed client-side
            // This could be extended in the future
            console.log('Video captured:', media);
        });
        
        // Listen for camera state changes
        document.addEventListener('camera:initialized', (event) => {
            this._onCameraInitialized(event.detail);
        });
        
        document.addEventListener('camera:photo-ready', (event) => {
            this._onCameraReady('photo', event.detail);
        });
        
        document.addEventListener('camera:video-ready', (event) => {
            this._onCameraReady('video', event.detail);
        });
    }

    _setupAdaptiveProcessing() {
        // Listen for adaptation changes
        this.adaptiveProcessor.onAdaptationChange((changeInfo) => {
            console.log('Processing adapted:', changeInfo);
            this._updateProcessingOptions();
            this._updateInterfaceForAdaptiveSettings();
            this._showAdaptationNotification(changeInfo);
        });
        
        // Update processing options based on current adaptive settings
        this._updateProcessingOptions();
    }

    _setupBatchUploadCallbacks() {
        // Set default callbacks for batch upload manager
        this.batchUploadManager.setCallbacks({
            onProgress: (progress) => {
                console.log('Batch upload progress:', progress);
                this._updateBatchProgress(progress);
            },
            onFileProgress: (fileProgress) => {
                console.log('File progress:', fileProgress);
                this._updateFileProgress(fileProgress);
            },
            onFileComplete: (result) => {
                console.log('File upload complete:', result);
                this._onFileUploadComplete(result);
            },
            onBatchComplete: (result) => {
                console.log('Batch upload complete:', result);
                this._onBatchUploadComplete(result);
            },
            onError: (error) => {
                console.error('Upload error:', error);
                this._onUploadError(error);
            }
        });
    }

    _updateProcessingOptions() {
        const adaptiveSettings = this.adaptiveProcessor.getOptimalSettings();
        
        this.processingOptions = {
            quality: adaptiveSettings.quality,
            maxWidth: adaptiveSettings.maxWidth,
            maxHeight: adaptiveSettings.maxHeight,
            compressionThreshold: adaptiveSettings.compressionThreshold,
            useWebWorkers: adaptiveSettings.useWebWorkers,
            maxConcurrent: adaptiveSettings.maxConcurrent
        };
    }

    _addProcessingControls(container) {
        const controlsContainer = document.createElement('div');
        controlsContainer.className = 'processing-controls-container';
        
        const processingOptionsUI = this.getProcessingOptionsUI();
        controlsContainer.appendChild(processingOptionsUI);
        
        // Insert controls at the top of camera interface
        const firstChild = container.firstChild;
        if (firstChild) {
            container.insertBefore(controlsContainer, firstChild);
        } else {
            container.appendChild(controlsContainer);
        }
        
        this.processingControls = controlsContainer;
    }

    _addProcessingPreview(container) {
        const previewContainer = document.createElement('div');
        previewContainer.className = 'processing-preview-container bg-gray-50 p-4 rounded-lg mb-4 hidden';
        
        previewContainer.innerHTML = `
            <h4 class="text-md font-medium text-gray-800 mb-2">Processing Preview</h4>
            <div class="grid grid-cols-2 gap-4">
                <div class="text-center">
                    <p class="text-sm text-gray-600 mb-2">Original</p>
                    <div id="originalPreview" class="bg-white border-2 border-dashed border-gray-300 rounded-lg h-32 flex items-center justify-center">
                        <span class="text-gray-400">No image</span>
                    </div>
                    <p id="originalSize" class="text-xs text-gray-500 mt-1">-</p>
                </div>
                <div class="text-center">
                    <p class="text-sm text-gray-600 mb-2">Processed</p>
                    <div id="processedPreview" class="bg-white border-2 border-dashed border-gray-300 rounded-lg h-32 flex items-center justify-center">
                        <span class="text-gray-400">No image</span>
                    </div>
                    <p id="processedSize" class="text-xs text-gray-500 mt-1">-</p>
                </div>
            </div>
            <div class="mt-3 text-center">
                <p id="compressionInfo" class="text-sm text-green-600"></p>
            </div>
        `;
        
        container.appendChild(previewContainer);
        this.processingPreview = previewContainer;
    }

    _addBatchProgressIndicator(container) {
        const progressContainer = document.createElement('div');
        progressContainer.className = 'batch-progress-container bg-blue-50 p-4 rounded-lg mb-4 hidden';
        
        progressContainer.innerHTML = `
            <h4 class="text-md font-medium text-blue-800 mb-2">Batch Upload Progress</h4>
            <div class="space-y-2">
                <div class="flex justify-between text-sm">
                    <span id="batchStatus">Ready</span>
                    <span id="batchProgress">0/0</span>
                </div>
                <div class="w-full bg-blue-200 rounded-full h-2">
                    <div id="batchProgressBar" class="bg-blue-600 h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
                </div>
                <div id="batchDetails" class="text-xs text-blue-600"></div>
            </div>
        `;
        
        container.appendChild(progressContainer);
        this.batchProgress = progressContainer;
    }

    _setupProcessingOptionsListeners(optionsContainer) {
        // Compression level slider
        const compressionSlider = optionsContainer.querySelector('#compressionLevel');
        const compressionValue = optionsContainer.querySelector('#compressionValue');
        
        compressionSlider.addEventListener('input', (e) => {
            const value = parseFloat(e.target.value);
            compressionValue.textContent = Math.round(value * 100) + '%';
            this.processingOptions.quality = value;
        });
        
        // Thumbnail generation checkbox
        const thumbnailCheckbox = optionsContainer.querySelector('#enableThumbnails');
        thumbnailCheckbox.addEventListener('change', (e) => {
            this.processingOptions.generateThumbnails = e.target.checked;
        });
        
        // Real-time processing checkbox
        const realTimeCheckbox = optionsContainer.querySelector('#enableRealTimeProcessing');
        realTimeCheckbox.addEventListener('change', (e) => {
            this.isProcessingEnabled = e.target.checked;
        });
        
        // Update adaptive settings info
        this._updateAdaptiveSettingsInfo(optionsContainer);
    }

    _updateInterfaceForAdaptiveSettings() {
        const adaptiveSettings = this.adaptiveProcessor.getOptimalSettings();
        const adaptationMessage = this.adaptiveProcessor.getAdaptationMessage();
        
        // Update adaptive settings info if it exists
        const adaptiveInfo = document.querySelector('#adaptiveSettingsInfo');
        if (adaptiveInfo) {
            adaptiveInfo.textContent = adaptationMessage;
        }
        
        // Update compression slider if it exists
        const compressionSlider = document.querySelector('#compressionLevel');
        const compressionValue = document.querySelector('#compressionValue');
        if (compressionSlider && compressionValue) {
            compressionSlider.value = adaptiveSettings.quality;
            compressionValue.textContent = Math.round(adaptiveSettings.quality * 100) + '%';
        }
    }

    _updateAdaptiveSettingsInfo(optionsContainer) {
        const adaptiveInfo = optionsContainer.querySelector('#adaptiveSettingsInfo');
        if (adaptiveInfo) {
            const message = this.adaptiveProcessor.getAdaptationMessage();
            adaptiveInfo.textContent = message;
        }
    }

    _showProcessingIndicator(type) {
        // Show processing indicator in the camera interface
        const indicator = document.createElement('div');
        indicator.className = 'processing-indicator absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
        indicator.innerHTML = `
            <div class="bg-white rounded-lg p-4 text-center">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
                <p class="text-sm text-gray-700">Processing ${type}...</p>
            </div>
        `;
        
        const container = document.querySelector('.camera-capture-container');
        if (container) {
            container.appendChild(indicator);
        }
    }

    _hideProcessingIndicator() {
        const indicator = document.querySelector('.processing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    _updateProcessingPreview(result) {
        if (!this.processingPreview || this.processingPreview.classList.contains('hidden')) {
            return;
        }
        
        const originalPreview = this.processingPreview.querySelector('#originalPreview');
        const processedPreview = this.processingPreview.querySelector('#processedPreview');
        const originalSize = this.processingPreview.querySelector('#originalSize');
        const processedSize = this.processingPreview.querySelector('#processedSize');
        const compressionInfo = this.processingPreview.querySelector('#compressionInfo');
        
        // Create preview images
        const originalImg = document.createElement('img');
        originalImg.src = URL.createObjectURL(result.original);
        originalImg.className = 'max-w-full max-h-full object-contain';
        originalPreview.innerHTML = '';
        originalPreview.appendChild(originalImg);
        
        const processedImg = document.createElement('img');
        processedImg.src = URL.createObjectURL(result.processed);
        processedImg.className = 'max-w-full max-h-full object-contain';
        processedPreview.innerHTML = '';
        processedPreview.appendChild(processedImg);
        
        // Update size information
        originalSize.textContent = this._formatFileSize(result.metadata.originalSize);
        processedSize.textContent = this._formatFileSize(result.metadata.processedSize);
        
        // Update compression info
        const compressionRatio = result.metadata.compressionRatio;
        const savings = Math.round((1 - 1/compressionRatio) * 100);
        compressionInfo.textContent = `${savings}% size reduction (${compressionRatio.toFixed(1)}x compression)`;
        
        // Show preview
        this.processingPreview.classList.remove('hidden');
    }

    _showProcessingError(error) {
        const errorContainer = document.createElement('div');
        errorContainer.className = 'processing-error bg-red-50 border border-red-200 rounded-lg p-3 mb-4';
        errorContainer.innerHTML = `
            <div class="flex items-center">
                <svg class="w-5 h-5 text-red-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                </svg>
                <p class="text-sm text-red-700">Processing failed: ${error.message}</p>
            </div>
        `;
        
        const container = document.querySelector('.camera-capture-container');
        if (container) {
            container.insertBefore(errorContainer, container.firstChild);
            
            // Remove error after 5 seconds
            setTimeout(() => {
                if (errorContainer.parentNode) {
                    errorContainer.remove();
                }
            }, 5000);
        }
    }

    _showAdaptationNotification(changeInfo) {
        const notification = document.createElement('div');
        notification.className = 'adaptation-notification fixed top-4 right-4 bg-blue-500 text-white p-3 rounded-lg shadow-lg z-50 max-w-sm';
        notification.innerHTML = `
            <div class="flex items-center">
                <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
                </svg>
                <div>
                    <p class="text-sm font-medium">Settings Adapted</p>
                    <p class="text-xs">Switched to ${changeInfo.newProfile} profile</p>
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Remove notification after 4 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 4000);
    }

    _updateBatchProgress(progress) {
        if (!this.batchProgress) return;
        
        const statusElement = this.batchProgress.querySelector('#batchStatus');
        const progressElement = this.batchProgress.querySelector('#batchProgress');
        const progressBar = this.batchProgress.querySelector('#batchProgressBar');
        const detailsElement = this.batchProgress.querySelector('#batchDetails');
        
        statusElement.textContent = progress.status.charAt(0).toUpperCase() + progress.status.slice(1);
        progressElement.textContent = `${progress.completedFiles}/${progress.totalFiles}`;
        progressBar.style.width = `${(progress.progress * 100)}%`;
        
        const details = [];
        if (progress.processedSize > 0) {
            details.push(`Processed: ${this._formatFileSize(progress.processedSize)}`);
        }
        if (progress.uploadedSize > 0) {
            details.push(`Uploaded: ${this._formatFileSize(progress.uploadedSize)}`);
        }
        if (progress.errors > 0) {
            details.push(`Errors: ${progress.errors}`);
        }
        
        detailsElement.textContent = details.join(' • ');
        
        // Show progress container
        this.batchProgress.classList.remove('hidden');
    }

    _onFileUploadComplete(result) {
        console.log('File upload completed:', result);
        // Could show individual file completion feedback
    }

    _onBatchUploadComplete(result) {
        console.log('Batch upload completed:', result);
        
        // Show completion notification
        const notification = document.createElement('div');
        notification.className = 'batch-complete-notification fixed top-4 right-4 bg-green-500 text-white p-4 rounded-lg shadow-lg z-50 max-w-md';
        notification.innerHTML = `
            <div class="flex items-center">
                <svg class="w-6 h-6 mr-3" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                </svg>
                <div>
                    <p class="font-medium">Upload Complete!</p>
                    <p class="text-sm">
                        ${result.successfulFiles}/${result.totalFiles} files uploaded
                        ${result.compressionRatio > 1 ? ` • ${Math.round((1 - 1/result.compressionRatio) * 100)}% size reduction` : ''}
                    </p>
                </div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Remove notification after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
        
        // Hide batch progress
        if (this.batchProgress) {
            this.batchProgress.classList.add('hidden');
        }
    }

    _onUploadError(error) {
        console.error('Upload error:', error);
        this._showError(`Upload failed: ${error.error}`);
    }

    _showError(message) {
        const errorNotification = document.createElement('div');
        errorNotification.className = 'error-notification fixed top-4 right-4 bg-red-500 text-white p-3 rounded-lg shadow-lg z-50 max-w-sm';
        errorNotification.innerHTML = `
            <div class="flex items-center">
                <svg class="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                </svg>
                <p class="text-sm">${message}</p>
            </div>
        `;
        
        document.body.appendChild(errorNotification);
        
        // Remove notification after 5 seconds
        setTimeout(() => {
            if (errorNotification.parentNode) {
                errorNotification.remove();
            }
        }, 5000);
    }

    _convertMediaToFiles(mediaItems) {
        return Promise.all(mediaItems.map(async (media, index) => {
            const blob = media.processedBlob || media.blob;
            const filename = `captured_${media.type}_${index + 1}.${media.type === 'photo' ? 'jpg' : 'webm'}`;
            const mimeType = media.type === 'photo' ? 'image/jpeg' : 'video/webm';
            
            return new File([blob], filename, { type: mimeType });
        }));
    }

    _formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    _onCameraInitialized(detail) {
        console.log('Camera initialized with processing integration:', detail);
    }

    _onCameraReady(type, detail) {
        console.log(`Camera ready for ${type} with processing:`, detail);
        
        // Update interface when camera is ready
        this._updateInterfaceForAdaptiveSettings();
    }

    _initializeBatchCaptureUI(container) {
        // Add batch capture specific UI elements
        const batchControls = document.createElement('div');
        batchControls.className = 'batch-capture-controls bg-yellow-50 p-3 rounded-lg mb-4';
        batchControls.innerHTML = `
            <div class="flex items-center justify-between">
                <div>
                    <h4 class="text-sm font-medium text-yellow-800">Batch Capture Mode</h4>
                    <p class="text-xs text-yellow-600">Capture multiple photos quickly</p>
                </div>
                <div class="flex space-x-2">
                    <button id="finishBatchBtn" class="bg-green-500 text-white px-3 py-1 rounded text-sm hover:bg-green-600">
                        Finish & Upload
                    </button>
                    <button id="cancelBatchBtn" class="bg-gray-500 text-white px-3 py-1 rounded text-sm hover:bg-gray-600">
                        Cancel
                    </button>
                </div>
            </div>
            <div class="mt-2">
                <p class="text-xs text-yellow-600">Captured: <span id="batchCount">0</span> photos</p>
            </div>
        `;
        
        container.insertBefore(batchControls, container.firstChild);
    }

    _setupBatchCaptureListeners() {
        // Finish batch button
        document.getElementById('finishBatchBtn')?.addEventListener('click', async () => {
            if (this.capturedMedia.length > 0) {
                await this.uploadCapturedMedia(this.capturedMedia);
                this.capturedMedia = [];
                this._updateBatchCount();
            }
        });
        
        // Cancel batch button
        document.getElementById('cancelBatchBtn')?.addEventListener('click', () => {
            this.capturedMedia = [];
            this._updateBatchCount();
            this._hideBatchCaptureControls();
        });
        
        // Listen for photo captures in batch mode
        document.addEventListener('photo:processed', (event) => {
            this.capturedMedia.push(event.detail.media);
            this._updateBatchCount();
        });
    }

    _showBatchCaptureControls(container) {
        const controls = container.querySelector('.batch-capture-controls');
        if (controls) {
            controls.classList.remove('hidden');
        }
    }

    _hideBatchCaptureControls() {
        const controls = document.querySelector('.batch-capture-controls');
        if (controls) {
            controls.classList.add('hidden');
        }
    }

    _updateBatchCount() {
        const countElement = document.getElementById('batchCount');
        if (countElement) {
            countElement.textContent = this.capturedMedia.length;
        }
    }

    _updateFileProgress(fileProgress) {
        // Could implement individual file progress indicators
        console.log('File progress update:', fileProgress);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CameraImageProcessorIntegration;
}