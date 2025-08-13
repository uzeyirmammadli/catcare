/**
 * Client-Side Image Processor
 * Provides immediate image processing feedback with Canvas API
 * Optimized for upload optimization and bandwidth-limited connections
 */

class ImageProcessor {
    constructor(options = {}) {
        this.options = {
            // Compression settings
            defaultQuality: 0.8,
            maxFileSize: 2 * 1024 * 1024, // 2MB
            aggressiveCompressionThreshold: 1 * 1024 * 1024, // 1MB
            
            // Resize settings
            maxWidth: 1920,
            maxHeight: 1080,
            thumbnailSize: 300,
            
            // Format settings
            supportedFormats: ['image/jpeg', 'image/png', 'image/webp'],
            outputFormat: 'image/jpeg',
            
            // Performance settings
            useWebWorkers: true,
            maxConcurrentProcessing: 3,
            
            // Device adaptation
            adaptToConnection: true,
            adaptToDevice: true,
            
            ...options
        };

        // Processing state
        this.processingQueue = [];
        this.activeProcessing = 0;
        this.workerPool = [];
        
        // Device and network detection
        this.deviceCapabilities = this._detectDeviceCapabilities();
        this.networkInfo = this._detectNetworkCapabilities();
        
        // Initialize Web Workers if supported
        if (this.options.useWebWorkers && this._supportsWebWorkers()) {
            this._initializeWorkerPool();
        }
        
        // Adaptive settings based on device/network
        this._applyAdaptiveSettings();
    }

    /**
     * Process a single image file
     * @param {File} file - Image file to process
     * @param {Object} processingOptions - Processing options
     * @returns {Promise<ProcessedImageResult>}
     */
    async processImage(file, processingOptions = {}) {
        try {
            // Validate input
            const validation = this.validateImageFormat(file);
            if (!validation.isValid) {
                throw new Error(`Invalid image format: ${validation.error}`);
            }

            // Merge options with defaults
            const options = {
                ...this.options,
                ...processingOptions
            };

            // Create processing task
            const task = {
                id: this._generateId(),
                file,
                options,
                timestamp: Date.now()
            };

            // Add to queue and process
            return await this._processImageTask(task);
            
        } catch (error) {
            console.error('Image processing failed:', error);
            throw error;
        }
    }

    /**
     * Process multiple images in batch
     * @param {FileList|Array} files - Array of image files
     * @param {Object} options - Processing options
     * @returns {Promise<Array<ProcessedImageResult>>}
     */
    async processBatch(files, options = {}) {
        const fileArray = Array.from(files);
        const results = [];
        
        // Process files with concurrency limit
        const chunks = this._chunkArray(fileArray, this.options.maxConcurrentProcessing);
        
        for (const chunk of chunks) {
            const chunkPromises = chunk.map(file => 
                this.processImage(file, options).catch(error => ({
                    error: error.message,
                    file: file.name
                }))
            );
            
            const chunkResults = await Promise.all(chunkPromises);
            results.push(...chunkResults);
        }
        
        return results;
    }

