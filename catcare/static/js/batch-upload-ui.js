/**
 * Batch Upload UI Manager
 * Provides a comprehensive user interface for batch file uploads with progress tracking
 * Enhanced with accessibility features and performance optimizations
 */

class BatchUploadUI {
    constructor(options = {}) {
        this.options = {
            maxFiles: 20,
            maxFileSize: 50 * 1024 * 1024, // 50MB
            supportedTypes: ['image/*', 'video/*'],
            uploadEndpoint: '/api/media/upload',
            enableAccessibility: true,
            enableAnimations: true,
            enableKeyboardNavigation: true,
            announceProgress: true,
            ...options
        };

        // State management
        this.selectedFiles = [];
        this.batchManager = null;
        this.imageProcessor = null;
        this.currentBatchId = null;
        this.fileProgressMap = new Map();
        this.failedFiles = [];
        this.isVisible = false;
        this.isProcessing = false;
        this.isPaused = false;

        // UI elements
        this.modal = null;
        this.elements = {};

        // Accessibility features
        this.announcer = null;
        this.focusManager = null;
        this.keyboardHandler = null;

        // Performance optimization
        this.updateThrottleMap = new Map();
        this.animationFrameId = null;

        // Initialize
        this.init();
    }

    /**
     * Initialize the batch upload UI
     */
    async init() {
        try {
            // Initialize ImageProcessor if available
            if (window.ImageProcessor) {
                this.imageProcessor = new ImageProcessor();
            }

            // Initialize BatchUploadManager if available
            if (window.BatchUploadManager && this.imageProcessor) {
                this.batchManager = new BatchUploadManager(this.imageProcessor, {
                    uploadEndpoint: this.options.uploadEndpoint,
                    maxConcurrentUploads: 3,
                    maxConcurrentProcessing: 3
                });

                // Set up batch manager callbacks
                this.batchManager.setCallbacks({
                    onProgress: this.throttledHandleBatchProgress.bind(this),
                    onFileProgress: this.throttledHandleFileProgress.bind(this),
                    onFileComplete: this.handleFileComplete.bind(this),
                    onBatchComplete: this.handleBatchComplete.bind(this),
                    onError: this.handleError.bind(this)
                });
            }

            this.setupUI();
            this.bindEvents();
            this.initializeAccessibility();
            this.setupPerformanceOptimizations();

            console.log('BatchUploadUI initialized successfully');
        } catch (error) {
            console.error('BatchUploadUI initialization failed:', error);
        }
    }

    /**
     * Initialize accessibility features
     */
    initializeAccessibility() {
        if (!this.options.enableAccessibility) return;

        // Create screen reader announcer
        this.announcer = this.createScreenReaderAnnouncer();

        // Initialize focus management
        this.focusManager = new FocusManager(this.modal);

        // Setup keyboard navigation
        if (this.options.enableKeyboardNavigation) {
            this.keyboardHandler = new KeyboardHandler(this);
        }

        // Add ARIA labels and descriptions
        this.enhanceAccessibility();
    }

    /**
     * Create screen reader announcer element
     */
    createScreenReaderAnnouncer() {
        const announcer = document.createElement('div');
        announcer.setAttribute('aria-live', 'polite');
        announcer.setAttribute('aria-atomic', 'true');
        announcer.className = 'sr-only';
        announcer.id = 'batch-upload-announcer';
        document.body.appendChild(announcer);
        return announcer;
    }

    /**
     * Enhance accessibility with ARIA attributes
     */
    enhanceAccessibility() {
        if (!this.modal) return;

        // Modal accessibility
        this.modal.setAttribute('role', 'dialog');
        this.modal.setAttribute('aria-modal', 'true');
        this.modal.setAttribute('aria-labelledby', 'batch-upload-title');
        this.modal.setAttribute('aria-describedby', 'batch-upload-description');

        // Add title and description if not present
        if (!document.getElementById('batch-upload-title')) {
            const title = document.createElement('h2');
            title.id = 'batch-upload-title';
            title.className = 'sr-only';
            title.textContent = 'Batch File Upload';
            this.modal.appendChild(title);
        }

        if (!document.getElementById('batch-upload-description')) {
            const description = document.createElement('div');
            description.id = 'batch-upload-description';
            description.className = 'sr-only';
            description.textContent = 'Upload multiple files with progress tracking and processing options';
            this.modal.appendChild(description);
        }

        // Enhance form controls
        this.enhanceFormAccessibility();
    }

