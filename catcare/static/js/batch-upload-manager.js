/**
 * Batch Upload Manager
 * Manages parallel processing and upload of multiple files with ImageProcessor integration
 */

class BatchUploadManager {
    constructor(imageProcessor, options = {}) {
        this.imageProcessor = imageProcessor;
        this.options = {
            maxConcurrentUploads: 3,
            maxConcurrentProcessing: 3,
            chunkSize: 1024 * 1024, // 1MB chunks for large files
            retryAttempts: 3,
            retryDelay: 1000,
            uploadEndpoint: '/api/media/upload',
            ...options
        };

        // State management
        this.batches = new Map();
        this.activeUploads = 0;
        this.activeProcessing = 0;
        this.abortControllers = new Map(); // For cancelling uploads
        
        // Event callbacks
        this.callbacks = {
            onProgress: null,
            onFileProgress: null,
            onFileComplete: null,
            onBatchComplete: null,
            onError: null
        };
    }

    /**
     * Process and upload a batch of files
     * @param {FileList|Array} files - Files to process and upload
     * @param {Object} options - Processing and upload options
     * @returns {Promise<BatchResult>}
     */
    async processBatch(files, options = {}) {
        const batchId = this._generateBatchId();
        const fileArray = Array.from(files);
        
        const batch = {
            id: batchId,
            files: fileArray,
            results: [],
            errors: [],
            status: 'processing',
            startTime: Date.now(),
            totalFiles: fileArray.length,
            completedFiles: 0,
            uploadedFiles: 0,
            totalSize: fileArray.reduce((sum, file) => sum + file.size, 0),
            processedSize: 0,
            uploadedSize: 0,
            options: { ...this.options, ...options },
            fileProgress: new Map() // Track individual file progress
        };
        
        this.batches.set(batchId, batch);
        this.abortControllers.set(batchId, new AbortController());
        
        try {
            // Emit batch started event
            this._emitProgress(batch);
            
            // Process and upload files in parallel with concurrency limits
            await this._processAndUploadBatch(batch);
            
            if (batch.status !== 'cancelled') {
                batch.status = 'completed';
            }
            batch.endTime = Date.now();
            batch.processingTime = batch.endTime - batch.startTime;
            
            // Emit batch completed event
            this._emitBatchComplete(batch);
            
            return this._createBatchResult(batch);
            
        } catch (error) {
            if (batch.status !== 'cancelled') {
                batch.status = 'failed';
                batch.error = error.message;
                this._emitError(batch, error);
            }
            throw error;
        } finally {
            // Cleanup
            this.abortControllers.delete(batchId);
        }
    }

    /**
     * Pause batch processing
     * @param {string} batchId - Batch ID to pause
     */
    pauseBatch(batchId) {
        const batch = this.batches.get(batchId);
        if (batch && (batch.status === 'processing' || batch.status === 'uploading')) {
            batch.previousStatus = batch.status;
            batch.status = 'paused';
            batch.pausedAt = Date.now();
            
            // Emit progress update
            this._emitProgress(batch);
        }
    }

    /**
     * Resume paused batch processing
     * @param {string} batchId - Batch ID to resume
     */
    async resumeBatch(batchId) {
        const batch = this.batches.get(batchId);
        if (batch && batch.status === 'paused') {
            batch.status = batch.previousStatus || 'processing';
            batch.pausedDuration = (batch.pausedDuration || 0) + (Date.now() - batch.pausedAt);
            
            // Emit progress update
            this._emitProgress(batch);
            
            // Continue processing remaining files if needed
            if (batch.completedFiles < batch.totalFiles) {
                await this._processAndUploadBatch(batch);
            }
        }
    }

    /**
     * Cancel batch processing
     * @param {string} batchId - Batch ID to cancel
     */
    cancelBatch(batchId) {
        const batch = this.batches.get(batchId);
        const abortController = this.abortControllers.get(batchId);
        
        if (batch) {
            batch.status = 'cancelled';
            batch.cancelledAt = Date.now();
            
            // Abort any ongoing uploads
            if (abortController) {
                abortController.abort();
            }
            
            // Emit progress update
            this._emitProgress(batch);
        }
    }

    /**
     * Get batch status
     * @param {string} batchId - Batch ID
     * @returns {Object} Batch status information
     */
    getBatchStatus(batchId) {
        const batch = this.batches.get(batchId);
        if (!batch) return null;
        
        return {
            id: batch.id,
            status: batch.status,
            totalFiles: batch.totalFiles,
            completedFiles: batch.completedFiles,
            uploadedFiles: batch.uploadedFiles,
            progress: batch.completedFiles / batch.totalFiles,
            uploadProgress: batch.uploadedFiles / batch.totalFiles,
            totalSize: batch.totalSize,
            processedSize: batch.processedSize,
            uploadedSize: batch.uploadedSize,
            errors: batch.errors.length,
            startTime: batch.startTime,
            processingTime: batch.endTime ? batch.endTime - batch.startTime : Date.now() - batch.startTime,
            pausedDuration: batch.pausedDuration || 0
        };
    }