    /**
     * Compress image with adaptive quality
     * @param {File} file - Image file to compress
     * @param {number} quality - Compression quality (0-1)
     * @returns {Promise<Blob>}
     */
    async compressImage(file, quality = null) {
        return new Promise((resolve, reject) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            
            img.onload = () => {
                try {
                    // Set canvas dimensions
                    canvas.width = img.width;
                    canvas.height = img.height;
                    
                    // Draw image to canvas
                    ctx.drawImage(img, 0, 0);
                    
                    // Determine compression quality
                    const compressionQuality = quality || this._calculateOptimalQuality(file.size);
                    
                    // Convert to blob with compression
                    canvas.toBlob((blob) => {
                        if (blob) {
                            resolve(blob);
                        } else {
                            reject(new Error('Failed to compress image'));
                        }
                    }, this.options.outputFormat, compressionQuality);
                    
                } catch (error) {
                    reject(error);
                }
            };
            
            img.onerror = () => reject(new Error('Failed to load image'));
            img.src = URL.createObjectURL(file);
        });
    }

    /**
     * Resize image for bandwidth optimization
     * @param {File} file - Image file to resize
     * @param {number} maxWidth - Maximum width
     * @param {number} maxHeight - Maximum height
     * @returns {Promise<Blob>}
     */
    async resizeImage(file, maxWidth = null, maxHeight = null) {
        return new Promise((resolve, reject) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            
            img.onload = () => {
                try {
                    // Calculate new dimensions
                    const targetWidth = maxWidth || this.options.maxWidth;
                    const targetHeight = maxHeight || this.options.maxHeight;
                    
                    const dimensions = this._calculateResizeDimensions(
                        img.width, 
                        img.height, 
                        targetWidth, 
                        targetHeight
                    );
                    
                    // Set canvas dimensions
                    canvas.width = dimensions.width;
                    canvas.height = dimensions.height;
                    
                    // Enable image smoothing for better quality
                    ctx.imageSmoothingEnabled = true;
                    ctx.imageSmoothingQuality = 'high';
                    
                    // Draw resized image
                    ctx.drawImage(img, 0, 0, dimensions.width, dimensions.height);
                    
                    // Convert to blob
                    canvas.toBlob((blob) => {
                        if (blob) {
                            resolve(blob);
                        } else {
                            reject(new Error('Failed to resize image'));
                        }
                    }, this.options.outputFormat, this.options.defaultQuality);
                    
                } catch (error) {
                    reject(error);
                }
            };
            
            img.onerror = () => reject(new Error('Failed to load image for resizing'));
            img.src = URL.createObjectURL(file);
        });
    }

    /**
     * Generate preview thumbnail
     * @param {File} file - Image file
     * @param {number} size - Thumbnail size
     * @returns {Promise<Blob>}
     */
    async generatePreviewThumbnail(file, size = null) {
        const thumbnailSize = size || this.options.thumbnailSize;
        
        return new Promise((resolve, reject) => {
            const canvas = document.createElement('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            
            img.onload = () => {
                try {
                    // Calculate square thumbnail dimensions with smart cropping
                    const cropDimensions = this._calculateSquareCrop(img.width, img.height);
                    
                    // Set canvas to thumbnail size
                    canvas.width = thumbnailSize;
                    canvas.height = thumbnailSize;
                    
                    // Enable high-quality scaling
                    ctx.imageSmoothingEnabled = true;
                    ctx.imageSmoothingQuality = 'high';
                    
                    // Draw cropped and scaled image
                    ctx.drawImage(
                        img,
                        cropDimensions.x, cropDimensions.y, 
                        cropDimensions.width, cropDimensions.height,
                        0, 0, 
                        thumbnailSize, thumbnailSize
                    );
                    
                    // Convert to blob with optimized quality for thumbnails
                    canvas.toBlob((blob) => {
                        if (blob) {
                            resolve(blob);
                        } else {
                            reject(new Error('Failed to generate thumbnail'));
                        }
                    }, this.options.outputFormat, 0.85);
                    
                } catch (error) {
                    reject(error);
                }
            };
            
            img.onerror = () => reject(new Error('Failed to load image for thumbnail'));
            img.src = URL.createObjectURL(file);
        });
    }

    /**
     * Validate image format
     * @param {File} file - File to validate
     * @returns {Object} Validation result
     */
    validateImageFormat(file) {
        if (!file) {
            return { isValid: false, error: 'No file provided' };
        }
        
        if (!file.type.startsWith('image/')) {
            return { isValid: false, error: 'File is not an image' };
        }
        
        if (!this.options.supportedFormats.includes(file.type)) {
            return { 
                isValid: false, 
                error: `Unsupported format: ${file.type}. Supported: ${this.options.supportedFormats.join(', ')}` 
            };
        }
        
        if (file.size > 50 * 1024 * 1024) { // 50MB limit
            return { isValid: false, error: 'File too large (max 50MB)' };
        }
        
        return { isValid: true };
    }

    /**
     * Get processing capabilities info
     * @returns {Object} Capabilities information
     */
    getCapabilities() {
        return {
            webWorkers: this._supportsWebWorkers(),
            canvas: this._supportsCanvas(),
            supportedFormats: this.options.supportedFormats,
            deviceCapabilities: this.deviceCapabilities,
            networkInfo: this.networkInfo,
            adaptiveSettings: this._getAdaptiveSettings()
        };
    }

    // Private methods

    async _processImageTask(task) {
        const { file, options } = task;
        
        try {
            // Use Web Worker if available and beneficial
            if (this.options.useWebWorkers && this.workerPool.length > 0 && file.size > 500 * 1024) {
                return await this._processWithWorker(task);
            } else {
                return await this._processOnMainThread(task);
            }
        } catch (error) {
            throw new Error(`Processing failed for ${file.name}: ${error.message}`);
        }
    }

    async _processOnMainThread(task) {
        const { file, options } = task;
        const startTime = performance.now();
        
        // Step 1: Compress if needed
        let processedBlob = file;
        if (file.size > options.aggressiveCompressionThreshold) {
            processedBlob = await this.compressImage(file);
        }
        
        // Step 2: Resize if needed
        const img = await this._loadImage(processedBlob);
        if (img.width > options.maxWidth || img.height > options.maxHeight) {
            processedBlob = await this.resizeImage(processedBlob, options.maxWidth, options.maxHeight);
        }
        
        // Step 3: Generate thumbnail
        const thumbnail = await this.generatePreviewThumbnail(processedBlob);
        
        // Calculate metrics
        const processingTime = performance.now() - startTime;
        const compressionRatio = file.size / processedBlob.size;
        
        return {
            original: file,
            processed: processedBlob,
            thumbnail,
            metadata: {
                originalSize: file.size,
                processedSize: processedBlob.size,
                compressionRatio,
                processingTime,
                dimensions: {
                    width: img.width,
                    height: img.height
                }
            }
        };
    }

    async _processWithWorker(task) {
        return new Promise((resolve, reject) => {
            const worker = this._getAvailableWorker();
            if (!worker) {
                // Fallback to main thread
                return this._processOnMainThread(task).then(resolve).catch(reject);
            }
            
            const timeout = setTimeout(() => {
                reject(new Error('Worker processing timeout'));
            }, 30000); // 30 second timeout
            
            worker.onmessage = (e) => {
                clearTimeout(timeout);
                this._releaseWorker(worker);
                
                if (e.data.error) {
                    reject(new Error(e.data.error));
                } else {
                    resolve(e.data.result);
                }
            };
            
            worker.onerror = (error) => {
                clearTimeout(timeout);
                this._releaseWorker(worker);
                reject(error);
            };
            
            // Send task to worker
            worker.postMessage({
                type: 'processImage',
                task: {
                    ...task,
                    file: {
                        name: task.file.name,
                        size: task.file.size,
                        type: task.file.type,
                        arrayBuffer: task.file.arrayBuffer()
                    }
                }
            });
        });
    }

    _initializeWorkerPool() {
        const workerCount = Math.min(navigator.hardwareConcurrency || 2, 4);
        
        for (let i = 0; i < workerCount; i++) {
            try {
                const worker = new Worker('/static/js/image-processor-worker.js');
                worker.available = true;
                this.workerPool.push(worker);
            } catch (error) {
                console.warn('Failed to create image processing worker:', error);
                break;
            }
        }
    }

    _getAvailableWorker() {
        return this.workerPool.find(worker => worker.available);
    }

    _releaseWorker(worker) {
        worker.available = true;
    }

    _detectDeviceCapabilities() {
        return {
            isMobile: /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
            memory: navigator.deviceMemory || 4,
            cores: navigator.hardwareConcurrency || 2,
            pixelRatio: window.devicePixelRatio || 1
        };
    }

    _detectNetworkCapabilities() {
        const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
        
        return {
            effectiveType: connection?.effectiveType || '4g',
            downlink: connection?.downlink || 10,
            rtt: connection?.rtt || 100,
            saveData: connection?.saveData || false
        };
    }

    _applyAdaptiveSettings() {
        if (!this.options.adaptToDevice && !this.options.adaptToConnection) {
            return;
        }
        
        // Adapt to device capabilities
        if (this.options.adaptToDevice) {
            if (this.deviceCapabilities.isMobile) {
                this.options.maxWidth = Math.min(this.options.maxWidth, 1280);
                this.options.maxHeight = Math.min(this.options.maxHeight, 720);
                this.options.defaultQuality = Math.min(this.options.defaultQuality, 0.75);
            }
            
            if (this.deviceCapabilities.memory < 4) {
                this.options.maxConcurrentProcessing = 1;
                this.options.useWebWorkers = false;
            }
        }
        
        // Adapt to network conditions
        if (this.options.adaptToConnection) {
            if (this.networkInfo.saveData || this.networkInfo.effectiveType === 'slow-2g' || this.networkInfo.effectiveType === '2g') {
                this.options.defaultQuality = 0.6;
                this.options.maxWidth = 800;
                this.options.maxHeight = 600;
                this.options.aggressiveCompressionThreshold = 500 * 1024; // 500KB
            } else if (this.networkInfo.effectiveType === '3g') {
                this.options.defaultQuality = 0.7;
                this.options.maxWidth = 1280;
                this.options.maxHeight = 720;
            }
        }
    }

    _getAdaptiveSettings() {
        return {
            quality: this.options.defaultQuality,
            maxWidth: this.options.maxWidth,
            maxHeight: this.options.maxHeight,
            compressionThreshold: this.options.aggressiveCompressionThreshold,
            useWebWorkers: this.options.useWebWorkers,
            maxConcurrent: this.options.maxConcurrentProcessing
        };
    }

    _calculateOptimalQuality(fileSize) {
        if (fileSize > this.options.maxFileSize) {
            return 0.6; // Aggressive compression for large files
        } else if (fileSize > this.options.aggressiveCompressionThreshold) {
            return 0.75; // Moderate compression
        } else {
            return this.options.defaultQuality; // Default quality
        }
    }

    _calculateResizeDimensions(originalWidth, originalHeight, maxWidth, maxHeight) {
        const aspectRatio = originalWidth / originalHeight;
        
        let newWidth = originalWidth;
        let newHeight = originalHeight;
        
        // Scale down if needed
        if (newWidth > maxWidth) {
            newWidth = maxWidth;
            newHeight = newWidth / aspectRatio;
        }
        
        if (newHeight > maxHeight) {
            newHeight = maxHeight;
            newWidth = newHeight * aspectRatio;
        }
        
        return {
            width: Math.round(newWidth),
            height: Math.round(newHeight)
        };
    }

    _calculateSquareCrop(width, height) {
        const size = Math.min(width, height);
        const x = (width - size) / 2;
        const y = (height - size) / 2;
        
        return { x, y, width: size, height: size };
    }

    _loadImage(blob) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.onload = () => resolve(img);
            img.onerror = reject;
            img.src = URL.createObjectURL(blob);
        });
    }

    _supportsWebWorkers() {
        return typeof Worker !== 'undefined';
    }

    _supportsCanvas() {
        const canvas = document.createElement('canvas');
        return !!(canvas.getContext && canvas.getContext('2d'));
    }

    _chunkArray(array, chunkSize) {
        const chunks = [];
        for (let i = 0; i < array.length; i += chunkSize) {
            chunks.push(array.slice(i, i + chunkSize));
        }
        return chunks;
    }

    _generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ImageProcessor;
}