    /**
     * Enhance form accessibility
     */
    enhanceFormAccessibility() {
        // File input accessibility
        if (this.elements.fileInput) {
            this.elements.fileInput.setAttribute('aria-describedby', 'file-input-help');
            
            if (!document.getElementById('file-input-help')) {
                const help = document.createElement('div');
                help.id = 'file-input-help';
                help.className = 'sr-only';
                help.textContent = `Select up to ${this.options.maxFiles} files. Maximum file size: ${this.formatFileSize(this.options.maxFileSize)}`;
                this.elements.fileInput.parentNode.appendChild(help);
            }
        }

        // Drop zone accessibility
        if (this.elements.dropZone) {
            this.elements.dropZone.setAttribute('role', 'button');
            this.elements.dropZone.setAttribute('tabindex', '0');
            this.elements.dropZone.setAttribute('aria-label', 'Drop files here or click to select files');
            this.elements.dropZone.setAttribute('aria-describedby', 'drop-zone-help');

            if (!document.getElementById('drop-zone-help')) {
                const help = document.createElement('div');
                help.id = 'drop-zone-help';
                help.className = 'sr-only';
                help.textContent = 'Drag and drop files here, or press Enter or Space to open file selector';
                this.elements.dropZone.appendChild(help);
            }
        }

        // Progress bars accessibility
        this.enhanceProgressBarsAccessibility();
    }

    /**
     * Enhance progress bars with accessibility
     */
    enhanceProgressBarsAccessibility() {
        const progressBars = [
            { bar: this.elements.overallProgressBar, text: this.elements.overallProgressText, label: 'Overall progress' },
            { bar: this.elements.uploadProgressBar, text: this.elements.uploadProgressText, label: 'Upload progress' }
        ];

        progressBars.forEach(({ bar, text, label }) => {
            if (bar) {
                bar.setAttribute('role', 'progressbar');
                bar.setAttribute('aria-label', label);
                bar.setAttribute('aria-valuemin', '0');
                bar.setAttribute('aria-valuemax', '100');
                bar.setAttribute('aria-valuenow', '0');
                
                if (text) {
                    bar.setAttribute('aria-describedby', text.id || `${label.toLowerCase().replace(' ', '-')}-text`);
                }
            }
        });
    }

    /**
     * Setup performance optimizations
     */
    setupPerformanceOptimizations() {
        // Throttle progress updates to prevent UI blocking
        this.throttledHandleBatchProgress = this.throttle(this.handleBatchProgress.bind(this), 100);
        this.throttledHandleFileProgress = this.throttle(this.handleFileProgress.bind(this), 50);

        // Setup intersection observer for lazy loading
        this.setupIntersectionObserver();

        // Setup resize observer for responsive updates
        this.setupResizeObserver();
    }