    /**
     * Get individual file progress
     * @param {string} batchId - Batch ID
     * @param {string} fileName - File name
     * @returns {Object} File progress information
     */
    getFileProgress(batchId, fileName) {
        const batch = this.batches.get(batchId);
        if (!batch) return null;
        
        return batch.fileProgress.get(fileName) || {
            status: 'pending',
            progress: 0,
            stage: 'waiting'
        };
    }

    /**
     * Set event callbacks
     * @param {Object} callbacks - Event callback functions
     */
    setCallbacks(callbacks) {
        this.callbacks = { ...this.callbacks, ...callbacks };
    }

    // Private methods

    async _processAndUploadBatch(batch) {
        const semaphore = new Semaphore(batch.options.maxConcurrentProcessing);
        const uploadSemaphore = new Semaphore(batch.options.maxConcurrentUploads);
        
        const filePromises = batch.files.map(async (file, index) => {
            // Skip if already processed or batch is cancelled/paused
            if (batch.results[index] || batch.errors.some(e => e.fileIndex === index) || 
                batch.status === 'cancelled' || batch.status === 'paused') {
                return;
            }
            
            return semaphore.acquire(async () => {
                return this._processAndUploadFile(batch, file, index, uploadSemaphore);
            });
        });
        
        await Promise.allSettled(filePromises);
    }

    async _processAndUploadFile(batch, file, fileIndex, uploadSemaphore) {
        const fileName = file.name;
        
        // Initialize file progress
        batch.fileProgress.set(fileName, {
            status: 'processing',
            progress: 0,
            stage: 'processing'
        });
        
        this._emitFileProgress(batch, fileName);
        
        try {
            // Check if batch is still active
            if (batch.status === 'cancelled' || batch.status === 'paused') {
                return;
            }
            
            this.activeProcessing++;
            
            // Process the image
            const processedResult = await this.imageProcessor.processImage(file, batch.options);
            
            // Update file progress
            batch.fileProgress.set(fileName, {
                status: 'uploading',
                progress: 0,
                stage: 'uploading'
            });
            
            this._emitFileProgress(batch, fileName);
            
            // Upload the processed file
            const uploadResult = await uploadSemaphore.acquire(async () => {
                return this._uploadFile(batch, file, processedResult, fileIndex);
            });
            
            // Create file result
            const fileResult = {
                originalFile: file,
                processedBlob: processedResult.processed,
                thumbnail: processedResult.thumbnail,
                metadata: processedResult.metadata,
                uploadResult: uploadResult,
                status: 'completed',
                processingTime: processedResult.metadata.processingTime,
                uploadTime: uploadResult.uploadTime
            };
            
            // Update batch progress
            batch.results[fileIndex] = fileResult;
            batch.completedFiles++;
            batch.uploadedFiles++;
            batch.processedSize += processedResult.processed.size;
            batch.uploadedSize += processedResult.processed.size;
            
            // Update file progress
            batch.fileProgress.set(fileName, {
                status: 'completed',
                progress: 100,
                stage: 'completed'
            });
            
            // Emit progress updates
            this._emitProgress(batch);
            this._emitFileProgress(batch, fileName);
            this._emitFileComplete(batch, fileResult);
            
            return fileResult;
            
        } catch (error) {
            const fileError = {
                file: fileName,
                fileIndex: fileIndex,
                error: error.message,
                timestamp: Date.now(),
                stage: batch.fileProgress.get(fileName)?.stage || 'processing'
            };
            
            batch.errors.push(fileError);
            batch.completedFiles++;
            
            // Update file progress
            batch.fileProgress.set(fileName, {
                status: 'error',
                progress: 0,
                stage: 'error',
                error: error.message
            });
            
            this._emitError(batch, error, file);
            this._emitFileProgress(batch, fileName);
            
            return fileError;
            
        } finally {
            this.activeProcessing--;
        }
    }

