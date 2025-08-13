/**
 * Image Processing Web Worker
 * Handles image processing tasks in a separate thread to avoid blocking the main UI
 */

// Import OffscreenCanvas polyfill if needed
if (typeof OffscreenCanvas === 'undefined') {
    // Fallback for browsers that don't support OffscreenCanvas
    self.OffscreenCanvas = function(width, height) {
        const canvas = {
            width: width,
            height: height,
            getContext: function(type) {
                // Return a mock context for basic operations
                return {
                    drawImage: function() {},
                    getImageData: function() { return { data: new Uint8ClampedArray(width * height * 4) }; },
                    putImageData: function() {},
                    imageSmoothingEnabled: true,
                    imageSmoothingQuality: 'high'
                };
            },
            convertToBlob: function() {
                return Promise.resolve(new Blob());
            }
        };
        return canvas;
    };
}

class ImageProcessorWorker {
    constructor() {
        this.supportedFormats = ['image/jpeg', 'image/png', 'image/webp'];
        this.outputFormat = 'image/jpeg';
        this.defaultQuality = 0.8;
    }

    async processImage(task) {
        try {
            const { file, options } = task;
            const startTime = performance.now();
            
            // Convert ArrayBuffer back to Blob
            const fileBlob = new Blob([await file.arrayBuffer], { type: file.type });
            
            // Create ImageBitmap for efficient processing
            const imageBitmap = await createImageBitmap(fileBlob);
            
            // Process the image
            const result = await this._processImageBitmap(imageBitmap, file, options);
            
            // Calculate processing time
            result.metadata.processingTime = performance.now() - startTime;
            
            // Clean up
            imageBitmap.close();
            
            return result;
            
        } catch (error) {
            throw new Error(`Worker processing failed: ${error.message}`);
        }
    }

    async _processImageBitmap(imageBitmap, originalFile, options) {
        const { width, height } = imageBitmap;
        
        // Step 1: Determine if resizing is needed
        const needsResize = width > options.maxWidth || height > options.maxHeight;
        const targetDimensions = needsResize ? 
            this._calculateResizeDimensions(width, height, options.maxWidth, options.maxHeight) :
            { width, height };
        
        // Step 2: Create OffscreenCanvas for processing
        const canvas = new OffscreenCanvas(targetDimensions.width, targetDimensions.height);
        const ctx = canvas.getContext('2d');
        
        // Enable high-quality scaling
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        
        // Draw the image (resized if needed)
        ctx.drawImage(imageBitmap, 0, 0, targetDimensions.width, targetDimensions.height);
        
        // Step 3: Determine compression quality
        const quality = this._calculateOptimalQuality(originalFile.size, options);
        
        // Step 4: Convert to blob with compression
        const processedBlob = await canvas.convertToBlob({
            type: this.outputFormat,
            quality: quality
        });
        
        // Step 5: Generate thumbnail
        const thumbnail = await this._generateThumbnail(imageBitmap, options.thumbnailSize || 300);
        
        // Step 6: Calculate metrics
        const compressionRatio = originalFile.size / processedBlob.size;
        
        return {
            processed: await this._blobToArrayBuffer(processedBlob),
            thumbnail: await this._blobToArrayBuffer(thumbnail),
            metadata: {
                originalSize: originalFile.size,
                processedSize: processedBlob.size,
                compressionRatio,
                dimensions: {
                    original: { width, height },
                    processed: targetDimensions
                },
                quality,
                resized: needsResize
            }
        };
    }

    async _generateThumbnail(imageBitmap, size) {
        const { width, height } = imageBitmap;
        
        // Calculate square crop dimensions
        const cropSize = Math.min(width, height);
        const cropX = (width - cropSize) / 2;
        const cropY = (height - cropSize) / 2;
        
        // Create thumbnail canvas
        const thumbnailCanvas = new OffscreenCanvas(size, size);
        const ctx = thumbnailCanvas.getContext('2d');
        
        // Enable high-quality scaling
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';
        
        // Draw cropped and scaled image
        ctx.drawImage(
            imageBitmap,
            cropX, cropY, cropSize, cropSize,
            0, 0, size, size
        );
        
        // Convert to blob with optimized quality for thumbnails
        return await thumbnailCanvas.convertToBlob({
            type: this.outputFormat,
            quality: 0.85
        });
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

    _calculateOptimalQuality(fileSize, options) {
        const maxFileSize = options.maxFileSize || 2 * 1024 * 1024; // 2MB
        const aggressiveThreshold = options.aggressiveCompressionThreshold || 1 * 1024 * 1024; // 1MB
        
        if (fileSize > maxFileSize) {
            return 0.6; // Aggressive compression for large files
        } else if (fileSize > aggressiveThreshold) {
            return 0.75; // Moderate compression
        } else {
            return options.defaultQuality || this.defaultQuality; // Default quality
        }
    }

    async _blobToArrayBuffer(blob) {
        return await blob.arrayBuffer();
    }
}

// Worker message handler
const processor = new ImageProcessorWorker();

self.onmessage = async function(e) {
    const { type, task } = e.data;
    
    try {
        if (type === 'processImage') {
            const result = await processor.processImage(task);
            
            // Convert ArrayBuffers back to transferable objects
            self.postMessage({
                result: {
                    ...result,
                    processed: result.processed,
                    thumbnail: result.thumbnail
                }
            }, [result.processed, result.thumbnail]);
            
        } else {
            throw new Error(`Unknown task type: ${type}`);
        }
        
    } catch (error) {
        self.postMessage({
            error: error.message
        });
    }
};

// Handle worker errors
self.onerror = function(error) {
    self.postMessage({
        error: `Worker error: ${error.message}`
    });
};