    /**
     * Setup intersection observer for performance
     */
    setupIntersectionObserver() {
        if (!window.IntersectionObserver) return;

        this.intersectionObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('visible');
                } else {
                    entry.target.classList.remove('visible');
                }
            });
        }, { threshold: 0.1 });
    }

    /**
     * Setup resize observer for responsive behavior
     */
    setupResizeObserver() {
        if (!window.ResizeObserver) return;

        this.resizeObserver = new ResizeObserver((entries) => {
            this.handleResize();
        });

        if (this.modal) {
            this.resizeObserver.observe(this.modal);
        }
    }

    /**
     * Handle resize events
     */
    handleResize() {
        // Adjust UI for different screen sizes
        if (window.innerWidth < 768) {
            this.modal?.classList.add('mobile-layout');
        } else {
            this.modal?.classList.remove('mobile-layout');
        }
    }

    /**
     * Throttle function to limit execution frequency
     */
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    }

    /**
     * Announce message to screen readers
     */
    announce(message, priority = 'polite') {
        if (!this.announcer || !this.options.announceProgress) return;

        this.announcer.setAttribute('aria-live', priority);
        this.announcer.textContent = message;

        // Clear after announcement
        setTimeout(() => {
            if (this.announcer) {
                this.announcer.textContent = '';
            }
        }, 1000);
    }

    /**
     * Set up UI elements
     */
    setupUI() {
        this.modal = document.getElementById('batchUploadModal');
        if (!this.modal) {
            console.error('Batch upload modal not found');
            return;
        }

        // Cache UI elements
        this.elements = {
            // File selection
            dropZone: document.getElementById('dropZone'),
            selectFilesBtn: document.getElementById('selectFilesBtn'),
            fileInput: document.getElementById('batchFileInput'),
            selectedFilesSection: document.getElementById('selectedFilesSection'),
            selectedFilesList: document.getElementById('selectedFilesList'),
            clearAllFiles: document.getElementById('clearAllFiles'),

            // Processing options
            processingOptions: document.getElementById('processingOptions'),
            compressionQuality: document.getElementById('compressionQuality'),
            maxConcurrentUploads: document.getElementById('maxConcurrentUploads'),
            maxProcessingThreads: document.getElementById('maxProcessingThreads'),

            // Batch controls
            batchControls: document.getElementById('batchControls'),
            startBatchBtn: document.getElementById('startBatchBtn'),
            pauseBatchBtn: document.getElementById('pauseBatchBtn'),
            resumeBatchBtn: document.getElementById('resumeBatchBtn'),
            cancelBatchBtn: document.getElementById('cancelBatchBtn'),

            // Progress overview
            progressOverview: document.getElementById('progressOverview'),
            overallProgressText: document.getElementById('overallProgressText'),
            overallProgressBar: document.getElementById('overallProgressBar'),
            uploadProgressText: document.getElementById('uploadProgressText'),
            uploadProgressBar: document.getElementById('uploadProgressBar'),
            totalFilesCount: document.getElementById('totalFilesCount'),
            completedFilesCount: document.getElementById('completedFilesCount'),
            uploadedFilesCount: document.getElementById('uploadedFilesCount'),
            errorFilesCount: document.getElementById('errorFilesCount'),

            // File progress
            fileProgressSection: document.getElementById('fileProgressSection'),
            toggleFileProgress: document.getElementById('toggleFileProgress'),
            fileProgressList: document.getElementById('fileProgressList'),

            // Error handling
            errorSection: document.getElementById('errorSection'),
            retryFailedBtn: document.getElementById('retryFailedBtn'),
            errorList: document.getElementById('errorList'),

            // Results
            batchResults: document.getElementById('batchResults'),
            successfulUploads: document.getElementById('successfulUploads'),
            spaceSaved: document.getElementById('spaceSaved'),
            totalTime: document.getElementById('totalTime'),
            avgCompressionRatio: document.getElementById('avgCompressionRatio'),

            // Actions
            closeBatchUpload: document.getElementById('closeBatchUpload'),
            closeBatchUploadBtn: document.getElementById('closeBatchUploadBtn'),
            addToFormBtn: document.getElementById('addToFormBtn')
        };
    }

    /**
     * Bind event listeners
     */
    bindEvents() {
        if (!this.elements.dropZone) return;

        // File selection events
        this.elements.selectFilesBtn?.addEventListener('click', () => {
            this.elements.fileInput?.click();
        });

        this.elements.fileInput?.addEventListener('change', (e) => {
            this.handleFileSelection(Array.from(e.target.files));
        });

        this.elements.clearAllFiles?.addEventListener('click', () => {
            this.clearAllFiles();
        });

        // Drag and drop events
        this.elements.dropZone.addEventListener('dragover', this.handleDragOver.bind(this));
        this.elements.dropZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.elements.dropZone.addEventListener('drop', this.handleDrop.bind(this));

        // Batch control events
        this.elements.startBatchBtn?.addEventListener('click', this.startBatch.bind(this));
        this.elements.pauseBatchBtn?.addEventListener('click', this.pauseBatch.bind(this));
        this.elements.resumeBatchBtn?.addEventListener('click', this.resumeBatch.bind(this));
        this.elements.cancelBatchBtn?.addEventListener('click', this.cancelBatch.bind(this));

        // UI control events
        this.elements.toggleFileProgress?.addEventListener('click', this.toggleFileProgressDetails.bind(this));
        this.elements.retryFailedBtn?.addEventListener('click', this.retryFailedFiles.bind(this));

        // Modal close events
        this.elements.closeBatchUpload?.addEventListener('click', this.hide.bind(this));
        this.elements.closeBatchUploadBtn?.addEventListener('click', this.hide.bind(this));
        this.elements.addToFormBtn?.addEventListener('click', this.addToForm.bind(this));

        // Processing option changes
        this.elements.compressionQuality?.addEventListener('change', this.updateProcessingOptions.bind(this));
        this.elements.maxConcurrentUploads?.addEventListener('change', this.updateProcessingOptions.bind(this));
        this.elements.maxProcessingThreads?.addEventListener('change', this.updateProcessingOptions.bind(this));

        // Close modal when clicking outside
        this.modal?.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });
    }

    /**
     * Show the batch upload modal
     */
    show() {
        if (this.modal) {
            this.modal.classList.remove('hidden');
            this.isVisible = true;
            this.resetUI();
            
            // Initialize focus management
            if (this.focusManager) {
                this.focusManager.initialize();
            }
            
            // Announce modal opening
            this.announce('Batch upload dialog opened');
            
            // Add animation class if enabled
            if (this.options.enableAnimations) {
                this.modal.classList.add('fade-in');
                setTimeout(() => {
                    this.modal.classList.remove('fade-in');
                }, 300);
            }
            
            // Handle responsive layout
            this.handleResize();
        }
    }

    /**
     * Hide the batch upload modal
     */
    hide() {
        if (this.modal) {
            // Confirm if processing is ongoing
            if (this.isProcessing && !this.isPaused) {
                const confirmClose = confirm('Upload is in progress. Are you sure you want to close?');
                if (!confirmClose) {
                    return;
                }
            }
            
            this.modal.classList.add('hidden');
            this.isVisible = false;
            
            // Cancel any ongoing batch if user closes modal
            if (this.currentBatchId && this.batchManager) {
                this.batchManager.cancelBatch(this.currentBatchId);
            }
            
            // Restore focus
            if (this.focusManager) {
                this.focusManager.restore();
            }
            
            // Announce modal closing
            this.announce('Batch upload dialog closed');
            
            // Clean up
            this.cleanup();
        }
    }

    /**
     * Clean up resources when hiding modal
     */
    cleanup() {
        // Cancel any pending animation frames
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        
        // Clear throttle timers
        this.updateThrottleMap.clear();
        
        // Reset processing state
        this.isProcessing = false;
        this.isPaused = false;
    }

    /**
     * Reset UI to initial state
     */
    resetUI() {
        this.selectedFiles = [];
        this.failedFiles = [];
        this.fileProgressMap.clear();
        this.currentBatchId = null;

        // Hide sections
        this.elements.selectedFilesSection?.classList.add('hidden');
        this.elements.processingOptions?.classList.add('hidden');
        this.elements.batchControls?.classList.add('hidden');
        this.elements.progressOverview?.classList.add('hidden');
        this.elements.fileProgressSection?.classList.add('hidden');
        this.elements.errorSection?.classList.add('hidden');
        this.elements.batchResults?.classList.add('hidden');
        this.elements.addToFormBtn?.classList.add('hidden');

        // Reset progress bars
        this.updateProgressBar(this.elements.overallProgressBar, this.elements.overallProgressText, 0);
        this.updateProgressBar(this.elements.uploadProgressBar, this.elements.uploadProgressText, 0);

        // Reset counters
        this.updateCounter(this.elements.totalFilesCount, 0);
        this.updateCounter(this.elements.completedFilesCount, 0);
        this.updateCounter(this.elements.uploadedFilesCount, 0);
        this.updateCounter(this.elements.errorFilesCount, 0);

        // Reset button states
        this.updateButtonStates('idle');

        // Clear lists
        if (this.elements.selectedFilesList) {
            this.elements.selectedFilesList.innerHTML = '';
        }
        if (this.elements.fileProgressList) {
            this.elements.fileProgressList.innerHTML = '';
        }
        if (this.elements.errorList) {
            this.elements.errorList.innerHTML = '';
        }
    }

    /**
     * Handle drag over event
     */
    handleDragOver(e) {
        e.preventDefault();
        this.elements.dropZone?.classList.add('drop-zone-active');
    }

    /**
     * Handle drag leave event
     */
    handleDragLeave(e) {
        e.preventDefault();
        this.elements.dropZone?.classList.remove('drop-zone-active');
    }

    /**
     * Handle drop event
     */
    handleDrop(e) {
        e.preventDefault();
        this.elements.dropZone?.classList.remove('drop-zone-active');
        
        const files = Array.from(e.dataTransfer.files);
        this.handleFileSelection(files);
    }

    /**
     * Handle file selection
     */
    handleFileSelection(files) {
        const validFiles = this.validateFiles(files);
        
        if (validFiles.length === 0) {
            return;
        }

        // Add to selected files (avoid duplicates)
        validFiles.forEach(file => {
            const exists = this.selectedFiles.some(existing => 
                existing.name === file.name && existing.size === file.size
            );
            if (!exists) {
                this.selectedFiles.push(file);
            }
        });

        this.updateSelectedFilesDisplay();
        this.showRelevantSections();
    }

    /**
     * Validate selected files
     */
    validateFiles(files) {
        const validFiles = [];
        const errors = [];

        files.forEach(file => {
            // Check file count limit
            if (this.selectedFiles.length + validFiles.length >= this.options.maxFiles) {
                errors.push(`Maximum ${this.options.maxFiles} files allowed`);
                return;
            }

            // Check file size
            if (file.size > this.options.maxFileSize) {
                errors.push(`${file.name}: File too large (max ${this.formatFileSize(this.options.maxFileSize)})`);
                return;
            }

            // Check file type
            const isValidType = this.options.supportedTypes.some(type => {
                if (type.endsWith('/*')) {
                    return file.type.startsWith(type.slice(0, -1));
                }
                return file.type === type;
            });

            if (!isValidType) {
                errors.push(`${file.name}: Unsupported file type`);
                return;
            }

            validFiles.push(file);
        });

        // Show errors if any
        if (errors.length > 0) {
            this.showErrors(errors);
        }

        return validFiles;
    }

    /**
     * Update selected files display
     */
    updateSelectedFilesDisplay() {
        if (!this.elements.selectedFilesList) return;

        this.elements.selectedFilesList.innerHTML = '';

        this.selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'batch-upload-file-item';
            fileItem.innerHTML = `
                <div class="flex items-center space-x-3 flex-1">
                    <i class="fas ${this.getFileIcon(file.type)} text-gray-400"></i>
                    <div class="flex-1">
                        <div class="font-medium text-gray-900">${this.escapeHtml(file.name)}</div>
                        <div class="file-size-text">${this.formatFileSize(file.size)}</div>
                    </div>
                </div>
                <button class="text-red-600 hover:text-red-800 p-1" onclick="batchUploadUI.removeFile(${index})">
                    <i class="fas fa-times"></i>
                </button>
            `;
            this.elements.selectedFilesList.appendChild(fileItem);
        });

        this.updateCounter(this.elements.totalFilesCount, this.selectedFiles.length);
    }

    /**
     * Remove a file from selection
     */
    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        this.updateSelectedFilesDisplay();
        
        if (this.selectedFiles.length === 0) {
            this.elements.selectedFilesSection?.classList.add('hidden');
            this.elements.processingOptions?.classList.add('hidden');
            this.elements.batchControls?.classList.add('hidden');
        }
    }

    /**
     * Clear all selected files
     */
    clearAllFiles() {
        this.selectedFiles = [];
        this.updateSelectedFilesDisplay();
        this.elements.selectedFilesSection?.classList.add('hidden');
        this.elements.processingOptions?.classList.add('hidden');
        this.elements.batchControls?.classList.add('hidden');
    }

    /**
     * Show relevant UI sections based on current state
     */
    showRelevantSections() {
        if (this.selectedFiles.length > 0) {
            this.elements.selectedFilesSection?.classList.remove('hidden');
            this.elements.processingOptions?.classList.remove('hidden');
            this.elements.batchControls?.classList.remove('hidden');
        }
    }

    /**
     * Update processing options
     */
    updateProcessingOptions() {
        if (!this.batchManager) return;

        const quality = parseFloat(this.elements.compressionQuality?.value || 0.8);
        const maxUploads = parseInt(this.elements.maxConcurrentUploads?.value || 3);
        const maxProcessing = parseInt(this.elements.maxProcessingThreads?.value || 3);

        // Update batch manager options
        this.batchManager.options.maxConcurrentUploads = maxUploads;
        this.batchManager.options.maxConcurrentProcessing = maxProcessing;

        // Update image processor options if available
        if (this.imageProcessor) {
            this.imageProcessor.options = {
                ...this.imageProcessor.options,
                quality: quality
            };
        }
    }

    /**
     * Start batch processing
     */
    async startBatch() {
        if (!this.batchManager || this.selectedFiles.length === 0) {
            return;
        }

        try {
            this.updateProcessingOptions();
            this.updateButtonStates('processing');
            this.showProgressSections();
            this.setupFileProgressDisplay();

            const options = {
                quality: parseFloat(this.elements.compressionQuality?.value || 0.8),
                caseId: this.options.caseId // Pass case ID if available
            };

            const result = await this.batchManager.processBatch(this.selectedFiles, options);
            console.log('Batch processing completed:', result);

        } catch (error) {
            console.error('Batch processing failed:', error);
            this.showErrors([`Batch processing failed: ${error.message}`]);
        } finally {
            this.updateButtonStates('completed');
        }
    }

    /**
     * Pause batch processing
     */
    pauseBatch() {
        if (this.currentBatchId && this.batchManager) {
            this.batchManager.pauseBatch(this.currentBatchId);
            this.updateButtonStates('paused');
        }
    }

    /**
     * Resume batch processing
     */
    resumeBatch() {
        if (this.currentBatchId && this.batchManager) {
            this.batchManager.resumeBatch(this.currentBatchId);
            this.updateButtonStates('processing');
        }
    }

    /**
     * Cancel batch processing
     */
    cancelBatch() {
        if (this.currentBatchId && this.batchManager) {
            this.batchManager.cancelBatch(this.currentBatchId);
            this.updateButtonStates('cancelled');
        }
    }

    /**
     * Show progress sections
     */
    showProgressSections() {
        this.elements.progressOverview?.classList.remove('hidden');
        this.elements.fileProgressSection?.classList.remove('hidden');
    }

    /**
     * Setup file progress display
     */
    setupFileProgressDisplay() {
        if (!this.elements.fileProgressList) return;

        this.elements.fileProgressList.innerHTML = '';
        this.fileProgressMap.clear();

        this.selectedFiles.forEach(file => {
            const progressItem = document.createElement('div');
            progressItem.className = 'batch-upload-file-item';
            progressItem.innerHTML = `
                <div class="flex items-center space-x-3 flex-1">
                    <i class="fas ${this.getFileIcon(file.type)} text-gray-400"></i>
                    <div class="flex-1">
                        <div class="font-medium text-gray-900">${this.escapeHtml(file.name)}</div>
                        <div class="file-size-text">${this.formatFileSize(file.size)}</div>
                        <div class="batch-upload-file-progress mt-1">
                            <div class="batch-upload-file-progress-fill bg-blue-500" style="width: 0%"></div>
                        </div>
                    </div>
                </div>
                <div class="text-right">
                    <span class="batch-upload-status waiting">Waiting</span>
                </div>
            `;
            this.elements.fileProgressList.appendChild(progressItem);
            this.fileProgressMap.set(file.name, progressItem);
        });
    }

    /**
     * Handle batch progress updates
     */
    handleBatchProgress(progress) {
        this.currentBatchId = progress.batchId;

        const overallPercent = Math.round(progress.progress * 100);
        const uploadPercent = Math.round(progress.uploadProgress * 100);

        this.updateProgressBar(this.elements.overallProgressBar, this.elements.overallProgressText, overallPercent);
        this.updateProgressBar(this.elements.uploadProgressBar, this.elements.uploadProgressText, uploadPercent);

        this.updateCounter(this.elements.completedFilesCount, progress.completedFiles);
        this.updateCounter(this.elements.uploadedFilesCount, progress.uploadedFiles);
        this.updateCounter(this.elements.errorFilesCount, progress.errors);

        // Announce progress milestones
        if (overallPercent % 25 === 0 && overallPercent > 0) {
            this.announce(`${overallPercent}% complete. ${progress.completedFiles} of ${progress.totalFiles} files processed.`);
        }

        // Update processing state
        this.isProcessing = progress.status === 'processing';
        this.isPaused = progress.status === 'paused';
    }

    /**
     * Handle individual file progress updates
     */
    handleFileProgress(fileProgress) {
        const progressItem = this.fileProgressMap.get(fileProgress.fileName);
        if (!progressItem) return;

        const statusElement = progressItem.querySelector('.batch-upload-status');
        const progressBar = progressItem.querySelector('.batch-upload-file-progress-fill');

        // Update status
        statusElement.textContent = this.getStatusText(fileProgress.stage, fileProgress.status);
        statusElement.className = `batch-upload-status ${fileProgress.status}`;

        // Update progress bar
        if (fileProgress.progress !== undefined) {
            progressBar.style.width = `${fileProgress.progress}%`;
        }

        // Show error if present
        if (fileProgress.error) {
            statusElement.textContent = `Error: ${fileProgress.error}`;
        }
    }

    /**
     * Handle file completion
     */
    handleFileComplete(event) {
        console.log('File completed:', event.fileResult.originalFile.name);
        
        // Show compression info if available
        const metadata = event.fileResult.metadata;
        if (metadata && metadata.compressionRatio > 1) {
            const progressItem = this.fileProgressMap.get(event.fileResult.originalFile.name);
            if (progressItem) {
                const compressionInfo = document.createElement('div');
                compressionInfo.className = 'compression-info';
                compressionInfo.textContent = `Compressed ${Math.round((1 - 1/metadata.compressionRatio) * 100)}%`;
                progressItem.querySelector('.file-size-text').appendChild(compressionInfo);
            }
        }
    }

    /**
     * Handle batch completion
     */
    handleBatchComplete(result) {
        console.log('Batch completed:', result);
        
        this.updateButtonStates('completed');
        this.showBatchResults(result);
        
        // Show add to form button if successful uploads
        if (result.successfulFiles > 0) {
            this.elements.addToFormBtn?.classList.remove('hidden');
        }

        // Announce completion
        const successCount = result.successfulFiles || 0;
        const failedCount = result.failedFiles || 0;
        const totalTime = ((result.processingTime || 0) / 1000).toFixed(1);
        
        let announcement = `Batch upload completed. ${successCount} files uploaded successfully`;
        if (failedCount > 0) {
            announcement += `, ${failedCount} files failed`;
        }
        announcement += `. Total time: ${totalTime} seconds.`;
        
        this.announce(announcement, 'assertive');

        // Reset processing state
        this.isProcessing = false;
        this.isPaused = false;

        // Focus on results or next action
        if (this.elements.addToFormBtn && !this.elements.addToFormBtn.classList.contains('hidden')) {
            setTimeout(() => this.elements.addToFormBtn.focus(), 100);
        }
    }

    /**
     * Handle errors
     */
    handleError(error) {
        console.error('Batch upload error:', error);
        
        if (error.file) {
            this.failedFiles.push({
                fileName: error.file,
                error: error.error,
                timestamp: error.timestamp
            });
        }
        
        this.showErrors([error.error]);
    }

    /**
     * Show batch results
     */
    showBatchResults(result) {
        if (!this.elements.batchResults) return;

        this.elements.batchResults.classList.remove('hidden');

        const spaceSaved = result.totalOriginalSize - result.totalProcessedSize;
        const totalTimeSeconds = (result.processingTime / 1000).toFixed(1);

        this.updateCounter(this.elements.successfulUploads, result.successfulFiles);
        this.elements.spaceSaved.textContent = this.formatFileSize(spaceSaved);
        this.elements.totalTime.textContent = `${totalTimeSeconds}s`;
        this.elements.avgCompressionRatio.textContent = `${result.averageCompressionRatio.toFixed(1)}x`;
    }

    /**
     * Show errors
     */
    showErrors(errors) {
        if (!this.elements.errorList || errors.length === 0) return;

        this.elements.errorSection?.classList.remove('hidden');

        errors.forEach(error => {
            const errorItem = document.createElement('div');
            errorItem.className = 'batch-upload-error-item';
            errorItem.innerHTML = `
                <div class="flex items-start space-x-2">
                    <i class="fas fa-exclamation-triangle text-red-500 mt-1"></i>
                    <div class="flex-1">
                        <div class="text-sm text-red-800">${this.escapeHtml(error)}</div>
                        <div class="text-xs text-red-600 mt-1">${new Date().toLocaleTimeString()}</div>
                    </div>
                </div>
            `;
            this.elements.errorList.appendChild(errorItem);
        });
    }

    /**
     * Retry failed files
     */
    async retryFailedFiles() {
        if (this.failedFiles.length === 0) return;

        const filesToRetry = this.selectedFiles.filter(file => 
            this.failedFiles.some(failed => failed.fileName === file.name)
        );

        if (filesToRetry.length === 0) return;

        // Clear previous errors
        this.failedFiles = [];
        if (this.elements.errorList) {
            this.elements.errorList.innerHTML = '';
        }

        // Retry with the failed files
        try {
            this.updateButtonStates('processing');
            const options = {
                quality: parseFloat(this.elements.compressionQuality?.value || 0.8),
                caseId: this.options.caseId
            };

            await this.batchManager.processBatch(filesToRetry, options);
        } catch (error) {
            console.error('Retry failed:', error);
            this.showErrors([`Retry failed: ${error.message}`]);
        }
    }

    /**
     * Toggle file progress details
     */
    toggleFileProgressDetails() {
        const list = this.elements.fileProgressList;
        const button = this.elements.toggleFileProgress;
        
        if (!list || !button) return;

        const isHidden = list.classList.contains('hidden');
        
        if (isHidden) {
            list.classList.remove('hidden');
            button.innerHTML = '<i class="fas fa-chevron-up mr-1"></i>Hide Details';
        } else {
            list.classList.add('hidden');
            button.innerHTML = '<i class="fas fa-chevron-down mr-1"></i>Show Details';
        }
    }

    /**
     * Add successful uploads to form
     */
    addToForm() {
        // This method should be implemented based on the specific form integration needs
        // For now, we'll emit a custom event that the parent form can listen to
        const event = new CustomEvent('batchUpload:completed', {
            detail: {
                batchId: this.currentBatchId,
                successfulFiles: this.selectedFiles.length - this.failedFiles.length
            }
        });
        document.dispatchEvent(event);
        
        this.hide();
    }

    /**
     * Update button states based on current status
     */
    updateButtonStates(status) {
        const buttons = {
            start: this.elements.startBatchBtn,
            pause: this.elements.pauseBatchBtn,
            resume: this.elements.resumeBatchBtn,
            cancel: this.elements.cancelBatchBtn
        };

        // Reset all buttons
        Object.values(buttons).forEach(btn => {
            if (btn) btn.disabled = true;
        });

        switch (status) {
            case 'idle':
                if (buttons.start) buttons.start.disabled = false;
                break;
            case 'processing':
                if (buttons.pause) buttons.pause.disabled = false;
                if (buttons.cancel) buttons.cancel.disabled = false;
                break;
            case 'paused':
                if (buttons.resume) buttons.resume.disabled = false;
                if (buttons.cancel) buttons.cancel.disabled = false;
                break;
            case 'completed':
            case 'cancelled':
                if (buttons.start) buttons.start.disabled = false;
                break;
        }
    }

    /**
     * Update progress bar with accessibility support
     */
    updateProgressBar(barElement, textElement, percent) {
        if (barElement) {
            // Use requestAnimationFrame for smooth animations
            if (this.options.enableAnimations) {
                this.animationFrameId = requestAnimationFrame(() => {
                    barElement.style.width = `${percent}%`;
                    barElement.setAttribute('aria-valuenow', percent.toString());
                });
            } else {
                barElement.style.width = `${percent}%`;
                barElement.setAttribute('aria-valuenow', percent.toString());
            }
        }
        if (textElement) {
            textElement.textContent = `${percent}%`;
        }
    }

    /**
     * Update counter display
     */
    updateCounter(element, value) {
        if (element) {
            element.textContent = value.toString();
        }
    }

    /**
     * Get file icon based on file type
     */
    getFileIcon(fileType) {
        if (fileType.startsWith('image/')) {
            return 'fa-image';
        } else if (fileType.startsWith('video/')) {
            return 'fa-video';
        }
        return 'fa-file';
    }

    /**
     * Get status text for display
     */
    getStatusText(stage, status) {
        const statusMap = {
            waiting: 'Waiting',
            processing: 'Processing',
            uploading: 'Uploading',
            completed: 'Completed',
            error: 'Error',
            paused: 'Paused'
        };
        return statusMap[status] || statusMap[stage] || 'Unknown';
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

/**
 * Focus Management for accessibility
 */
class FocusManager {
    constructor(modal) {
        this.modal = modal;
        this.focusableElements = [];
        this.previousFocus = null;
        this.firstFocusable = null;
        this.lastFocusable = null;
    }

    /**
     * Initialize focus management when modal opens
     */
    initialize() {
        this.previousFocus = document.activeElement;
        this.updateFocusableElements();
        this.trapFocus();
        
        // Focus first element
        if (this.firstFocusable) {
            this.firstFocusable.focus();
        }
    }

    /**
     * Update list of focusable elements
     */
    updateFocusableElements() {
        const focusableSelectors = [
            'button:not([disabled])',
            'input:not([disabled])',
            'select:not([disabled])',
            'textarea:not([disabled])',
            '[tabindex]:not([tabindex="-1"])',
            'a[href]'
        ];

        this.focusableElements = Array.from(
            this.modal.querySelectorAll(focusableSelectors.join(', '))
        ).filter(el => {
            return el.offsetWidth > 0 && el.offsetHeight > 0 && !el.hidden;
        });

        this.firstFocusable = this.focusableElements[0];
        this.lastFocusable = this.focusableElements[this.focusableElements.length - 1];
    }

    /**
     * Trap focus within modal
     */
    trapFocus() {
        this.modal.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                if (e.shiftKey) {
                    if (document.activeElement === this.firstFocusable) {
                        e.preventDefault();
                        this.lastFocusable?.focus();
                    }
                } else {
                    if (document.activeElement === this.lastFocusable) {
                        e.preventDefault();
                        this.firstFocusable?.focus();
                    }
                }
            }
        });
    }

    /**
     * Restore focus when modal closes
     */
    restore() {
        if (this.previousFocus) {
            this.previousFocus.focus();
        }
    }
}