    async _uploadFile(batch, originalFile, processedResult, fileIndex) {
        const startTime = Date.now();
        const abortController = this.abortControllers.get(batch.id);
        
        try {
            this.activeUploads++;
            
            // Create FormData for upload
            const formData = new FormData();
            formData.append('file', processedResult.processed, originalFile.name);
            formData.append('thumbnail', processedResult.thumbnail, `thumb_${originalFile.name}`);
            formData.append('metadata', JSON.stringify(processedResult.metadata));
            formData.append('originalSize', originalFile.size);
            formData.append('processedSize', processedResult.processed.size);
            
            // Add any additional options
            if (batch.options.caseId) {
                formData.append('caseId', batch.options.caseId);
            }
            
            const response = await fetch(batch.options.uploadEndpoint, {
                method: 'POST',
                body: formData,
                signal: abortController?.signal
            });
            
            if (!response.ok) {
                throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
            }
            
            const result = await response.json();
            
            return {
                success: true,
                uploadTime: Date.now() - startTime,
                response: result
            };
            
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Upload cancelled');
            }
            throw error;
        } finally {
            this.activeUploads--;
        }
    }

    _createBatchResult(batch) {
        const successfulResults = batch.results.filter(r => r && r.status === 'completed');
        const totalOriginalSize = batch.files.reduce((sum, file) => sum + file.size, 0);
        const totalProcessedSize = successfulResults.reduce((sum, result) => sum + result.processedBlob.size, 0);
        
        return {
            batchId: batch.id,
            status: batch.status,
            totalFiles: batch.totalFiles,
            successfulFiles: successfulResults.length,
            failedFiles: batch.errors.length,
            uploadedFiles: batch.uploadedFiles,
            results: batch.results.filter(r => r), // Remove null entries
            errors: batch.errors,
            totalOriginalSize,
            totalProcessedSize,
            totalUploadedSize: batch.uploadedSize,
            compressionRatio: totalOriginalSize > 0 ? totalOriginalSize / totalProcessedSize : 1,
            processingTime: batch.processingTime,
            pausedDuration: batch.pausedDuration || 0,
            averageCompressionRatio: successfulResults.length > 0 ? 
                successfulResults.reduce((sum, r) => sum + (r.metadata.compressionRatio || 1), 0) / successfulResults.length : 0,
            averageProcessingTime: successfulResults.length > 0 ?
                successfulResults.reduce((sum, r) => sum + (r.processingTime || 0), 0) / successfulResults.length : 0,
            averageUploadTime: successfulResults.length > 0 ?
                successfulResults.reduce((sum, r) => sum + (r.uploadTime || 0), 0) / successfulResults.length : 0
        };
    }

    _emitProgress(batch) {
        if (this.callbacks.onProgress) {
            this.callbacks.onProgress({
                batchId: batch.id,
                status: batch.status,
                progress: batch.completedFiles / batch.totalFiles,
                uploadProgress: batch.uploadedFiles / batch.totalFiles,
                completedFiles: batch.completedFiles,
                uploadedFiles: batch.uploadedFiles,
                totalFiles: batch.totalFiles,
                processedSize: batch.processedSize,
                uploadedSize: batch.uploadedSize,
                totalSize: batch.totalSize,
                errors: batch.errors.length,
                activeProcessing: this.activeProcessing,
                activeUploads: this.activeUploads
            });
        }
    }

    _emitFileProgress(batch, fileName) {
        if (this.callbacks.onFileProgress) {
            const fileProgress = batch.fileProgress.get(fileName);
            this.callbacks.onFileProgress({
                batchId: batch.id,
                fileName,
                ...fileProgress
            });
        }
    }

    _emitFileComplete(batch, fileResult) {
        if (this.callbacks.onFileComplete) {
            this.callbacks.onFileComplete({
                batchId: batch.id,
                fileResult,
                progress: batch.completedFiles / batch.totalFiles,
                uploadProgress: batch.uploadedFiles / batch.totalFiles
            });
        }
    }

    _emitBatchComplete(batch) {
        if (this.callbacks.onBatchComplete) {
            this.callbacks.onBatchComplete(this._createBatchResult(batch));
        }
    }

    _emitError(batch, error, file = null) {
        if (this.callbacks.onError) {
            this.callbacks.onError({
                batchId: batch.id,
                error: error.message,
                file: file ? file.name : null,
                timestamp: Date.now(),
                stage: file ? batch.fileProgress.get(file.name)?.stage : 'batch'
            });
        }
    }

    _chunkArray(array, chunkSize) {
        const chunks = [];
        for (let i = 0; i < array.length; i += chunkSize) {
            chunks.push(array.slice(i, i + chunkSize));
        }
        return chunks;
    }

    _generateBatchId() {
        return 'batch_' + Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
}

/**
 * Semaphore class for managing concurrency
 */
class Semaphore {
    constructor(maxConcurrency) {
        this.maxConcurrency = maxConcurrency;
        this.currentConcurrency = 0;
        this.queue = [];
    }

    async acquire(task) {
        return new Promise((resolve, reject) => {
            this.queue.push({ task, resolve, reject });
            this._tryNext();
        });
    }

    _tryNext() {
        if (this.currentConcurrency >= this.maxConcurrency || this.queue.length === 0) {
            return;
        }

        this.currentConcurrency++;
        const { task, resolve, reject } = this.queue.shift();

        task()
            .then(resolve)
            .catch(reject)
            .finally(() => {
                this.currentConcurrency--;
                this._tryNext();
            });
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BatchUploadManager;
}