/**
 * Keyboard Handler for enhanced navigation
 */
class KeyboardHandler {
    constructor(batchUploadUI) {
        this.ui = batchUploadUI;
        this.shortcuts = new Map([
            ['Escape', () => this.ui.hide()],
            ['Enter', (e) => this.handleEnterKey(e)],
            [' ', (e) => this.handleSpaceKey(e)],
            ['Delete', (e) => this.handleDeleteKey(e)],
            ['Backspace', (e) => this.handleDeleteKey(e)]
        ]);

        this.bindEvents();
    }

    /**
     * Bind keyboard events
     */
    bindEvents() {
        document.addEventListener('keydown', (e) => {
            if (!this.ui.isVisible) return;

            const handler = this.shortcuts.get(e.key);
            if (handler) {
                handler(e);
            }
        });

        // Drop zone keyboard support
        if (this.ui.elements.dropZone) {
            this.ui.elements.dropZone.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.ui.elements.fileInput?.click();
                }
            });
        }
    }

    /**
     * Handle Enter key
     */
    handleEnterKey(e) {
        const target = e.target;
        
        if (target === this.ui.elements.dropZone) {
            e.preventDefault();
            this.ui.elements.fileInput?.click();
        } else if (target.classList.contains('batch-upload-file-item')) {
            // Focus on remove button within file item
            const removeBtn = target.querySelector('button');
            if (removeBtn) {
                removeBtn.focus();
            }
        }
    }

    /**
     * Handle Space key
     */
    handleSpaceKey(e) {
        const target = e.target;
        
        if (target === this.ui.elements.dropZone) {
            e.preventDefault();
            this.ui.elements.fileInput?.click();
        }
    }

    /**
     * Handle Delete/Backspace key
     */
    handleDeleteKey(e) {
        const target = e.target;
        
        if (target.classList.contains('batch-upload-file-item')) {
            e.preventDefault();
            const removeBtn = target.querySelector('button');
            if (removeBtn) {
                removeBtn.click();
            }
        }
    }
}

// Global instance
let batchUploadUI = null;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if the batch upload modal exists
    if (document.getElementById('batchUploadModal')) {
        batchUploadUI = new BatchUploadUI();
        
        // Make it globally accessible
        window.batchUploadUI = batchUploadUI;
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BatchUploadUI;
}