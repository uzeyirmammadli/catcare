/**
 * Camera Capture Module
 * Provides direct photo and video capture capabilities using HTML5 Camera API
 * Optimized for performance with lazy loading and monitoring
 */

class CameraCapture {
    constructor(options = {}) {
        // Performance monitoring initialization
        this.performanceMonitor = new CameraPerformanceMonitor();
        this.performanceMonitor.startSession();
        
        // Mobile-optimized default constraints
        const isMobile = this._isMobileDevice();
        
        this.options = {
            maxRecordingDuration: 120000, // 2 minutes in milliseconds
            photoConstraints: {
                video: {
                    width: { ideal: isMobile ? 720 : 1280 },
                    height: { ideal: isMobile ? 480 : 720 },
                    facingMode: isMobile ? 'environment' : 'user',
                    frameRate: { ideal: isMobile ? 24 : 30 }
                }
            },
            videoConstraints: {
                video: {
                    width: { ideal: isMobile ? 720 : 1280 },
                    height: { ideal: isMobile ? 480 : 720 },
                    facingMode: isMobile ? 'environment' : 'user',
                    frameRate: { ideal: isMobile ? 24 : 30 }
                },
                audio: true
            },
            // Mobile-specific options
            enableHapticFeedback: isMobile,
            touchGestures: isMobile,
            orientationHandling: isMobile,
            // Performance options
            enableLazyLoading: true,
            enablePerformanceMonitoring: true,
            preloadComponents: false,
            // Advanced processing options
            enableAdvancedProcessing: true,
            enableBatchCapture: true,
            enableProcessingPreview: true,
            ...options
        };

        // Lazy initialization of components
        this._componentsLoaded = false;
        this._componentPromises = new Map();
        
        this.state = {
            isActive: false,
            isRecording: false,
            currentCamera: null,
            availableCameras: [],
            capturedMedia: [],
            permissionStatus: 'prompt',
            orientation: this._getCurrentOrientation(),
            isMobile: this._isMobileDevice()
        };

        // Mobile-specific initialization
        this.touchHandler = null;
        this.orientationHandler = null;
        this.hapticSupported = this._checkHapticSupport();
        
        // Advanced processing components
        this.imageProcessor = null;
        this.batchUploadManager = null;
        this.adaptiveProcessor = null;
        this.processingIntegration = null;
        
        // Initialize core functionality
        this._initializeCore();
        this._initializeBlobTracking();
        
        // Initialize advanced processing if enabled
        if (this.options.enableAdvancedProcessing) {
            this._initializeAdvancedProcessing();
        }
        
        // Preload components if requested
        if (this.options.preloadComponents) {
            this._preloadAllComponents();
        }
    }

    // Core initialization without heavy components
    async _initializeCore() {
        try {
            // Initialize performance monitoring
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackEvent('core_init_start');
            }
            
            // Initialize mobile optimizations early
            this._initializeMobileOptimizations();
            
            // Set up event listeners
            this._setupCameraSwitchListener();
            
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackEvent('core_init_complete');
            }
            
            return true;
        } catch (error) {
            console.error('Core initialization failed:', error);
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackError('core_init_error', error);
            }
            return false;
        }
    }

    // Lazy loading of camera components
    async _loadComponents() {
        if (this._componentsLoaded) {
            return true;
        }

        try {
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackEvent('components_load_start');
            }

            // Load components in parallel for better performance
            const componentPromises = [
                this._loadCameraManager(),
                this._loadMediaCapture(),
                this._loadMediaPreview(),
                this._loadCameraControls(),
                this._loadFallbackHandler()
            ];

            await Promise.all(componentPromises);
            this._componentsLoaded = true;

            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackEvent('components_load_complete');
            }

            return true;
        } catch (error) {
            console.error('Component loading failed:', error);
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackError('components_load_error', error);
            }
            throw error;
        }
    }

    async _loadCameraManager() {
        if (!this._componentPromises.has('cameraManager')) {
            this._componentPromises.set('cameraManager', 
                new Promise(resolve => {
                    this.cameraManager = new CameraManager(this.options);
                    resolve(this.cameraManager);
                })
            );
        }
        return this._componentPromises.get('cameraManager');
    }

    async _loadMediaCapture() {
        if (!this._componentPromises.has('mediaCapture')) {
            this._componentPromises.set('mediaCapture',
                new Promise(resolve => {
                    this.mediaCapture = new MediaCapture(this.options);
                    resolve(this.mediaCapture);
                })
            );
        }
        return this._componentPromises.get('mediaCapture');
    }

    async _loadMediaPreview() {
        if (!this._componentPromises.has('mediaPreview')) {
            this._componentPromises.set('mediaPreview',
                new Promise(resolve => {
                    this.mediaPreview = new MediaPreview(this.options);
                    resolve(this.mediaPreview);
                })
            );
        }
        return this._componentPromises.get('mediaPreview');
    }

    async _loadCameraControls() {
        if (!this._componentPromises.has('cameraControls')) {
            this._componentPromises.set('cameraControls',
                new Promise(resolve => {
                    this.cameraControls = new CameraControls(this.options);
                    resolve(this.cameraControls);
                })
            );
        }
        return this._componentPromises.get('cameraControls');
    }

    async _loadFallbackHandler() {
        if (!this._componentPromises.has('fallbackHandler')) {
            this._componentPromises.set('fallbackHandler',
                new Promise(resolve => {
                    this.fallbackHandler = new FallbackHandler(this.options);
                    resolve(this.fallbackHandler);
                })
            );
        }
        return this._componentPromises.get('fallbackHandler');
    }

    // Preload all components for immediate use
    async _preloadAllComponents() {
        try {
            await this._loadComponents();
            await this._initializeCamera();
        } catch (error) {
            console.warn('Component preloading failed:', error);
        }
    }

    async _initializeCamera() {
        try {
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackEvent('camera_init_start');
            }

            // Ensure components are loaded
            await this._loadComponents();

            // Check camera support and initialize fallback if needed
            const isSupported = await this.fallbackHandler.checkCameraSupport();
            if (!isSupported) {
                console.warn('Camera not supported, showing fallback interface');
                this.fallbackHandler.showFallbackInterface();
                
                // Dispatch event to notify that camera is not supported
                const unsupportedEvent = new CustomEvent('camera:unsupported', {
                    detail: { 
                        supportStatus: this.fallbackHandler.getSupportStatus(),
                        timestamp: Date.now()
                    }
                });
                document.dispatchEvent(unsupportedEvent);
                
                if (this.options.enablePerformanceMonitoring) {
                    this.performanceMonitor.trackEvent('camera_unsupported');
                }
                
                return false;
            }

            // Initialize camera manager
            await this.cameraManager.init();
            
            // Update state with available cameras
            this.state.availableCameras = await this.cameraManager.getAvailableCameras();
            this.state.currentCamera = this.cameraManager.getCurrentCamera();
            
            // Dispatch event to notify successful initialization
            const initEvent = new CustomEvent('camera:initialized', {
                detail: { 
                    availableCameras: this.state.availableCameras.length,
                    currentCamera: this.state.currentCamera,
                    supportStatus: this.fallbackHandler.getSupportStatus()
                }
            });
            document.dispatchEvent(initEvent);
            
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackEvent('camera_init_complete');
            }
            
            return true;
        } catch (error) {
            console.error('Camera initialization failed:', error);
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackError('camera_init_error', error);
            }
            
            // Ensure fallback handler is loaded before using it
            await this._loadFallbackHandler();
            this.fallbackHandler.handleGenericError(error);
            return false;
        }
    }

    async startPhotoCapture(container) {
        try {
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackEvent('photo_capture_start');
            }

            // Show loading indicator
            this._showCameraLoadingIndicator(container, 'photo');
            
            // Ensure components are loaded
            await this._loadComponents();
            
            // Initialize camera if not already done
            if (!this._componentsLoaded || !this.cameraManager.isInitialized) {
                await this._initializeCamera();
            }
            
            // Dispatch starting event
            const startingEvent = new CustomEvent('camera:photo-starting', {
                detail: { timestamp: Date.now() }
            });
            document.dispatchEvent(startingEvent);
            
            const stream = await this.cameraManager.initializeCamera(this.options.photoConstraints);
            this.state.isActive = true;
            this.state.permissionStatus = 'granted';
            
            // Hide loading indicator
            this._hideCameraLoadingIndicator();
            
            this.mediaPreview.showLivePreview(stream, container);
            this.cameraControls.renderControls(container, 'photo');
            
            // Enhance camera interface with processing options
            if (this.processingIntegration) {
                this.processingIntegration.enhanceCameraInterface(container);
            }
            
            // Dispatch success event
            const successEvent = new CustomEvent('camera:photo-ready', {
                detail: { 
                    timestamp: Date.now(),
                    cameraInfo: this.cameraManager.getCurrentCamera(),
                    processingEnabled: !!this.processingIntegration
                }
            });
            document.dispatchEvent(successEvent);
            
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackEvent('photo_capture_ready');
            }
            
            return true;
        } catch (error) {
            this._hideCameraLoadingIndicator();
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackError('photo_capture_error', error);
            }
            return this._handleCameraError(error, 'photo');
        }
    }

    async startVideoCapture(container) {
        try {
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackEvent('video_capture_start');
            }

            // Show loading indicator
            this._showCameraLoadingIndicator(container, 'video');
            
            // Ensure components are loaded
            await this._loadComponents();
            
            // Initialize camera if not already done
            if (!this._componentsLoaded || !this.cameraManager.isInitialized) {
                await this._initializeCamera();
            }
            
            // Dispatch starting event
            const startingEvent = new CustomEvent('camera:video-starting', {
                detail: { timestamp: Date.now() }
            });
            document.dispatchEvent(startingEvent);
            
            const stream = await this.cameraManager.initializeCamera(this.options.videoConstraints);
            this.state.isActive = true;
            this.state.permissionStatus = 'granted';
            
            // Hide loading indicator
            this._hideCameraLoadingIndicator();
            
            this.mediaPreview.showLivePreview(stream, container);
            this.cameraControls.renderControls(container, 'video');
            
            // Enhance camera interface with processing options (limited for video)
            if (this.processingIntegration) {
                this.processingIntegration.enhanceCameraInterface(container);
            }
            
            // Dispatch success event
            const successEvent = new CustomEvent('camera:video-ready', {
                detail: { 
                    timestamp: Date.now(),
                    cameraInfo: this.cameraManager.getCurrentCamera(),
                    processingEnabled: !!this.processingIntegration
                }
            });
            document.dispatchEvent(successEvent);
            
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackEvent('video_capture_ready');
            }
            
            return true;
        } catch (error) {
            this._hideCameraLoadingIndicator();
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackError('video_capture_error', error);
            }
            return this._handleCameraError(error, 'video');
        }
    }

    async capturePhoto() {
        if (!this.state.isActive) {
            throw new Error('Camera is not active');
        }
        
        // Show capture progress
        this._showCaptureProgress('photo');
        
        try {
            // Dispatch capture starting event
            const startingEvent = new CustomEvent('photo:capture-starting', {
                detail: { timestamp: Date.now() }
            });
            document.dispatchEvent(startingEvent);
            
            // Capture the photo
            const rawPhotoBlob = await this.mediaCapture.capturePhoto();
            
            // Process the photo with enhanced validation and compression
            let photoData;
            if (this.imageProcessor) {
                // Use advanced image processor if available
                const file = new File([rawPhotoBlob], `photo_${Date.now()}.jpg`, { type: 'image/jpeg' });
                photoData = await this.imageProcessor.processImage(file);
            } else {
                // Fallback to basic processing
                photoData = await this.mediaCapture.processPhoto(rawPhotoBlob);
            }
            
            const capturedMedia = {
                id: this._generateId(),
                type: 'photo',
                blob: photoData.processed || photoData.original,
                originalBlob: photoData.original,
                thumbnail: photoData.thumbnail,
                timestamp: new Date(),
                size: (photoData.processed || photoData.original).size,
                metadata: photoData.metadata,
                processingResult: photoData
            };
            
            this.state.capturedMedia.push(capturedMedia);
            
            // Hide capture progress
            this._hideCaptureProgress();
            
            // Show capture success feedback
            this._showCaptureSuccess('photo');
            
            // Show the captured photo in thumbnail gallery
            const container = document.querySelector('.camera-capture-container');
            if (container) {
                this.mediaPreview.addPhotoToGallery(capturedMedia, container);
                this._updatePhotoCount();
            }
            
            // Update camera controls to show photo count
            this.cameraControls.updatePhotoCount(this.state.capturedMedia.filter(m => m.type === 'photo').length);
            
            // Dispatch capture event
            const captureEvent = new CustomEvent('photo:captured', {
                detail: { 
                    media: capturedMedia, 
                    totalPhotos: this.getPhotoCount(),
                    timestamp: Date.now()
                }
            });
            document.dispatchEvent(captureEvent);
            
            return capturedMedia;
        } catch (error) {
            console.error('Photo capture failed:', error);
            
            // Hide capture progress
            this._hideCaptureProgress();
            
            // Show capture error feedback
            this._showCaptureError('photo', error);
            
            // Dispatch error event
            const errorEvent = new CustomEvent('photo:capture-error', {
                detail: { 
                    error: error.message,
                    errorName: error.name,
                    timestamp: Date.now()
                }
            });
            document.dispatchEvent(errorEvent);
            
            throw error;
        }
    }

    async startVideoRecording() {
        if (!this.state.isActive || this.state.isRecording) return false;
        
        // Show recording start progress
        this._showRecordingStartProgress();
        
        try {
            // Dispatch recording starting event
            const startingEvent = new CustomEvent('video:recording-starting', {
                detail: { timestamp: Date.now() }
            });
            document.dispatchEvent(startingEvent);
            
            await this.mediaCapture.startVideoRecording();
            this.state.isRecording = true;
            
            // Hide recording start progress
            this._hideRecordingStartProgress();
            
            // Show recording indicator with elapsed time
            this.cameraControls.showRecordingIndicator();
            
            // Update control states
            this.cameraControls.updateControlStates(this);
            
            // Show recording started feedback
            this._showRecordingStartedFeedback();
            
            // Dispatch recording started event
            const startEvent = new CustomEvent('video:recording-started', {
                detail: { timestamp: Date.now() }
            });
            document.dispatchEvent(startEvent);
            
            return true;
        } catch (error) {
            console.error('Video recording start failed:', error);
            
            // Hide recording start progress
            this._hideRecordingStartProgress();
            
            // Show recording start error
            this._showRecordingStartError(error);
            
            // Dispatch error event
            const errorEvent = new CustomEvent('video:recording-error', {
                detail: { 
                    error: error.message,
                    errorName: error.name,
                    phase: 'start',
                    timestamp: Date.now()
                }
            });
            document.dispatchEvent(errorEvent);
            
            return false;
        }
    }

    async stopVideoRecording() {
        if (!this.state.isRecording) return null;
        
        // Show recording stop progress
        this._showRecordingStopProgress();
        
        try {
            // Dispatch recording stopping event
            const stoppingEvent = new CustomEvent('video:recording-stopping', {
                detail: { timestamp: Date.now() }
            });
            document.dispatchEvent(stoppingEvent);
            
            const rawVideoBlob = await this.mediaCapture.stopVideoRecording();
            this.state.isRecording = false;
            
            // Hide recording indicator
            this.cameraControls.hideRecordingIndicator();
            
            // Process the video with enhanced validation and metadata
            const videoData = await this.mediaCapture.processVideo(rawVideoBlob);
            
            // Hide recording stop progress
            this._hideRecordingStopProgress();
            
            const capturedMedia = {
                id: this._generateId(),
                type: 'video',
                blob: videoData.original,
                thumbnail: videoData.thumbnail,
                timestamp: new Date(),
                size: videoData.original.size,
                duration: videoData.metadata.duration,
                metadata: videoData.metadata
            };
            
            this.state.capturedMedia.push(capturedMedia);
            
            // Show capture success feedback
            this._showCaptureSuccess('video');
            
            // Show the captured video in preview
            const container = document.querySelector('.camera-capture-container');
            if (container) {
                this.mediaPreview.showCapturedVideo(videoBlob, container, {
                    size: videoBlob.size,
                    duration: capturedMedia.duration,
                    timestamp: capturedMedia.timestamp.toISOString()
                });
            }
            
            // Update control states
            this.cameraControls.updateControlStates(this);
            
            // Dispatch capture event
            const captureEvent = new CustomEvent('video:captured', {
                detail: { 
                    media: capturedMedia,
                    timestamp: Date.now()
                }
            });
            document.dispatchEvent(captureEvent);
            
            return capturedMedia;
        } catch (error) {
            console.error('Video recording stop failed:', error);
            
            // Hide recording indicator on error
            this.cameraControls.hideRecordingIndicator();
            this.state.isRecording = false;
            
            // Hide recording stop progress
            this._hideRecordingStopProgress();
            
            // Show recording stop error
            this._showRecordingStopError(error);
            
            // Dispatch error event
            const errorEvent = new CustomEvent('video:capture-error', {
                detail: { 
                    error: error.message,
                    errorName: error.name,
                    phase: 'stop',
                    timestamp: Date.now()
                }
            });
            document.dispatchEvent(errorEvent);
            
            return null;
        }
    }

    async switchCamera() {
        if (!this.state.isActive) return false;
        
        try {
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackEvent('camera_switch_start');
            }

            // Show switching indicator
            this._showCameraSwitchingIndicator();
            
            // Dispatch switching started event
            const switchingEvent = new CustomEvent('camera:switching-started', {
                detail: { 
                    currentCamera: this.state.currentCamera,
                    timestamp: Date.now()
                }
            });
            document.dispatchEvent(switchingEvent);
            
            // Optimized camera switching with minimal interruption
            const switchStartTime = performance.now();
            const newStream = await this.cameraManager.switchCamera();
            
            // Update preview stream immediately for smooth transition
            this.mediaPreview.updateStream(newStream);
            
            // Update state
            this.state.currentCamera = this.cameraManager.getCurrentCamera();
            this.state.availableCameras = await this.cameraManager.getAvailableCameras();
            
            // Hide switching indicator
            this._hideCameraSwitchingIndicator();
            
            // Update controls to reflect new camera state
            this.cameraControls.updateControlStates(this);
            
            // Show success feedback
            this._showCameraSwitchSuccess();
            
            // Track performance
            if (this.options.enablePerformanceMonitoring) {
                const switchDuration = performance.now() - switchStartTime;
                this.performanceMonitor.trackTiming('camera_switch_duration', switchDuration);
                this.performanceMonitor.trackEvent('camera_switch_complete');
            }
            
            // Dispatch camera switched event
            const switchedEvent = new CustomEvent('camera:switched', {
                detail: { 
                    camera: this.state.currentCamera,
                    availableCameras: this.state.availableCameras,
                    timestamp: Date.now()
                }
            });
            document.dispatchEvent(switchedEvent);
            
            return true;
        } catch (error) {
            console.error('Camera switch failed:', error);
            
            if (this.options.enablePerformanceMonitoring) {
                this.performanceMonitor.trackError('camera_switch_error', error);
            }
            
            // Hide switching indicator
            this._hideCameraSwitchingIndicator();
            
            // Show error feedback
            this._showCameraSwitchError(error);
            
            // Dispatch error event
            const errorEvent = new CustomEvent('camera:switch-error', {
                detail: { 
                    error: error.message,
                    errorName: error.name,
                    timestamp: Date.now()
                }
            });
            document.dispatchEvent(errorEvent);
            
            return false;
        }
    }

    _showCameraSwitchingIndicator() {
        // Remove existing indicator
        this._hideCameraSwitchingIndicator();
        
        const container = document.querySelector('.camera-capture-container');
        if (!container) return;
        
        this.switchingIndicator = document.createElement('div');
        this.switchingIndicator.className = 'switching-indicator absolute top-4 left-1/2 transform -translate-x-1/2 bg-black bg-opacity-75 text-white px-4 py-2 rounded-full z-40 flex items-center space-x-2';
        this.switchingIndicator.innerHTML = `
            <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            <span class="text-sm font-medium">Switching camera...</span>
        `;
        
        container.appendChild(this.switchingIndicator);
    }
    
    _hideCameraSwitchingIndicator() {
        if (this.switchingIndicator) {
            this.switchingIndicator.remove();
            this.switchingIndicator = null;
        }
    }

    _showCameraSwitchSuccess() {
        const container = document.querySelector('.camera-capture-container');
        if (!container) return;
        
        const successIndicator = document.createElement('div');
        successIndicator.className = 'camera-switch-success absolute top-4 left-1/2 transform -translate-x-1/2 bg-green-500 text-white px-4 py-2 rounded-full z-40 flex items-center space-x-2';
        successIndicator.innerHTML = `
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
            </svg>
            <span class="text-sm font-medium">Camera switched</span>
        `;
        
        container.appendChild(successIndicator);
        
        // Remove after 2 seconds
        setTimeout(() => {
            if (successIndicator.parentNode) {
                successIndicator.remove();
            }
        }, 2000);
    }

    _showCameraSwitchError(error) {
        const container = document.querySelector('.camera-capture-container');
        if (!container) return;
        
        const errorIndicator = document.createElement('div');
        errorIndicator.className = 'camera-switch-error absolute top-4 left-1/2 transform -translate-x-1/2 bg-red-500 text-white px-4 py-2 rounded-full z-40 flex items-center space-x-2';
        errorIndicator.innerHTML = `
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
            </svg>
            <span class="text-sm font-medium">Switch failed</span>
        `;
        
        container.appendChild(errorIndicator);
        
        // Remove after 3 seconds
        setTimeout(() => {
            if (errorIndicator.parentNode) {
                errorIndicator.remove();
            }
        }, 3000);
    }

    _showCaptureProgress(type = 'photo') {
        // Remove existing progress indicator
        this._hideCaptureProgress();
        
        const container = document.querySelector('.camera-capture-container');
        if (!container) return;
        
        const typeText = type === 'photo' ? 'photo' : 'video';
        
        this.captureProgressIndicator = document.createElement('div');
        this.captureProgressIndicator.className = 'capture-progress-indicator absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50';
        this.captureProgressIndicator.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-sm mx-4 text-center">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <h3 class="text-lg font-semibold text-gray-900 mb-2">Processing ${typeText}...</h3>
                <p class="text-gray-600">Please wait while we process your ${typeText}.</p>
            </div>
        `;
        
        container.appendChild(this.captureProgressIndicator);
    }
    
    _hideCaptureProgress() {
        if (this.captureProgressIndicator) {
            this.captureProgressIndicator.remove();
            this.captureProgressIndicator = null;
        }
    }

    _showCaptureSuccess(type = 'photo') {
        const container = document.querySelector('.camera-capture-container');
        if (!container) return;
        
        const typeText = type === 'photo' ? 'Photo' : 'Video';
        const icon = type === 'photo' ? 
            `<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"></path>
            </svg>` :
            `<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z"></path>
            </svg>`;
        
        const successIndicator = document.createElement('div');
        successIndicator.className = 'capture-success absolute top-4 left-1/2 transform -translate-x-1/2 bg-green-500 text-white px-4 py-2 rounded-full z-40 flex items-center space-x-2';
        successIndicator.innerHTML = `
            ${icon}
            <span class="text-sm font-medium">${typeText} captured!</span>
        `;
        
        container.appendChild(successIndicator);
        
        // Add a subtle flash effect
        const flashEffect = document.createElement('div');
        flashEffect.className = 'capture-flash absolute inset-0 bg-white z-30 pointer-events-none';
        flashEffect.style.opacity = '0.8';
        container.appendChild(flashEffect);
        
        // Animate flash effect
        setTimeout(() => {
            flashEffect.style.transition = 'opacity 0.3s ease-out';
            flashEffect.style.opacity = '0';
            setTimeout(() => {
                if (flashEffect.parentNode) {
                    flashEffect.remove();
                }
            }, 300);
        }, 50);
        
        // Remove success indicator after 2 seconds
        setTimeout(() => {
            if (successIndicator.parentNode) {
                successIndicator.remove();
            }
        }, 2000);
    }

    _showCaptureError(type = 'photo', error) {
        const container = document.querySelector('.camera-capture-container');
        if (!container) return;
        
        const typeText = type === 'photo' ? 'Photo' : 'Video';
        
        const errorIndicator = document.createElement('div');
        errorIndicator.className = 'capture-error absolute top-4 left-1/2 transform -translate-x-1/2 bg-red-500 text-white px-4 py-2 rounded-full z-40 flex items-center space-x-2';
        errorIndicator.innerHTML = `
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
            </svg>
            <span class="text-sm font-medium">${typeText} capture failed</span>
        `;
        
        container.appendChild(errorIndicator);
        
        // Remove after 3 seconds
        setTimeout(() => {
            if (errorIndicator.parentNode) {
                errorIndicator.remove();
            }
        }, 3000);
    }

    _showRecordingStartProgress() {
        // Remove existing progress indicator
        this._hideRecordingStartProgress();
        
        const container = document.querySelector('.camera-capture-container');
        if (!container) return;
        
        this.recordingStartProgress = document.createElement('div');
        this.recordingStartProgress.className = 'recording-start-progress absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50';
        this.recordingStartProgress.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-sm mx-4 text-center">
                <div class="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg class="w-8 h-8 text-red-600 animate-pulse" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z"></path>
                    </svg>
                </div>
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-red-500 mx-auto mb-4"></div>
                <h3 class="text-lg font-semibold text-gray-900 mb-2">Starting Recording</h3>
                <p class="text-gray-600">Preparing video recording...</p>
            </div>
        `;
        
        container.appendChild(this.recordingStartProgress);
    }
    
    _hideRecordingStartProgress() {
        if (this.recordingStartProgress) {
            this.recordingStartProgress.remove();
            this.recordingStartProgress = null;
        }
    }

    _showRecordingStopProgress() {
        // Remove existing progress indicator
        this._hideRecordingStopProgress();
        
        const container = document.querySelector('.camera-capture-container');
        if (!container) return;
        
        this.recordingStopProgress = document.createElement('div');
        this.recordingStopProgress.className = 'recording-stop-progress absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50';
        this.recordingStopProgress.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-sm mx-4 text-center">
                <div class="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <svg class="w-8 h-8 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z"></path>
                    </svg>
                </div>
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <h3 class="text-lg font-semibold text-gray-900 mb-2">Saving Video</h3>
                <p class="text-gray-600">Processing and saving your video...</p>
            </div>
        `;
        
        container.appendChild(this.recordingStopProgress);
    }
    
    _hideRecordingStopProgress() {
        if (this.recordingStopProgress) {
            this.recordingStopProgress.remove();
            this.recordingStopProgress = null;
        }
    }

    _showRecordingStartedFeedback() {
        const container = document.querySelector('.camera-capture-container');
        if (!container) return;
        
        const startedIndicator = document.createElement('div');
        startedIndicator.className = 'recording-started absolute top-4 left-1/2 transform -translate-x-1/2 bg-red-500 text-white px-4 py-2 rounded-full z-40 flex items-center space-x-2';
        startedIndicator.innerHTML = `
            <div class="w-2 h-2 bg-white rounded-full animate-pulse"></div>
            <span class="text-sm font-medium">Recording started</span>
        `;
        
        container.appendChild(startedIndicator);
        
        // Remove after 2 seconds
        setTimeout(() => {
            if (startedIndicator.parentNode) {
                startedIndicator.remove();
            }
        }, 2000);
    }

    _showRecordingStartError(error) {
        const container = document.querySelector('.camera-capture-container');
        if (!container) return;
        
        const errorIndicator = document.createElement('div');
        errorIndicator.className = 'recording-start-error absolute top-4 left-1/2 transform -translate-x-1/2 bg-red-500 text-white px-4 py-2 rounded-full z-40 flex items-center space-x-2';
        errorIndicator.innerHTML = `
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
            </svg>
            <span class="text-sm font-medium">Recording failed to start</span>
        `;
        
        container.appendChild(errorIndicator);
        
        // Remove after 3 seconds
        setTimeout(() => {
            if (errorIndicator.parentNode) {
                errorIndicator.remove();
            }
        }, 3000);
    }

    _showRecordingStopError(error) {
        const container = document.querySelector('.camera-capture-container');
        if (!container) return;
        
        const errorIndicator = document.createElement('div');
        errorIndicator.className = 'recording-stop-error absolute top-4 left-1/2 transform -translate-x-1/2 bg-red-500 text-white px-4 py-2 rounded-full z-40 flex items-center space-x-2';
        errorIndicator.innerHTML = `
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
            </svg>
            <span class="text-sm font-medium">Failed to save video</span>
        `;
        
        container.appendChild(errorIndicator);
        
        // Remove after 3 seconds
        setTimeout(() => {
            if (errorIndicator.parentNode) {
                errorIndicator.remove();
            }
        }, 3000);
    }

    stopCamera() {
        // Enhanced camera cleanup with comprehensive resource management
        try {
            // Stop camera manager and release streams
            this.cameraManager.stopCamera();
            
            // Clean up media capture resources
            this.mediaCapture.cleanup();
            
            // Clear preview and captured media
            this.mediaPreview.clearPreview();
            this.mediaPreview.clearCapturedMedia();
            
            // Clean up controls
            this.cameraControls.cleanup();
            
            // Clean up captured media blobs
            this._cleanupCapturedMediaBlobs();
            
            // Reset state
            this.state.isActive = false;
            this.state.isRecording = false;
            
            // Dispatch cleanup event
            const cleanupEvent = new CustomEvent('camera:cleanup-complete', {
                detail: { 
                    timestamp: Date.now(),
                    mediaCleanedUp: this.state.capturedMedia.length
                }
            });
            document.dispatchEvent(cleanupEvent);
            
            console.log('Camera resources cleaned up successfully');
        } catch (error) {
            console.error('Error during camera cleanup:', error);
        }
    }

    getCapturedMedia() {
        return [...this.state.capturedMedia];
    }

    removeCapturedMedia(id) {
        const index = this.state.capturedMedia.findIndex(media => media.id === id);
        if (index > -1) {
            // Enhanced blob cleanup for individual media
            const media = this.state.capturedMedia[index];
            this._cleanupMediaBlob(media);
            this.state.capturedMedia.splice(index, 1);
            
            // Update photo count if it was a photo
            if (media.type === 'photo') {
                this._updatePhotoCount();
                this.cameraControls.updatePhotoCount(this.getPhotoCount());
            }
            
            // Dispatch media removed event
            const removeEvent = new CustomEvent('media:removed', {
                detail: { 
                    mediaId: id, 
                    mediaType: media.type,
                    totalPhotos: this.getPhotoCount()
                }
            });
            document.dispatchEvent(removeEvent);
            
            return true;
        }
        return false;
    }

    getPhotoCount() {
        return this.state.capturedMedia.filter(media => media.type === 'photo').length;
    }

    getVideoCount() {
        return this.state.capturedMedia.filter(media => media.type === 'video').length;
    }

    _updatePhotoCount() {
        const photoCount = this.getPhotoCount();
        const container = document.querySelector('.camera-capture-container');
        if (container) {
            this.mediaPreview.updatePhotoGalleryCount(photoCount);
        }
    }

    getState() {
        return { ...this.state };
    }

    // Advanced Processing Integration Methods

    /**
     * Initialize advanced processing components
     */
    async _initializeAdvancedProcessing() {
        try {
            // Initialize ImageProcessor
            if (typeof ImageProcessor !== 'undefined') {
                this.imageProcessor = new ImageProcessor({
                    adaptToDevice: true,
                    adaptToConnection: true,
                    useWebWorkers: true
                });
                console.log('ImageProcessor initialized');
            }

            // Initialize AdaptiveProcessor
            if (typeof AdaptiveProcessor !== 'undefined') {
                this.adaptiveProcessor = new AdaptiveProcessor({
                    performanceMonitoringEnabled: true,
                    networkAdaptationEnabled: true,
                    deviceAdaptationEnabled: true
                });
                console.log('AdaptiveProcessor initialized');
            }

            // Initialize BatchUploadManager
            if (typeof BatchUploadManager !== 'undefined' && this.imageProcessor) {
                this.batchUploadManager = new BatchUploadManager(this.imageProcessor, {
                    maxConcurrentUploads: 2,
                    maxConcurrentProcessing: 2,
                    uploadEndpoint: '/api/media/upload'
                });
                console.log('BatchUploadManager initialized');
            }

            // Initialize processing integration
            if (typeof CameraImageProcessorIntegration !== 'undefined' && 
                this.imageProcessor && this.batchUploadManager && this.adaptiveProcessor) {
                
                this.processingIntegration = new CameraImageProcessorIntegration(
                    this,
                    this.imageProcessor,
                    this.batchUploadManager,
                    this.adaptiveProcessor,
                    {
                        enableRealTimeProcessing: this.options.enableAdvancedProcessing,
                        enableProcessingPreview: this.options.enableProcessingPreview,
                        enableBatchCapture: this.options.enableBatchCapture
                    }
                );
                console.log('CameraImageProcessorIntegration initialized');
            }

        } catch (error) {
            console.warn('Advanced processing initialization failed:', error);
            // Continue without advanced processing
        }
    }

    /**
     * Start batch capture mode
     * @param {HTMLElement} container - Camera container element
     */
    async startBatchCapture(container) {
        if (!this.processingIntegration || !this.options.enableBatchCapture) {
            console.warn('Batch capture not available');
            return false;
        }

        try {
            // Start photo capture first
            const success = await this.startPhotoCapture(container);
            if (!success) return false;

            // Initialize batch capture mode
            await this.processingIntegration.startBatchCapture(container);
            
            // Dispatch batch capture started event
            const batchEvent = new CustomEvent('camera:batch-started', {
                detail: { timestamp: Date.now() }
            });
            document.dispatchEvent(batchEvent);

            return true;
        } catch (error) {
            console.error('Batch capture initialization failed:', error);
            return false;
        }
    }

    /**
     * Upload captured media using batch upload manager
     * @param {Object} uploadOptions - Upload options
     */
    async uploadCapturedMedia(uploadOptions = {}) {
        if (!this.processingIntegration || this.state.capturedMedia.length === 0) {
            return null;
        }

        try {
            const result = await this.processingIntegration.uploadCapturedMedia(
                this.state.capturedMedia,
                uploadOptions
            );

            // Clear captured media after successful upload
            if (result && result.status === 'completed') {
                this.state.capturedMedia = [];
            }

            return result;
        } catch (error) {
            console.error('Media upload failed:', error);
            throw error;
        }
    }

    /**
     * Get processing capabilities
     * @returns {Object} Processing capabilities information
     */
    getProcessingCapabilities() {
        if (!this.imageProcessor) {
            return { available: false };
        }

        return {
            available: true,
            imageProcessor: this.imageProcessor.getCapabilities(),
            adaptiveProcessor: this.adaptiveProcessor ? this.adaptiveProcessor.getAdaptationStatus() : null,
            batchUpload: !!this.batchUploadManager
        };
    }

    /**
     * Enable or disable advanced processing
     * @param {boolean} enabled - Whether to enable processing
     */
    setProcessingEnabled(enabled) {
        if (this.processingIntegration) {
            this.processingIntegration.isProcessingEnabled = enabled;
        }
    }

    /**
     * Get current processing settings
     * @returns {Object} Current processing settings
     */
    getProcessingSettings() {
        if (!this.adaptiveProcessor) {
            return null;
        }

        return this.adaptiveProcessor.getOptimalSettings();
    }

    _handleCameraError(error, context = 'general') {
        console.error('Camera error:', error);
        
        // Update state
        this.state.isActive = false;
        this.state.isRecording = false;
        
        // Show loading indicator while handling error
        this._showErrorProcessingIndicator();
        
        // Handle specific error types with enhanced messaging
        let errorHandled = false;
        
        if (error.name === 'NotAllowedError') {
            this.state.permissionStatus = 'denied';
            this.fallbackHandler.handlePermissionDenied(null, context);
            errorHandled = true;
        } else if (error.name === 'NotFoundError') {
            this.fallbackHandler.handleCameraNotFound(null, context);
            errorHandled = true;
        } else if (error.name === 'NotSupportedError') {
            this.fallbackHandler.handleUnsupportedBrowser(null, context);
            errorHandled = true;
        } else if (error.name === 'NotReadableError') {
            this.fallbackHandler.handleCameraInUse(null, context);
            errorHandled = true;
        } else if (error.name === 'OverconstrainedError') {
            this.fallbackHandler.handleConstraintError(error, null, context);
            errorHandled = true;
        } else if (error.name === 'SecurityError') {
            this.fallbackHandler.handleSecurityError(null, context);
            errorHandled = true;
        } else if (error.name === 'AbortError') {
            this.fallbackHandler.handleInterruptedError(null, context);
            errorHandled = true;
        } else {
            this.fallbackHandler.handleGenericError(error, null, context);
            errorHandled = true;
        }
        
        // Hide error processing indicator
        this._hideErrorProcessingIndicator();
        
        // Dispatch comprehensive error event for external handling
        const errorEvent = new CustomEvent('camera:error', {
            detail: { 
                error: error,
                errorName: error.name,
                errorMessage: error.message,
                context: context,
                state: this.getState(),
                supportStatus: this.fallbackHandler.getSupportStatus(),
                timestamp: Date.now(),
                errorHandled: errorHandled
            }
        });
        document.dispatchEvent(errorEvent);
        
        return false;
    }

    _showErrorProcessingIndicator() {
        // Remove existing indicator
        this._hideErrorProcessingIndicator();
        
        const container = document.querySelector('.camera-capture-container');
        if (!container) return;
        
        this.errorProcessingIndicator = document.createElement('div');
        this.errorProcessingIndicator.className = 'error-processing-indicator fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50';
        this.errorProcessingIndicator.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-sm mx-4 text-center">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p class="text-gray-700">Processing error...</p>
            </div>
        `;
        
        document.body.appendChild(this.errorProcessingIndicator);
    }
    
    _hideErrorProcessingIndicator() {
        if (this.errorProcessingIndicator) {
            this.errorProcessingIndicator.remove();
            this.errorProcessingIndicator = null;
        }
    }

    _showCameraLoadingIndicator(container, type = 'camera') {
        // Remove existing indicator
        this._hideCameraLoadingIndicator();
        
        if (!container) {
            container = document.querySelector('.camera-capture-container') || document.body;
        }
        
        const typeText = type === 'photo' ? 'photo capture' : 
                        type === 'video' ? 'video recording' : 'camera';
        
        this.cameraLoadingIndicator = document.createElement('div');
        this.cameraLoadingIndicator.className = 'camera-loading-indicator fixed inset-0 flex items-center justify-center bg-black bg-opacity-75 z-50';
        this.cameraLoadingIndicator.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-sm mx-4 text-center">
                <div class="mb-4">
                    <div class="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg class="w-8 h-8 text-blue-600 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0118.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"></path>
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"></path>
                        </svg>
                    </div>
                    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
                    <h3 class="text-lg font-semibold text-gray-900 mb-2">Starting Camera</h3>
                    <p class="text-gray-600 mb-4">
                        Initializing ${typeText}...
                    </p>
                </div>
                <div class="bg-blue-50 p-3 rounded-lg text-left">
                    <h4 class="font-medium text-blue-900 mb-2">💡 First time?</h4>
                    <p class="text-sm text-blue-800">
                        Your browser may ask for camera permission. Click "Allow" to continue.
                    </p>
                </div>
            </div>
        `;
        
        document.body.appendChild(this.cameraLoadingIndicator);
        
        // Auto-hide after 15 seconds to prevent hanging
        this.loadingTimeout = setTimeout(() => {
            this._hideCameraLoadingIndicator();
            console.warn('Camera loading timeout - hiding indicator');
        }, 15000);
    }
    
    _hideCameraLoadingIndicator() {
        if (this.cameraLoadingIndicator) {
            this.cameraLoadingIndicator.remove();
            this.cameraLoadingIndicator = null;
        }
        
        if (this.loadingTimeout) {
            clearTimeout(this.loadingTimeout);
            this.loadingTimeout = null;
        }
    }

    _generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    // Enhanced blob memory management methods
    _cleanupCapturedMediaBlobs() {
        try {
            console.log(`Cleaning up ${this.state.capturedMedia.length} captured media blobs`);
            
            this.state.capturedMedia.forEach(media => {
                this._cleanupMediaBlob(media);
            });
            
            // Clear the captured media array
            this.state.capturedMedia = [];
            
            console.log('All captured media blobs cleaned up successfully');
        } catch (error) {
            console.error('Error cleaning up captured media blobs:', error);
        }
    }

    _cleanupMediaBlob(media) {
        try {
            // Clean up main blob URL
            if (media.blobUrl) {
                URL.revokeObjectURL(media.blobUrl);
                media.blobUrl = null;
            }
            
            // Clean up thumbnail blob URL
            if (media.thumbnailUrl) {
                URL.revokeObjectURL(media.thumbnailUrl);
                media.thumbnailUrl = null;
            }
            
            // Clean up any preview URLs
            if (media.previewUrl) {
                URL.revokeObjectURL(media.previewUrl);
                media.previewUrl = null;
            }
            
            // Set blob references to null to help garbage collection
            if (media.blob) {
                media.blob = null;
            }
            
            if (media.thumbnail) {
                media.thumbnail = null;
            }
            
            console.log(`Cleaned up blob resources for media ${media.id}`);
        } catch (error) {
            console.error(`Error cleaning up media blob ${media.id}:`, error);
        }
    }

    // Enhanced page unload cleanup
    _setupResourceCleanup() {
        // Enhanced beforeunload handler
        const beforeUnloadHandler = (event) => {
            this._performComprehensiveCleanup();
            
            // Don't show confirmation dialog for cleanup
            return undefined;
        };
        
        // Enhanced unload handler for final cleanup
        const unloadHandler = () => {
            this._performComprehensiveCleanup();
        };
        
        // Enhanced visibility change handler for background cleanup and restoration
        const visibilityChangeHandler = () => {
            if (document.hidden) {
                // Page is hidden, perform cleanup to free resources
                this._performBackgroundCleanup();
            } else {
                // Page is visible again, restore camera streams if needed
                this._restoreFromBackground();
            }
        };
        
        // Enhanced page freeze handler for mobile devices
        const pageFreezeHandler = () => {
            this._performComprehensiveCleanup();
        };
        
        // Add all event listeners
        window.addEventListener('beforeunload', beforeUnloadHandler, { passive: true });
        window.addEventListener('unload', unloadHandler, { passive: true });
        document.addEventListener('visibilitychange', visibilityChangeHandler, { passive: true });
        
        // Modern page lifecycle API support
        if ('onfreeze' in document) {
            document.addEventListener('freeze', pageFreezeHandler, { passive: true });
        }
        
        // Store handlers for cleanup
        this._resourceCleanupHandlers = {
            beforeUnload: beforeUnloadHandler,
            unload: unloadHandler,
            visibilityChange: visibilityChangeHandler,
            pageFreeze: pageFreezeHandler
        };
    }

    _performComprehensiveCleanup() {
        try {
            console.log('Performing comprehensive resource cleanup');
            
            // Stop camera and clean up streams
            if (this.state.isActive) {
                this.stopCamera();
            }
            
            // Clean up all captured media blobs
            this._cleanupCapturedMediaBlobs();
            
            // Clean up all tracked blob URLs
            if (this._activeBlobUrls) {
                this._cleanupAllTrackedBlobs();
            }
            
            // Clean up mobile-specific handlers
            if (this.touchHandler) {
                this.touchHandler.cleanup();
                this.touchHandler = null;
            }
            
            if (this.orientationHandler) {
                this.orientationHandler.cleanup();
                this.orientationHandler = null;
            }
            
            // Clean up any remaining timers or intervals
            this._cleanupTimersAndIntervals();
            
            // Clean up event listeners
            this._cleanupEventListeners();
            
            console.log('Comprehensive cleanup completed');
        } catch (error) {
            console.error('Error during comprehensive cleanup:', error);
        }
    }

    _performBackgroundCleanup() {
        try {
            console.log('Performing background cleanup for hidden page');
            
            // Stop recording if active to save battery and memory
            if (this.state.isRecording) {
                this.stopVideoRecording().catch(error => {
                    console.error('Error stopping recording during background cleanup:', error);
                });
            }
            
            // Pause camera stream to save battery
            if (this.state.isActive && this.cameraManager.currentStream) {
                this.cameraManager.currentStream.getTracks().forEach(track => {
                    if (track.enabled) {
                        track.enabled = false;
                        // Store original state for restoration
                        track._wasEnabled = true;
                    }
                });
            }
            
            // Clean up any non-essential blob URLs to free memory
            this._cleanupNonEssentialBlobs();
            
            console.log('Background cleanup completed');
        } catch (error) {
            console.error('Error during background cleanup:', error);
        }
    }

    _cleanupNonEssentialBlobs() {
        // Clean up preview URLs but keep main blobs for restoration
        this.state.capturedMedia.forEach(media => {
            if (media.previewUrl) {
                URL.revokeObjectURL(media.previewUrl);
                media.previewUrl = null;
            }
        });
    }

    _restoreFromBackground() {
        try {
            console.log('Restoring camera from background state');
            
            // Restore camera stream if it was active
            if (this.state.isActive && this.cameraManager.currentStream) {
                this.cameraManager.currentStream.getTracks().forEach(track => {
                    if (track._wasEnabled) {
                        track.enabled = true;
                        delete track._wasEnabled;
                    }
                });
                
                console.log('Camera stream restored from background');
            }
            
            // Dispatch restoration event
            const restoreEvent = new CustomEvent('camera:restored-from-background', {
                detail: { 
                    timestamp: Date.now(),
                    wasActive: this.state.isActive
                }
            });
            document.dispatchEvent(restoreEvent);
            
        } catch (error) {
            console.error('Error restoring camera from background:', error);
        }
    }

    _cleanupTimersAndIntervals() {
        // Clean up any timers that might be running
        const timerProperties = [
            'captureProgressIndicator',
            'recordingStartProgress', 
            'recordingStopProgress',
            'switchingIndicator'
        ];
        
        timerProperties.forEach(prop => {
            if (this[prop]) {
                if (this[prop].remove) {
                    this[prop].remove();
                }
                this[prop] = null;
            }
        });
    }

    _cleanupEventListeners() {
        // Remove resource cleanup event listeners
        if (this._resourceCleanupHandlers) {
            window.removeEventListener('beforeunload', this._resourceCleanupHandlers.beforeUnload);
            window.removeEventListener('unload', this._resourceCleanupHandlers.unload);
            document.removeEventListener('visibilitychange', this._resourceCleanupHandlers.visibilityChange);
            
            if ('onfreeze' in document) {
                document.removeEventListener('freeze', this._resourceCleanupHandlers.pageFreeze);
            }
            
            this._resourceCleanupHandlers = null;
        }
    }

    // Enhanced blob URL tracking and management
    _initializeBlobTracking() {
        // Initialize blob URL tracking system
        this._activeBlobUrls = new Set();
        this._blobUrlMetadata = new Map();
    }

    _trackBlobUrl(url, metadata = {}) {
        if (url && url.startsWith('blob:')) {
            this._activeBlobUrls.add(url);
            this._blobUrlMetadata.set(url, {
                created: Date.now(),
                type: metadata.type || 'unknown',
                size: metadata.size || 0,
                mediaId: metadata.mediaId || null
            });
        }
    }

    _untrackBlobUrl(url) {
        if (url && url.startsWith('blob:')) {
            this._activeBlobUrls.delete(url);
            this._blobUrlMetadata.delete(url);
            URL.revokeObjectURL(url);
        }
    }

    _cleanupAllTrackedBlobs() {
        console.log(`Cleaning up ${this._activeBlobUrls.size} tracked blob URLs`);
        
        this._activeBlobUrls.forEach(url => {
            try {
                URL.revokeObjectURL(url);
            } catch (error) {
                console.error(`Error revoking blob URL ${url}:`, error);
            }
        });
        
        this._activeBlobUrls.clear();
        this._blobUrlMetadata.clear();
        
        console.log('All tracked blob URLs cleaned up');
    }

    // Memory usage monitoring
    _getMemoryUsageInfo() {
        const info = {
            capturedMediaCount: this.state.capturedMedia.length,
            activeBlobUrls: this._activeBlobUrls ? this._activeBlobUrls.size : 0,
            totalBlobSize: 0
        };
        
        // Calculate total blob size
        this.state.capturedMedia.forEach(media => {
            if (media.size) {
                info.totalBlobSize += media.size;
            }
        });
        
        // Add browser memory info if available
        if (performance.memory) {
            info.jsHeapSizeLimit = performance.memory.jsHeapSizeLimit;
            info.totalJSHeapSize = performance.memory.totalJSHeapSize;
            info.usedJSHeapSize = performance.memory.usedJSHeapSize;
        }
        
        return info;
    }

    // Public method to get resource usage and cleanup recommendations
    getResourceUsage() {
        const memoryInfo = this._getMemoryUsageInfo();
        const recommendations = [];
        
        // Generate cleanup recommendations
        if (memoryInfo.capturedMediaCount > 10) {
            recommendations.push('Consider removing some captured media to free memory');
        }
        
        if (memoryInfo.totalBlobSize > 50 * 1024 * 1024) { // 50MB
            recommendations.push('Large amount of media in memory, consider processing and clearing');
        }
        
        if (memoryInfo.activeBlobUrls > 20) {
            recommendations.push('Many active blob URLs, cleanup may improve performance');
        }
        
        return {
            ...memoryInfo,
            recommendations,
            timestamp: Date.now()
        };
    }

    // Public method to manually trigger cleanup
    performManualCleanup() {
        console.log('Manual cleanup requested');
        this._performComprehensiveCleanup();
        
        return {
            success: true,
            timestamp: Date.now(),
            message: 'Manual cleanup completed successfully'
        };
    }

    _setupCameraSwitchListener() {
        document.addEventListener('camera:switch-camera', async (event) => {
            await this.switchCamera();
        });
        
        // Add video recording toggle listener
        document.addEventListener('camera:toggle-recording', async (event) => {
            if (this.state.isRecording) {
                await this.stopVideoRecording();
            } else {
                await this.startVideoRecording();
            }
        });

        // Add photo deletion listener
        document.addEventListener('gallery:delete-photo', (event) => {
            const { mediaId } = event.detail;
            this.removeCapturedMedia(mediaId);
        });
    }

    // Mobile-specific optimization methods
    _initializeMobileOptimizations() {
        if (!this.state.isMobile) return;

        // Initialize touch gesture support
        if (this.options.touchGestures) {
            this._initializeTouchGestures();
        }

        // Initialize orientation change handling
        if (this.options.orientationHandling) {
            this._initializeOrientationHandling();
        }

        // Add mobile-specific event listeners
        this._setupMobileEventListeners();
    }

    _initializeTouchGestures() {
        this.touchHandler = new TouchGestureHandler({
            onTap: this._handleTouchTap.bind(this),
            onDoubleTap: this._handleDoubleTap.bind(this),
            onPinch: this._handlePinchGesture.bind(this),
            onSwipe: this._handleSwipeGesture.bind(this)
        });
    }

    _initializeOrientationHandling() {
        this.orientationHandler = new OrientationHandler({
            onOrientationChange: this._handleOrientationChange.bind(this),
            debounceMs: 300
        });
    }

    _setupMobileEventListeners() {
        // Handle device motion for shake-to-capture (if supported)
        if (window.DeviceMotionEvent) {
            window.addEventListener('devicemotion', this._handleDeviceMotion.bind(this));
        }

        // Handle visibility change to pause/resume camera
        document.addEventListener('visibilitychange', this._handleVisibilityChange.bind(this));

        // Enhanced resource cleanup setup
        this._setupResourceCleanup();
    }

    _handleTouchTap(event) {
        const target = event.target.closest('.camera-capture-button');
        if (target) {
            this._triggerHapticFeedback('light');
            // Let the normal click handler process the tap
        }
    }

    _handleDoubleTap(event) {
        // Double tap to switch camera (if multiple cameras available)
        if (this.state.isActive && this.cameraManager.hasMultipleCameras()) {
            event.preventDefault();
            this._triggerHapticFeedback('medium');
            this.switchCamera();
        }
    }

    _handlePinchGesture(event) {
        // Pinch to zoom (if supported by camera)
        if (this.state.isActive) {
            const videoTrack = this.cameraManager.currentStream?.getVideoTracks()[0];
            if (videoTrack && videoTrack.getCapabilities) {
                const capabilities = videoTrack.getCapabilities();
                if (capabilities.zoom) {
                    this._adjustCameraZoom(event.scale);
                }
            }
        }
    }

    _handleSwipeGesture(event) {
        if (!this.state.isActive) return;

        // Horizontal swipe to switch cameras
        if (Math.abs(event.deltaX) > Math.abs(event.deltaY)) {
            if (this.cameraManager.hasMultipleCameras()) {
                this._triggerHapticFeedback('light');
                this.switchCamera();
            }
        }
    }

    _handleOrientationChange(orientation) {
        this.state.orientation = orientation;
        
        // Update camera constraints for new orientation
        if (this.state.isActive) {
            this._updateCameraConstraintsForOrientation(orientation);
        }

        // Update UI layout
        this._updateUIForOrientation(orientation);

        // Dispatch orientation change event
        const orientationEvent = new CustomEvent('camera:orientation-changed', {
            detail: { orientation, timestamp: Date.now() }
        });
        document.dispatchEvent(orientationEvent);
    }

    _handleDeviceMotion(event) {
        // Shake-to-capture functionality
        const acceleration = event.accelerationIncludingGravity;
        if (!acceleration) return;

        const threshold = 15; // Adjust sensitivity
        const totalAcceleration = Math.sqrt(
            acceleration.x * acceleration.x +
            acceleration.y * acceleration.y +
            acceleration.z * acceleration.z
        );

        if (totalAcceleration > threshold && this.state.isActive && !this.state.isRecording) {
            // Debounce shake detection
            if (!this._lastShakeTime || Date.now() - this._lastShakeTime > 1000) {
                this._lastShakeTime = Date.now();
                this._triggerHapticFeedback('heavy');
                this.capturePhoto();
            }
        }
    }

    _handleVisibilityChange() {
        if (document.hidden && this.state.isActive) {
            // Pause camera when app goes to background
            this._pauseCamera();
        } else if (!document.hidden && this.state.isActive) {
            // Resume camera when app comes to foreground
            this._resumeCamera();
        }
    }



    _triggerHapticFeedback(intensity = 'light') {
        if (!this.hapticSupported || !this.options.enableHapticFeedback) return;

        try {
            if (navigator.vibrate) {
                const patterns = {
                    light: [10],
                    medium: [20],
                    heavy: [30, 10, 30]
                };
                navigator.vibrate(patterns[intensity] || patterns.light);
            }
        } catch (error) {
            console.warn('Haptic feedback failed:', error);
        }
    }

    _adjustCameraZoom(scale) {
        // Implement camera zoom if supported
        const videoTrack = this.cameraManager.currentStream?.getVideoTracks()[0];
        if (videoTrack && videoTrack.applyConstraints) {
            const currentZoom = videoTrack.getSettings().zoom || 1;
            const newZoom = Math.max(1, Math.min(3, currentZoom * scale));
            
            videoTrack.applyConstraints({
                advanced: [{ zoom: newZoom }]
            }).catch(error => {
                console.warn('Zoom adjustment failed:', error);
            });
        }
    }

    _updateCameraConstraintsForOrientation(orientation) {
        // Adjust camera constraints based on orientation
        const isLandscape = orientation === 'landscape-primary' || orientation === 'landscape-secondary';
        const constraints = isLandscape ? 
            { width: { ideal: 1280 }, height: { ideal: 720 } } :
            { width: { ideal: 720 }, height: { ideal: 1280 } };

        // Apply new constraints if camera is active
        if (this.cameraManager.currentStream) {
            const videoTrack = this.cameraManager.currentStream.getVideoTracks()[0];
            if (videoTrack && videoTrack.applyConstraints) {
                videoTrack.applyConstraints({ video: constraints }).catch(error => {
                    console.warn('Failed to update constraints for orientation:', error);
                });
            }
        }
    }

    _updateUIForOrientation(orientation) {
        const container = document.querySelector('.camera-capture-container');
        if (!container) return;

        // Add orientation class for CSS styling
        container.classList.remove('portrait', 'landscape');
        const isLandscape = orientation === 'landscape-primary' || orientation === 'landscape-secondary';
        container.classList.add(isLandscape ? 'landscape' : 'portrait');

        // Update control layout
        if (this.cameraControls) {
            this.cameraControls.updateLayoutForOrientation(orientation);
        }
    }

    _pauseCamera() {
        if (this.cameraManager.currentStream) {
            this.cameraManager.currentStream.getVideoTracks().forEach(track => {
                track.enabled = false;
            });
        }
    }

    _resumeCamera() {
        if (this.cameraManager.currentStream) {
            this.cameraManager.currentStream.getVideoTracks().forEach(track => {
                track.enabled = true;
            });
        }
    }

    _isMobileDevice() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
               (navigator.maxTouchPoints && navigator.maxTouchPoints > 2);
    }

    _getCurrentOrientation() {
        if (screen.orientation) {
            return screen.orientation.type;
        } else if (window.orientation !== undefined) {
            const angle = window.orientation;
            if (angle === 0) return 'portrait-primary';
            if (angle === 90) return 'landscape-primary';
            if (angle === 180) return 'portrait-secondary';
            if (angle === -90) return 'landscape-secondary';
        }
        return 'portrait-primary';
    }

    _checkHapticSupport() {
        return 'vibrate' in navigator || 'hapticFeedback' in navigator;
    }

    // Performance monitoring methods
    getPerformanceMetrics() {
        if (!this.options.enablePerformanceMonitoring) {
            return null;
        }
        return this.performanceMonitor.getMetrics();
    }

    // Accessibility improvements
    _enhanceAccessibility() {
        // Add ARIA labels and roles to camera interface
        const container = document.querySelector('.camera-capture-container');
        if (container) {
            container.setAttribute('role', 'application');
            container.setAttribute('aria-label', 'Camera capture interface');
            
            // Add keyboard navigation support
            this._addKeyboardNavigation(container);
            
            // Add screen reader announcements
            this._setupScreenReaderAnnouncements();
        }
    }

    _addKeyboardNavigation(container) {
        // Make container focusable
        container.setAttribute('tabindex', '0');
        
        // Add keyboard event listeners
        container.addEventListener('keydown', (event) => {
            switch (event.key) {
                case ' ':
                case 'Enter':
                    event.preventDefault();
                    if (this.state.isActive && !this.state.isRecording) {
                        this.capturePhoto();
                    }
                    break;
                case 'r':
                case 'R':
                    event.preventDefault();
                    if (this.state.isActive) {
                        if (this.state.isRecording) {
                            this.stopVideoRecording();
                        } else {
                            this.startVideoRecording();
                        }
                    }
                    break;
                case 's':
                case 'S':
                    event.preventDefault();
                    if (this.state.isActive && this.cameraManager.hasMultipleCameras()) {
                        this.switchCamera();
                    }
                    break;
                case 'Escape':
                    event.preventDefault();
                    this.stopCamera();
                    break;
            }
        });
    }

    _setupScreenReaderAnnouncements() {
        // Create live region for announcements
        const liveRegion = document.createElement('div');
        liveRegion.setAttribute('aria-live', 'polite');
        liveRegion.setAttribute('aria-atomic', 'true');
        liveRegion.className = 'sr-only';
        liveRegion.id = 'camera-announcements';
        document.body.appendChild(liveRegion);

        // Listen for camera events and announce them
        document.addEventListener('camera:photo-ready', () => {
            this._announce('Camera ready for photo capture. Press Space or Enter to take a photo.');
        });

        document.addEventListener('camera:video-ready', () => {
            this._announce('Camera ready for video recording. Press R to start recording.');
        });

        document.addEventListener('photo:captured', () => {
            this._announce('Photo captured successfully.');
        });

        document.addEventListener('video:recording-started', () => {
            this._announce('Video recording started. Press R again to stop recording.');
        });

        document.addEventListener('video:captured', () => {
            this._announce('Video recording completed successfully.');
        });

        document.addEventListener('camera:switched', () => {
            this._announce('Camera switched successfully.');
        });
    }

    _announce(message) {
        const liveRegion = document.getElementById('camera-announcements');
        if (liveRegion) {
            liveRegion.textContent = message;
        }
    }

    // Public method to get performance recommendations
    getOptimizationRecommendations() {
        const metrics = this.getPerformanceMetrics();
        const recommendations = [];

        if (metrics) {
            // Analyze performance metrics and provide recommendations
            if (metrics.averageInitTime > 2000) {
                recommendations.push('Camera initialization is slow. Consider enabling component preloading.');
            }

            if (metrics.averageSwitchTime > 1000) {
                recommendations.push('Camera switching is slow. Check device capabilities and network conditions.');
            }

            if (metrics.memoryUsage && metrics.memoryUsage.totalBlobSize > 100 * 1024 * 1024) {
                recommendations.push('High memory usage detected. Consider clearing captured media more frequently.');
            }

            if (metrics.errorRate > 0.1) {
                recommendations.push('High error rate detected. Check camera permissions and device compatibility.');
            }
        }

        return recommendations;
    }
}

/**
 * Camera Performance Monitor
 * Tracks performance metrics and provides optimization insights
 */
class CameraPerformanceMonitor {
    constructor() {
        this.metrics = {
            sessionStart: Date.now(),
            events: [],
            timings: new Map(),
            errors: [],
            memorySnapshots: []
        };
        
        this.isMonitoring = false;
    }

    startSession() {
        this.isMonitoring = true;
        this.metrics.sessionStart = Date.now();
        
        // Take initial memory snapshot
        this._takeMemorySnapshot('session_start');
        
        // Set up periodic memory monitoring
        this._setupMemoryMonitoring();
    }

    trackEvent(eventName, data = {}) {
        if (!this.isMonitoring) return;
        
        this.metrics.events.push({
            name: eventName,
            timestamp: Date.now(),
            data: data
        });
    }

    trackTiming(name, duration) {
        if (!this.isMonitoring) return;
        
        if (!this.metrics.timings.has(name)) {
            this.metrics.timings.set(name, []);
        }
        
        this.metrics.timings.get(name).push(duration);
    }

    trackError(errorType, error) {
        if (!this.isMonitoring) return;
        
        this.metrics.errors.push({
            type: errorType,
            message: error.message,
            name: error.name,
            timestamp: Date.now()
        });
    }

    _takeMemorySnapshot(label) {
        const snapshot = {
            label: label,
            timestamp: Date.now()
        };

        // Add browser memory info if available
        if (performance.memory) {
            snapshot.jsHeapSizeLimit = performance.memory.jsHeapSizeLimit;
            snapshot.totalJSHeapSize = performance.memory.totalJSHeapSize;
            snapshot.usedJSHeapSize = performance.memory.usedJSHeapSize;
        }

        this.metrics.memorySnapshots.push(snapshot);
    }

    _setupMemoryMonitoring() {
        // Take memory snapshots every 30 seconds
        setInterval(() => {
            if (this.isMonitoring) {
                this._takeMemorySnapshot('periodic');
            }
        }, 30000);
    }

    getMetrics() {
        if (!this.isMonitoring) return null;

        const sessionDuration = Date.now() - this.metrics.sessionStart;
        
        // Calculate timing averages
        const timingAverages = {};
        this.metrics.timings.forEach((values, name) => {
            timingAverages[name] = values.reduce((a, b) => a + b, 0) / values.length;
        });

        // Calculate error rate
        const totalEvents = this.metrics.events.length;
        const errorRate = totalEvents > 0 ? this.metrics.errors.length / totalEvents : 0;

        // Memory usage analysis
        const memoryUsage = this._analyzeMemoryUsage();

        return {
            sessionDuration,
            totalEvents: totalEvents,
            totalErrors: this.metrics.errors.length,
            errorRate,
            timingAverages,
            memoryUsage,
            events: this.metrics.events,
            errors: this.metrics.errors,
            memorySnapshots: this.metrics.memorySnapshots
        };
    }

    _analyzeMemoryUsage() {
        if (this.metrics.memorySnapshots.length === 0) return null;

        const latest = this.metrics.memorySnapshots[this.metrics.memorySnapshots.length - 1];
        const initial = this.metrics.memorySnapshots[0];

        return {
            current: latest,
            initial: initial,
            growth: latest.usedJSHeapSize ? latest.usedJSHeapSize - initial.usedJSHeapSize : 0
        };
    }

    stopSession() {
        this.isMonitoring = false;
        this._takeMemorySnapshot('session_end');
    }

    reset() {
        this.metrics = {
            sessionStart: Date.now(),
            events: [],
            timings: new Map(),
            errors: [],
            memorySnapshots: []
        };
    }
}
/**
 
* CameraManager Class
 * Handles core camera operations and stream management
 */
class CameraManager {
    constructor(options = {}) {
        this.options = options;
        this.currentStream = null;
        this.availableCameras = [];
        this.currentCameraIndex = 0;
        this.permissionStatus = 'prompt';
        this.isInitialized = false;
        
        // Performance optimizations
        this._streamCache = new Map();
        this._constraintsCache = new Map();
        this._deviceInfoCache = null;
        this._lastEnumerationTime = 0;
        this._enumerationCacheTimeout = 30000; // 30 seconds
    }

    async init() {
        try {
            // Check if getUserMedia is supported
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw new Error('Camera API not supported');
            }

            // Get available cameras with caching
            await this._enumerateDevices();
            
            this.isInitialized = true;
            return true;
        } catch (error) {
            console.error('Camera manager initialization failed:', error);
            this.isInitialized = false;
            throw error;
        }
    }

    async initializeCamera(constraints = {}) {
        try {
            // Check constraints cache for optimization
            const constraintsKey = JSON.stringify(constraints);
            
            // Request camera permissions and get stream
            const startTime = performance.now();
            this.currentStream = await navigator.mediaDevices.getUserMedia(constraints);
            const initTime = performance.now() - startTime;
            
            // Cache constraints for future use
            this._constraintsCache.set(constraintsKey, {
                constraints,
                initTime,
                timestamp: Date.now()
            });
            
            this.permissionStatus = 'granted';
            
            // Update available cameras after permission is granted (with caching)
            await this._enumerateDevices();
            
            // Determine which camera is currently active
            await this._identifyCurrentCamera();
            
            return this.currentStream;
        } catch (error) {
            this.permissionStatus = 'denied';
            console.error('Camera initialization failed:', error);
            throw error;
        }
    }

    async switchCamera() {
        if (this.availableCameras.length <= 1) {
            throw new Error('No additional cameras available');
        }

        try {
            // Get next camera
            const nextCameraIndex = (this.currentCameraIndex + 1) % this.availableCameras.length;
            const nextCamera = this.availableCameras[nextCameraIndex];
            
            // Create optimized constraints for the new camera
            const constraints = this._getOptimizedConstraints(nextCamera);

            // Check if we have a cached stream for this camera
            const cacheKey = `${nextCamera.deviceId}_${JSON.stringify(constraints)}`;
            
            // Initialize new camera stream
            const switchStartTime = performance.now();
            const newStream = await navigator.mediaDevices.getUserMedia(constraints);
            const switchTime = performance.now() - switchStartTime;
            
            // Cache the new stream info
            this._streamCache.set(cacheKey, {
                constraints,
                switchTime,
                timestamp: Date.now()
            });
            
            // Stop current stream after new one is ready (for smooth transition)
            if (this.currentStream) {
                // Use requestAnimationFrame for smooth transition
                requestAnimationFrame(() => {
                    this.currentStream.getTracks().forEach(track => {
                        track.stop();
                    });
                });
            }
            
            // Update to new stream and camera index
            this.currentStream = newStream;
            this.currentCameraIndex = nextCameraIndex;
            
            return this.currentStream;
        } catch (error) {
            console.error('Camera switch failed:', error);
            
            // If switching failed, try to restore previous camera
            if (!this.currentStream || this.currentStream.getTracks().every(track => track.readyState === 'ended')) {
                try {
                    await this._restorePreviousCamera();
                } catch (restoreError) {
                    console.error('Failed to restore previous camera:', restoreError);
                }
            }
            
            throw error;
        }
    }

    _getOptimizedConstraints(camera) {
        // Return optimized constraints based on device capabilities and previous performance
        const baseConstraints = {
            video: {
                deviceId: { exact: camera.deviceId },
                width: { ideal: 1280 },
                height: { ideal: 720 },
                frameRate: { ideal: 30 }
            }
        };

        // Check cache for previous performance data
        const cacheKey = `${camera.deviceId}_constraints`;
        const cachedData = this._constraintsCache.get(cacheKey);
        
        if (cachedData && cachedData.initTime > 2000) {
            // If previous init was slow, use lower quality constraints
            baseConstraints.video.width = { ideal: 720 };
            baseConstraints.video.height = { ideal: 480 };
            baseConstraints.video.frameRate = { ideal: 24 };
        }

        return baseConstraints;
    }

    stopCamera() {
        try {
            console.log('Stopping camera and cleaning up streams...');
            
            if (this.currentStream) {
                // Get track count for logging
                const trackCount = this.currentStream.getTracks().length;
                console.log(`Stopping ${trackCount} media tracks`);
                
                // Stop all tracks properly
                this.currentStream.getTracks().forEach((track, index) => {
                    try {
                        console.log(`Stopping track ${index + 1}/${trackCount}: ${track.kind} (${track.label})`);
                        track.stop();
                        
                        // Remove event listeners if any
                        track.onended = null;
                        track.onmute = null;
                        track.onunmute = null;
                    } catch (error) {
                        console.error(`Error stopping track ${index + 1}:`, error);
                    }
                });
                
                // Clear the stream reference
                this.currentStream = null;
                console.log('Camera stream stopped and cleaned up successfully');
            }
            
            // Reset camera state
            this._resetCameraState();
            
        } catch (error) {
            console.error('Error stopping camera:', error);
            // Force cleanup even on error
            this.currentStream = null;
            this._resetCameraState();
        }
    }

    _resetCameraState() {
        // Reset camera manager state
        this.isInitialized = false;
        this.currentCameraIndex = 0;
        
        // Clear any cached camera information
        if (this.availableCameras) {
            this.availableCameras = [];
        }
        
        console.log('Camera state reset completed');
    }

    async getAvailableCameras() {
        await this._enumerateDevices();
        return [...this.availableCameras];
    }

    getCurrentCamera() {
        if (this.availableCameras.length > 0 && this.currentCameraIndex < this.availableCameras.length) {
            return this.availableCameras[this.currentCameraIndex];
        }
        return null;
    }

    hasMultipleCameras() {
        return this.availableCameras.length > 1;
    }

    getPermissionStatus() {
        return this.permissionStatus;
    }

    async requestPermissions() {
        try {
            // Request basic camera permission
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            this.permissionStatus = 'granted';
            
            // Stop the test stream immediately
            stream.getTracks().forEach(track => track.stop());
            
            // Update available cameras
            await this._enumerateDevices();
            
            return true;
        } catch (error) {
            this.permissionStatus = 'denied';
            console.error('Permission request failed:', error);
            throw error;
        }
    }

    async _enumerateDevices() {
        try {
            // Check cache first to avoid unnecessary API calls
            const now = Date.now();
            if (this._deviceInfoCache && 
                (now - this._lastEnumerationTime) < this._enumerationCacheTimeout) {
                this.availableCameras = this._deviceInfoCache;
                return;
            }

            const devices = await navigator.mediaDevices.enumerateDevices();
            const videoDevices = devices.filter(device => device.kind === 'videoinput');
            
            // Process and label cameras
            this.availableCameras = videoDevices.map((device, index) => {
                let label = device.label;
                
                // If no label (permissions not granted), create a generic one
                if (!label) {
                    if (videoDevices.length === 1) {
                        label = 'Camera';
                    } else {
                        // Try to determine camera type from deviceId patterns
                        const deviceId = device.deviceId.toLowerCase();
                        if (deviceId.includes('front') || deviceId.includes('user')) {
                            label = 'Front Camera';
                        } else if (deviceId.includes('back') || deviceId.includes('environment')) {
                            label = 'Back Camera';
                        } else {
                            label = `Camera ${index + 1}`;
                        }
                    }
                }
                
                return {
                    deviceId: device.deviceId,
                    groupId: device.groupId,
                    kind: device.kind,
                    label: label,
                    facingMode: this._detectFacingMode(device, index)
                };
            });
            
            // Sort cameras to put back camera first on mobile devices
            if (CameraManager.isMobileDevice() && this.availableCameras.length > 1) {
                this.availableCameras.sort((a, b) => {
                    if (a.facingMode === 'environment' && b.facingMode === 'user') return -1;
                    if (a.facingMode === 'user' && b.facingMode === 'environment') return 1;
                    return 0;
                });
            }
            
            // Cache the results
            this._deviceInfoCache = this.availableCameras;
            this._lastEnumerationTime = now;
            
            return this.availableCameras;
        } catch (error) {
            console.error('Device enumeration failed:', error);
            this.availableCameras = [];
            return [];
        }
    }

    // Utility method to check if camera API is supported
    static isSupported() {
        return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    }

    // Utility method to detect mobile devices
    static isMobileDevice() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }

    // Get optimal constraints for current device
    getOptimalConstraints(type = 'photo') {
        const isMobile = CameraManager.isMobileDevice();
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
        
        const baseConstraints = {
            video: {
                width: { ideal: isMobile ? 720 : 1280 },
                height: { ideal: isMobile ? 480 : 720 },
                frameRate: { ideal: isMobile ? 24 : 30 }
            }
        };

        // Mobile-specific optimizations
        if (isMobile) {
            // Lower resolution for better performance on mobile
            baseConstraints.video.width = { ideal: 640, max: 1280 };
            baseConstraints.video.height = { ideal: 480, max: 720 };
            
            // iOS-specific optimizations
            if (isIOS) {
                baseConstraints.video.frameRate = { ideal: 24, max: 30 };
                // iOS performs better with these constraints
                baseConstraints.video.aspectRatio = { ideal: 4/3 };
            }
        }

        if (type === 'video') {
            baseConstraints.audio = !isIOS; // iOS has audio issues in some contexts
        }

        // Add camera selection if available
        const currentCamera = this.getCurrentCamera();
        if (currentCamera) {
            baseConstraints.video.deviceId = { exact: currentCamera.deviceId };
        } else if (this.availableCameras.length > 0) {
            // Default to back camera on mobile, front camera on desktop
            const preferredFacing = isMobile ? 'environment' : 'user';
            baseConstraints.video.facingMode = preferredFacing;
        }

        return baseConstraints;
    }

    // Helper method to detect camera facing mode
    _detectFacingMode(device, index) {
        const label = device.label.toLowerCase();
        const deviceId = device.deviceId.toLowerCase();
        
        // Check label for facing mode indicators
        if (label.includes('front') || label.includes('user') || label.includes('selfie')) {
            return 'user';
        }
        if (label.includes('back') || label.includes('rear') || label.includes('environment')) {
            return 'environment';
        }
        
        // Check deviceId for facing mode indicators
        if (deviceId.includes('front') || deviceId.includes('user')) {
            return 'user';
        }
        if (deviceId.includes('back') || deviceId.includes('environment')) {
            return 'environment';
        }
        
        // Default assumption: first camera is usually back on mobile, front on desktop
        if (CameraManager.isMobileDevice()) {
            return index === 0 ? 'environment' : 'user';
        } else {
            return index === 0 ? 'user' : 'environment';
        }
    }

    // Helper method to restore previous camera on switch failure
    async _restorePreviousCamera() {
        const currentCamera = this.getCurrentCamera();
        if (!currentCamera) {
            throw new Error('No current camera to restore');
        }

        const constraints = {
            video: {
                deviceId: { exact: currentCamera.deviceId },
                width: { ideal: 1280 },
                height: { ideal: 720 },
                frameRate: { ideal: 30 }
            }
        };

        this.currentStream = await navigator.mediaDevices.getUserMedia(constraints);
        return this.currentStream;
    }

    // Helper method to identify which camera is currently active
    async _identifyCurrentCamera() {
        if (!this.currentStream || this.availableCameras.length === 0) {
            return;
        }

        try {
            // Get the video track from current stream
            const videoTrack = this.currentStream.getVideoTracks()[0];
            if (!videoTrack) return;

            // Get the device ID from the track settings
            const settings = videoTrack.getSettings();
            const activeDeviceId = settings.deviceId;

            // Find the matching camera in our available cameras list
            const cameraIndex = this.availableCameras.findIndex(
                camera => camera.deviceId === activeDeviceId
            );

            if (cameraIndex !== -1) {
                this.currentCameraIndex = cameraIndex;
            } else {
                // If we can't find exact match, try to match by facing mode
                const facingMode = settings.facingMode;
                if (facingMode) {
                    const facingIndex = this.availableCameras.findIndex(
                        camera => camera.facingMode === facingMode
                    );
                    if (facingIndex !== -1) {
                        this.currentCameraIndex = facingIndex;
                    }
                }
            }
        } catch (error) {
            console.warn('Could not identify current camera:', error);
            // Default to first camera if identification fails
            this.currentCameraIndex = 0;
        }
    }
}

/**
 * MediaCapture Class
 * Handles photo and video capture operations
 */
class MediaCapture {
    constructor(options = {}) {
        this.options = options;
        this.mediaRecorder = null;
        this.recordingStartTime = null;
        this.maxRecordingDuration = options.maxRecordingDuration || 120000; // 2 minutes
        this.recordedChunks = [];
        this.recordingTimer = null;
        
        // Enhanced photo capture settings
        this.photoQuality = options.photoQuality || 0.8;
        this.photoFormat = options.photoFormat || 'image/jpeg';
        this.maxPhotoSize = options.maxPhotoSize || 10 * 1024 * 1024; // 10MB
        this.minPhotoSize = options.minPhotoSize || 1024; // 1KB minimum
        
        // Enhanced video capture settings
        this.maxVideoSize = options.maxVideoSize || 50 * 1024 * 1024; // 50MB
        this.minVideoSize = options.minVideoSize || 10 * 1024; // 10KB minimum
        this.videoFormat = options.videoFormat || 'video/webm';
        this.videoQuality = options.videoQuality || 0.8;
        
        // Compression settings
        this.enableCompression = options.enableCompression !== false; // Default true
        this.compressionThreshold = options.compressionThreshold || 5 * 1024 * 1024; // 5MB
        this.compressionQuality = options.compressionQuality || 0.7;
        this.maxCompressionAttempts = options.maxCompressionAttempts || 3;
        
        // Validation settings
        this.allowedPhotoFormats = options.allowedPhotoFormats || ['image/jpeg', 'image/png', 'image/webp'];
        this.allowedVideoFormats = options.allowedVideoFormats || ['video/webm', 'video/mp4'];
        this.maxDimensions = options.maxDimensions || { width: 4096, height: 4096 };
        this.minDimensions = options.minDimensions || { width: 100, height: 100 };
        
        // Thumbnail settings
        this.thumbnailSize = options.thumbnailSize || 150;
        this.thumbnailQuality = options.thumbnailQuality || 0.7;
        this.thumbnailFormat = options.thumbnailFormat || 'image/jpeg';
    }

    async capturePhoto() {
        const videoElement = document.querySelector('.camera-preview video');
        if (!videoElement) {
            throw new Error('No video element found for photo capture');
        }

        if (!videoElement.videoWidth || !videoElement.videoHeight) {
            throw new Error('Video stream not ready for capture');
        }

        try {
            // Create canvas to capture frame
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            
            // Set canvas dimensions to match video
            canvas.width = videoElement.videoWidth;
            canvas.height = videoElement.videoHeight;
            
            // Ensure we have valid dimensions
            if (canvas.width === 0 || canvas.height === 0) {
                throw new Error('Invalid video dimensions for capture');
            }
            
            // Draw current video frame to canvas
            context.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
            
            // Convert canvas to blob with validation
            const photoBlob = await this._canvasToBlob(canvas);
            
            // Validate the captured photo
            this.validatePhoto(photoBlob);
            
            return photoBlob;
        } catch (error) {
            console.error('Photo capture failed:', error);
            throw error;
        }
    }

    async _canvasToBlob(canvas) {
        return new Promise((resolve, reject) => {
            canvas.toBlob((blob) => {
                if (blob && blob.size > 0) {
                    resolve(blob);
                } else {
                    reject(new Error('Failed to create photo blob'));
                }
            }, this.photoFormat, this.photoQuality);
        });
    }

    validatePhoto(photoBlob) {
        if (!photoBlob) {
            throw new Error('Photo blob is null or undefined');
        }

        if (photoBlob.size === 0) {
            throw new Error('Photo is empty');
        }

        if (photoBlob.size < this.minPhotoSize) {
            throw new Error(`Photo size (${photoBlob.size} bytes) is too small. Minimum size is ${this.minPhotoSize} bytes`);
        }

        if (photoBlob.size > this.maxPhotoSize) {
            throw new Error(`Photo size (${Math.round(photoBlob.size / 1024 / 1024)}MB) exceeds maximum allowed size (${Math.round(this.maxPhotoSize / 1024 / 1024)}MB)`);
        }

        if (!photoBlob.type || !this.allowedPhotoFormats.includes(photoBlob.type)) {
            throw new Error(`Invalid photo format '${photoBlob.type}'. Allowed formats: ${this.allowedPhotoFormats.join(', ')}`);
        }

        return true;
    }

    async validatePhotoDimensions(photoBlob) {
        const dimensions = await this._getImageDimensions(photoBlob);
        
        if (dimensions.width < this.minDimensions.width || dimensions.height < this.minDimensions.height) {
            throw new Error(`Photo dimensions (${dimensions.width}x${dimensions.height}) are too small. Minimum: ${this.minDimensions.width}x${this.minDimensions.height}`);
        }

        if (dimensions.width > this.maxDimensions.width || dimensions.height > this.maxDimensions.height) {
            throw new Error(`Photo dimensions (${dimensions.width}x${dimensions.height}) are too large. Maximum: ${this.maxDimensions.width}x${this.maxDimensions.height}`);
        }

        return dimensions;
    }

    async createPhotoThumbnail(photoBlob, maxSize = null) {
        const thumbnailSize = maxSize || this.thumbnailSize;
        
        return new Promise((resolve, reject) => {
            const img = new Image();
            
            img.onload = () => {
                try {
                    const canvas = document.createElement('canvas');
                    const context = canvas.getContext('2d');
                    
                    // Calculate thumbnail dimensions maintaining aspect ratio
                    let { width, height } = img;
                    
                    if (width > height) {
                        if (width > thumbnailSize) {
                            height = (height * thumbnailSize) / width;
                            width = thumbnailSize;
                        }
                    } else {
                        if (height > thumbnailSize) {
                            width = (width * thumbnailSize) / height;
                            height = thumbnailSize;
                        }
                    }
                    
                    canvas.width = Math.round(width);
                    canvas.height = Math.round(height);
                    
                    // Enable image smoothing for better quality
                    context.imageSmoothingEnabled = true;
                    context.imageSmoothingQuality = 'high';
                    
                    // Draw resized image
                    context.drawImage(img, 0, 0, canvas.width, canvas.height);
                    
                    // Convert to blob with optimized settings
                    canvas.toBlob((thumbnailBlob) => {
                        URL.revokeObjectURL(img.src);
                        if (thumbnailBlob) {
                            resolve(thumbnailBlob);
                        } else {
                            reject(new Error('Failed to create photo thumbnail'));
                        }
                    }, this.thumbnailFormat, this.thumbnailQuality);
                } catch (error) {
                    URL.revokeObjectURL(img.src);
                    reject(error);
                }
            };
            
            img.onerror = () => {
                URL.revokeObjectURL(img.src);
                reject(new Error('Failed to load image for thumbnail creation'));
            };
            
            img.src = URL.createObjectURL(photoBlob);
        });
    }

    async compressPhoto(photoBlob, targetQuality = null, maxAttempts = null) {
        if (!this.enableCompression || photoBlob.size <= this.compressionThreshold) {
            return photoBlob; // No compression needed
        }

        const quality = targetQuality || this.compressionQuality;
        const attempts = maxAttempts || this.maxCompressionAttempts;
        
        return new Promise((resolve, reject) => {
            const img = new Image();
            
            img.onload = () => {
                try {
                    const canvas = document.createElement('canvas');
                    const context = canvas.getContext('2d');
                    
                    // Use original dimensions for compression (not resizing)
                    canvas.width = img.naturalWidth;
                    canvas.height = img.naturalHeight;
                    
                    // Enable high-quality rendering
                    context.imageSmoothingEnabled = true;
                    context.imageSmoothingQuality = 'high';
                    
                    // Draw image
                    context.drawImage(img, 0, 0);
                    
                    // Try compression with decreasing quality
                    let currentQuality = quality;
                    let attemptCount = 0;
                    
                    const tryCompress = () => {
                        canvas.toBlob((compressedBlob) => {
                            URL.revokeObjectURL(img.src);
                            
                            if (!compressedBlob) {
                                reject(new Error('Failed to compress photo'));
                                return;
                            }
                            
                            // Check if compression was successful or if we've reached max attempts
                            if (compressedBlob.size <= this.maxPhotoSize || attemptCount >= attempts) {
                                resolve(compressedBlob);
                            } else {
                                // Try with lower quality
                                attemptCount++;
                                currentQuality = Math.max(0.1, currentQuality - 0.1);
                                tryCompress();
                            }
                        }, this.photoFormat, currentQuality);
                    };
                    
                    tryCompress();
                } catch (error) {
                    URL.revokeObjectURL(img.src);
                    reject(error);
                }
            };
            
            img.onerror = () => {
                URL.revokeObjectURL(img.src);
                reject(new Error('Failed to load image for compression'));
            };
            
            img.src = URL.createObjectURL(photoBlob);
        });
    }

    async processPhoto(photoBlob) {
        try {
            // Step 1: Basic validation
            this.validatePhoto(photoBlob);
            
            // Step 2: Validate dimensions
            const dimensions = await this.validatePhotoDimensions(photoBlob);
            
            // Step 3: Compress if needed
            let processedBlob = photoBlob;
            let compressionApplied = false;
            
            if (this.enableCompression && photoBlob.size > this.compressionThreshold) {
                try {
                    processedBlob = await this.compressPhoto(photoBlob);
                    compressionApplied = true;
                    console.log(`Photo compressed from ${Math.round(photoBlob.size / 1024)}KB to ${Math.round(processedBlob.size / 1024)}KB`);
                } catch (compressionError) {
                    console.warn('Photo compression failed, using original:', compressionError);
                    processedBlob = photoBlob;
                }
            }
            
            // Step 4: Final validation after compression
            this.validatePhoto(processedBlob);
            
            // Step 5: Create optimized thumbnail
            const thumbnailBlob = await this.createPhotoThumbnail(processedBlob);
            
            // Step 6: Generate comprehensive metadata
            const metadata = {
                size: processedBlob.size,
                originalSize: photoBlob.size,
                type: processedBlob.type,
                timestamp: new Date().toISOString(),
                dimensions: dimensions,
                compressionApplied: compressionApplied,
                compressionRatio: compressionApplied ? (photoBlob.size / processedBlob.size).toFixed(2) : 1,
                quality: this.photoQuality,
                thumbnailSize: thumbnailBlob.size,
                validation: {
                    passed: true,
                    checks: ['format', 'size', 'dimensions']
                }
            };
            
            // Return processed photo data
            return {
                original: processedBlob,
                thumbnail: thumbnailBlob,
                metadata: metadata
            };
        } catch (error) {
            console.error('Photo processing failed:', error);
            
            // Create error metadata for debugging
            const errorMetadata = {
                error: error.message,
                timestamp: new Date().toISOString(),
                originalSize: photoBlob?.size || 0,
                originalType: photoBlob?.type || 'unknown',
                validation: {
                    passed: false,
                    error: error.message
                }
            };
            
            throw new Error(`Photo processing failed: ${error.message}`);
        }
    }

    async _getImageDimensions(imageBlob) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            
            img.onload = () => {
                const dimensions = {
                    width: img.naturalWidth,
                    height: img.naturalHeight
                };
                URL.revokeObjectURL(img.src);
                resolve(dimensions);
            };
            
            img.onerror = () => {
                URL.revokeObjectURL(img.src);
                reject(new Error('Failed to get image dimensions'));
            };
            
            img.src = URL.createObjectURL(imageBlob);
        });
    }

    async startVideoRecording() {
        const videoElement = document.querySelector('.camera-preview video');
        if (!videoElement || !videoElement.srcObject) {
            throw new Error('No video stream available for recording');
        }

        try {
            const stream = videoElement.srcObject;
            
            // Check if MediaRecorder is supported
            if (!MediaRecorder.isTypeSupported('video/webm')) {
                throw new Error('Video recording not supported');
            }

            // Initialize MediaRecorder
            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'video/webm'
            });

            this.recordedChunks = [];
            this.recordingStartTime = Date.now();

            // Set up event handlers
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.recordedChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                console.log('Recording stopped');
            };

            this.mediaRecorder.onerror = (event) => {
                console.error('MediaRecorder error:', event.error);
            };

            // Start recording
            this.mediaRecorder.start();

            // Set up automatic stop timer
            this.recordingTimer = setTimeout(() => {
                if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
                    console.log('Recording reached maximum duration, stopping automatically');
                    this.stopVideoRecording();
                    
                    // Dispatch max duration reached event
                    const maxDurationEvent = new CustomEvent('video:max-duration-reached', {
                        detail: { duration: this.maxRecordingDuration }
                    });
                    document.dispatchEvent(maxDurationEvent);
                }
            }, this.maxRecordingDuration);

            return true;
        } catch (error) {
            console.error('Video recording start failed:', error);
            throw error;
        }
    }

    async stopVideoRecording() {
        if (!this.mediaRecorder || this.mediaRecorder.state !== 'recording') {
            throw new Error('No active recording to stop');
        }

        return new Promise((resolve, reject) => {
            this.mediaRecorder.onstop = () => {
                try {
                    // Create blob from recorded chunks
                    const blob = new Blob(this.recordedChunks, { type: 'video/webm' });
                    
                    // Validate the recorded video
                    this.validateVideo(blob);
                    
                    // Clean up
                    this.recordedChunks = [];
                    this.mediaRecorder = null;
                    
                    if (this.recordingTimer) {
                        clearTimeout(this.recordingTimer);
                        this.recordingTimer = null;
                    }
                    
                    resolve(blob);
                } catch (error) {
                    // Clean up on error
                    this.recordedChunks = [];
                    this.mediaRecorder = null;
                    
                    if (this.recordingTimer) {
                        clearTimeout(this.recordingTimer);
                        this.recordingTimer = null;
                    }
                    
                    reject(error);
                }
            };

            this.mediaRecorder.onerror = (event) => {
                reject(new Error('Recording failed: ' + event.error));
            };

            // Stop the recording
            this.mediaRecorder.stop();
        });
    }

    getRecordingDuration() {
        if (this.recordingStartTime) {
            return Date.now() - this.recordingStartTime;
        }
        return 0;
    }

    isRecording() {
        return this.mediaRecorder && this.mediaRecorder.state === 'recording';
    }

    async validateMediaComprehensive(blob, type) {
        const validationResults = {
            passed: false,
            checks: [],
            errors: [],
            warnings: [],
            metadata: {}
        };

        try {
            // Basic validation
            if (type === 'photo') {
                this.validatePhoto(blob);
                const dimensions = await this.validatePhotoDimensions(blob);
                validationResults.metadata.dimensions = dimensions;
                validationResults.checks.push('photo-format', 'photo-size', 'photo-dimensions');
            } else if (type === 'video') {
                this.validateVideo(blob);
                const metadata = await this.validateVideoDimensions(blob);
                validationResults.metadata = metadata;
                validationResults.checks.push('video-format', 'video-size', 'video-dimensions', 'video-duration');
            }

            // Check for compression needs
            const compressionThreshold = type === 'photo' ? this.compressionThreshold : this.compressionThreshold * 2;
            if (blob.size > compressionThreshold) {
                validationResults.warnings.push(`File size (${Math.round(blob.size / 1024 / 1024)}MB) is large and may benefit from compression`);
            }

            // Quality assessment
            if (type === 'photo') {
                const qualityScore = await this._assessPhotoQuality(blob);
                validationResults.metadata.qualityScore = qualityScore;
                if (qualityScore < 0.5) {
                    validationResults.warnings.push('Photo quality appears to be low');
                }
            }

            validationResults.passed = true;
            return validationResults;

        } catch (error) {
            validationResults.errors.push(error.message);
            validationResults.passed = false;
            return validationResults;
        }
    }

    async _assessPhotoQuality(photoBlob) {
        // Simple quality assessment based on file size vs dimensions
        try {
            const dimensions = await this._getImageDimensions(photoBlob);
            const pixelCount = dimensions.width * dimensions.height;
            const bytesPerPixel = photoBlob.size / pixelCount;
            
            // Higher bytes per pixel generally indicates better quality
            // This is a rough heuristic
            if (bytesPerPixel > 3) return 0.9; // High quality
            if (bytesPerPixel > 2) return 0.7; // Good quality
            if (bytesPerPixel > 1) return 0.5; // Medium quality
            return 0.3; // Low quality
        } catch (error) {
            return 0.5; // Default to medium quality if assessment fails
        }
    }

    // Legacy method for backward compatibility
    validateMedia(blob, type) {
        if (type === 'photo') {
            return this.validatePhoto(blob);
        } else if (type === 'video') {
            return this.validateVideo(blob);
        }
        throw new Error(`Unknown media type: ${type}`);
    }

    validateVideo(videoBlob) {
        if (!videoBlob) {
            throw new Error('Video blob is null or undefined');
        }

        if (videoBlob.size === 0) {
            throw new Error('Video is empty');
        }

        if (videoBlob.size < this.minVideoSize) {
            throw new Error(`Video size (${videoBlob.size} bytes) is too small. Minimum size is ${this.minVideoSize} bytes`);
        }

        if (videoBlob.size > this.maxVideoSize) {
            throw new Error(`Video size (${Math.round(videoBlob.size / 1024 / 1024)}MB) exceeds maximum allowed size (${Math.round(this.maxVideoSize / 1024 / 1024)}MB)`);
        }

        if (!videoBlob.type || !this.allowedVideoFormats.includes(videoBlob.type)) {
            throw new Error(`Invalid video format '${videoBlob.type}'. Allowed formats: ${this.allowedVideoFormats.join(', ')}`);
        }
        
        return true;
    }

    async validateVideoDimensions(videoBlob) {
        const metadata = await this._getVideoMetadata(videoBlob);
        const dimensions = metadata.dimensions;
        
        if (dimensions.width < this.minDimensions.width || dimensions.height < this.minDimensions.height) {
            throw new Error(`Video dimensions (${dimensions.width}x${dimensions.height}) are too small. Minimum: ${this.minDimensions.width}x${this.minDimensions.height}`);
        }

        if (dimensions.width > this.maxDimensions.width || dimensions.height > this.maxDimensions.height) {
            throw new Error(`Video dimensions (${dimensions.width}x${dimensions.height}) are too large. Maximum: ${this.maxDimensions.width}x${this.maxDimensions.height}`);
        }

        return metadata;
    }

    // Enhanced method to create thumbnail from video
    async createVideoThumbnail(videoBlob, maxSize = null) {
        const thumbnailSize = maxSize || this.thumbnailSize;
        
        return new Promise((resolve, reject) => {
            const video = document.createElement('video');
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            
            // Set video properties for better thumbnail extraction
            video.muted = true;
            video.playsInline = true;
            video.preload = 'metadata';

            video.onloadedmetadata = () => {
                // Calculate thumbnail dimensions maintaining aspect ratio
                let { videoWidth: width, videoHeight: height } = video;
                
                if (width === 0 || height === 0) {
                    URL.revokeObjectURL(video.src);
                    reject(new Error('Invalid video dimensions'));
                    return;
                }
                
                if (width > height) {
                    if (width > thumbnailSize) {
                        height = (height * thumbnailSize) / width;
                        width = thumbnailSize;
                    }
                } else {
                    if (height > thumbnailSize) {
                        width = (width * thumbnailSize) / height;
                        height = thumbnailSize;
                    }
                }
                
                canvas.width = Math.round(width);
                canvas.height = Math.round(height);
                
                // Seek to a good frame for thumbnail (25% into video or 2 seconds, whichever is smaller)
                const seekTime = Math.min(2, video.duration * 0.25);
                video.currentTime = seekTime;
            };

            video.onseeked = () => {
                try {
                    // Enable high-quality rendering
                    context.imageSmoothingEnabled = true;
                    context.imageSmoothingQuality = 'high';
                    
                    context.drawImage(video, 0, 0, canvas.width, canvas.height);
                    
                    canvas.toBlob((thumbnailBlob) => {
                        URL.revokeObjectURL(video.src);
                        if (thumbnailBlob) {
                            resolve(thumbnailBlob);
                        } else {
                            reject(new Error('Failed to create video thumbnail'));
                        }
                    }, this.thumbnailFormat, this.thumbnailQuality);
                } catch (error) {
                    URL.revokeObjectURL(video.src);
                    reject(error);
                }
            };

            video.onerror = (e) => {
                URL.revokeObjectURL(video.src);
                reject(new Error(`Failed to load video for thumbnail: ${e.message || 'Unknown error'}`));
            };

            // Add timeout to prevent hanging
            const timeout = setTimeout(() => {
                URL.revokeObjectURL(video.src);
                reject(new Error('Video thumbnail creation timed out'));
            }, 10000); // 10 second timeout

            video.onloadedmetadata = () => {
                clearTimeout(timeout);
                video.onloadedmetadata(); // Call the original handler
            };

            video.src = URL.createObjectURL(videoBlob);
        });
    }

    async compressVideo(videoBlob) {
        // Note: True video compression requires server-side processing or WebCodecs API
        // For now, we'll implement basic validation and metadata optimization
        
        if (!this.enableCompression || videoBlob.size <= this.compressionThreshold) {
            return videoBlob; // No compression needed
        }

        // For client-side video compression, we would need WebCodecs API or similar
        // This is a placeholder for future implementation
        console.warn('Video compression not yet implemented on client-side. Consider server-side compression.');
        
        // Return original blob for now
        return videoBlob;
    }

    async processVideo(videoBlob) {
        try {
            // Step 1: Basic validation
            this.validateVideo(videoBlob);
            
            // Step 2: Get metadata and validate dimensions
            const videoMetadata = await this.validateVideoDimensions(videoBlob);
            
            // Step 3: Attempt compression if needed (placeholder for now)
            let processedBlob = videoBlob;
            let compressionApplied = false;
            
            if (this.enableCompression && videoBlob.size > this.compressionThreshold) {
                try {
                    processedBlob = await this.compressVideo(videoBlob);
                    compressionApplied = processedBlob !== videoBlob;
                    if (compressionApplied) {
                        console.log(`Video compressed from ${Math.round(videoBlob.size / 1024)}KB to ${Math.round(processedBlob.size / 1024)}KB`);
                    }
                } catch (compressionError) {
                    console.warn('Video compression failed, using original:', compressionError);
                    processedBlob = videoBlob;
                }
            }
            
            // Step 4: Final validation after compression
            this.validateVideo(processedBlob);
            
            // Step 5: Create optimized thumbnail
            const thumbnailBlob = await this.createVideoThumbnail(processedBlob);
            
            // Step 6: Generate comprehensive metadata
            const metadata = {
                size: processedBlob.size,
                originalSize: videoBlob.size,
                type: processedBlob.type,
                timestamp: new Date().toISOString(),
                duration: videoMetadata.duration,
                dimensions: videoMetadata.dimensions,
                compressionApplied: compressionApplied,
                compressionRatio: compressionApplied ? (videoBlob.size / processedBlob.size).toFixed(2) : 1,
                quality: this.videoQuality,
                thumbnailSize: thumbnailBlob.size,
                frameRate: await this._estimateFrameRate(processedBlob),
                bitRate: this._calculateBitRate(processedBlob.size, videoMetadata.duration),
                validation: {
                    passed: true,
                    checks: ['format', 'size', 'dimensions', 'duration']
                }
            };
            
            // Return processed video data
            return {
                original: processedBlob,
                thumbnail: thumbnailBlob,
                metadata: metadata
            };
        } catch (error) {
            console.error('Video processing failed:', error);
            
            // Create error metadata for debugging
            const errorMetadata = {
                error: error.message,
                timestamp: new Date().toISOString(),
                originalSize: videoBlob?.size || 0,
                originalType: videoBlob?.type || 'unknown',
                validation: {
                    passed: false,
                    error: error.message
                }
            };
            
            throw new Error(`Video processing failed: ${error.message}`);
        }
    }

    _calculateBitRate(sizeBytes, durationMs) {
        if (!durationMs || durationMs === 0) return 0;
        // Convert to bits per second
        return Math.round((sizeBytes * 8) / (durationMs / 1000));
    }

    async _estimateFrameRate(videoBlob) {
        // This is a simplified estimation - in practice, you'd need more sophisticated analysis
        // For now, return a reasonable default based on video size and duration
        try {
            const metadata = await this._getVideoMetadata(videoBlob);
            // Rough estimation based on file size and duration
            const estimatedFrames = Math.round(metadata.duration / 1000 * 24); // Assume 24fps baseline
            return Math.min(30, Math.max(15, estimatedFrames / (metadata.duration / 1000)));
        } catch (error) {
            return 24; // Default frame rate
        }
    }

    async _getVideoMetadata(videoBlob) {
        return new Promise((resolve, reject) => {
            const video = document.createElement('video');
            
            video.onloadedmetadata = () => {
                const metadata = {
                    duration: video.duration * 1000, // Convert to milliseconds
                    dimensions: {
                        width: video.videoWidth,
                        height: video.videoHeight
                    }
                };
                URL.revokeObjectURL(video.src);
                resolve(metadata);
            };
            
            video.onerror = () => {
                URL.revokeObjectURL(video.src);
                reject(new Error('Failed to get video metadata'));
            };
            
            video.src = URL.createObjectURL(videoBlob);
        });
    }

    // Utility methods for media processing
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    formatDuration(milliseconds) {
        const seconds = Math.floor(milliseconds / 1000);
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        
        if (minutes > 0) {
            return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
        }
        return `${remainingSeconds}s`;
    }

    getMediaInfo(blob, metadata = {}) {
        const info = {
            size: this.formatFileSize(blob.size),
            sizeBytes: blob.size,
            type: blob.type,
            timestamp: new Date().toISOString()
        };

        if (metadata.dimensions) {
            info.dimensions = `${metadata.dimensions.width}x${metadata.dimensions.height}`;
            info.aspectRatio = (metadata.dimensions.width / metadata.dimensions.height).toFixed(2);
        }

        if (metadata.duration) {
            info.duration = this.formatDuration(metadata.duration);
            info.durationMs = metadata.duration;
        }

        if (metadata.bitRate) {
            info.bitRate = `${Math.round(metadata.bitRate / 1000)}kbps`;
        }

        return info;
    }

    // Enhanced cleanup with comprehensive resource management
    cleanup() {
        try {
            console.log('Starting MediaCapture cleanup...');
            
            // Stop recording if active with proper state management
            if (this.mediaRecorder) {
                if (this.mediaRecorder.state === 'recording') {
                    console.log('Stopping active recording during cleanup');
                    this.mediaRecorder.stop();
                }
                
                // Wait a brief moment for stop event to process
                setTimeout(() => {
                    this._cleanupMediaRecorder();
                }, 100);
            } else {
                this._cleanupMediaRecorder();
            }
            
            // Clear recording timer and intervals
            this._cleanupTimers();
            
            // Clean up recorded chunks and release memory
            this._cleanupRecordedChunks();
            
            // Reset all state variables
            this._resetState();
            
            console.log('MediaCapture cleanup completed successfully');
        } catch (error) {
            console.error('Error during MediaCapture cleanup:', error);
            // Force cleanup even if errors occur
            this._forceCleanup();
        }
    }

    _cleanupMediaRecorder() {
        if (this.mediaRecorder) {
            try {
                // Remove all event listeners to prevent memory leaks
                this.mediaRecorder.ondataavailable = null;
                this.mediaRecorder.onstop = null;
                this.mediaRecorder.onerror = null;
                this.mediaRecorder.onstart = null;
                this.mediaRecorder.onpause = null;
                this.mediaRecorder.onresume = null;
                
                // Clear the MediaRecorder reference
                this.mediaRecorder = null;
                
                console.log('MediaRecorder cleaned up successfully');
            } catch (error) {
                console.error('Error cleaning up MediaRecorder:', error);
                this.mediaRecorder = null; // Force null even on error
            }
        }
    }

    _cleanupTimers() {
        // Clear recording timer
        if (this.recordingTimer) {
            clearTimeout(this.recordingTimer);
            this.recordingTimer = null;
        }
        
        // Clear any other timers that might exist
        if (this.recordingInterval) {
            clearInterval(this.recordingInterval);
            this.recordingInterval = null;
        }
        
        // Clear duration update timer
        if (this.durationTimer) {
            clearInterval(this.durationTimer);
            this.durationTimer = null;
        }
    }

    _cleanupRecordedChunks() {
        try {
            // Clear recorded chunks array and help garbage collection
            if (this.recordedChunks && this.recordedChunks.length > 0) {
                console.log(`Cleaning up ${this.recordedChunks.length} recorded chunks`);
                this.recordedChunks.length = 0; // Clear array efficiently
                this.recordedChunks = [];
            }
        } catch (error) {
            console.error('Error cleaning up recorded chunks:', error);
            this.recordedChunks = []; // Force reset
        }
    }

    _resetState() {
        // Reset timing
        this.recordingStartTime = null;
        this.recordingDuration = 0;
        
        // Reset flags
        this.isRecording = false;
        this.isPaused = false;
        
        // Reset any cached streams
        this.currentStream = null;
    }

    _forceCleanup() {
        // Force cleanup in case of errors
        try {
            this.mediaRecorder = null;
            this.recordingTimer = null;
            this.recordingInterval = null;
            this.durationTimer = null;
            this.recordedChunks = [];
            this.recordingStartTime = null;
            this.recordingDuration = 0;
            this.isRecording = false;
            this.isPaused = false;
            this.currentStream = null;
            
            console.log('Force cleanup completed');
        } catch (error) {
            console.error('Error during force cleanup:', error);
        }
    }

    // Get current settings summary
    getSettings() {
        return {
            photo: {
                quality: this.photoQuality,
                format: this.photoFormat,
                maxSize: this.formatFileSize(this.maxPhotoSize),
                minSize: this.formatFileSize(this.minPhotoSize),
                allowedFormats: this.allowedPhotoFormats
            },
            video: {
                quality: this.videoQuality,
                format: this.videoFormat,
                maxSize: this.formatFileSize(this.maxVideoSize),
                minSize: this.formatFileSize(this.minVideoSize),
                maxDuration: this.formatDuration(this.maxRecordingDuration),
                allowedFormats: this.allowedVideoFormats
            },
            compression: {
                enabled: this.enableCompression,
                threshold: this.formatFileSize(this.compressionThreshold),
                quality: this.compressionQuality,
                maxAttempts: this.maxCompressionAttempts
            },
            dimensions: {
                max: `${this.maxDimensions.width}x${this.maxDimensions.height}`,
                min: `${this.minDimensions.width}x${this.minDimensions.height}`
            },
            thumbnail: {
                size: this.thumbnailSize,
                quality: this.thumbnailQuality,
                format: this.thumbnailFormat
            }
        };
    }
}/**
 * MediaPreview Class
 * Handles display of live camera preview and captured media
 */
class MediaPreview {
    constructor(options = {}) {
        this.options = options;
        this.previewElement = null;
        this.capturedMediaContainer = null;
        this.currentStream = null;
        this.qualityIndicator = null;
        this.qualityCheckInterval = null;
        this.orientationHandler = null;
        
        // Quality monitoring settings
        this.qualityThresholds = {
            lowLight: 50,    // Brightness threshold
            blurry: 0.3,     // Variance threshold for blur detection
            checkInterval: 2000  // Check every 2 seconds
        };
        
        // Responsive breakpoints
        this.breakpoints = {
            mobile: 768,
            tablet: 1024
        };
        
        this._setupOrientationHandler();
    }

    showLivePreview(stream, container) {
        try {
            // Create preview container if it doesn't exist
            if (!this.previewElement) {
                this._createPreviewElement(container);
            }

            // Set stream to video element
            this.previewElement.srcObject = stream;
            this.currentStream = stream;
            
            // Play the video
            this.previewElement.play();

            // Show the preview container
            const previewContainer = container.querySelector('.camera-preview');
            if (previewContainer) {
                previewContainer.style.display = 'block';
                this._updateResponsiveLayout(previewContainer);
            }

            // Start quality monitoring
            this._startQualityMonitoring();

            // Handle orientation changes
            this._handleOrientationChange();

            return true;
        } catch (error) {
            console.error('Failed to show live preview:', error);
            throw error;
        }
    }

    updateStream(newStream) {
        if (this.previewElement) {
            this.previewElement.srcObject = newStream;
            this.currentStream = newStream;
            
            // Restart quality monitoring with new stream
            this._stopQualityMonitoring();
            this._startQualityMonitoring();
        }
    }

    showCapturedMedia(blob, type, container, metadata = null) {
        try {
            if (!this.capturedMediaContainer) {
                this._createCapturedMediaContainer(container);
            }

            const mediaElement = this._createMediaElement(blob, type, metadata);
            
            // Add to grid container
            const mediaGrid = this.capturedMediaContainer.querySelector('.grid');
            if (mediaGrid) {
                mediaGrid.appendChild(mediaElement);
            } else {
                this.capturedMediaContainer.appendChild(mediaElement);
            }

            // Update media count
            this._updateMediaCount();

            return mediaElement;
        } catch (error) {
            console.error('Failed to show captured media:', error);
            throw error;
        }
    }

    showCapturedPhoto(photoData, container) {
        try {
            const mediaElement = this.showCapturedMedia(photoData.original, 'photo', container, photoData.metadata);
            
            // Add photo-specific data attributes
            mediaElement.dataset.photoSize = photoData.metadata.size;
            mediaElement.dataset.photoDimensions = `${photoData.metadata.dimensions.width}x${photoData.metadata.dimensions.height}`;
            
            return mediaElement;
        } catch (error) {
            console.error('Failed to show captured photo:', error);
            throw error;
        }
    }

    showCapturedVideo(videoBlob, container, metadata = null) {
        try {
            const videoMetadata = {
                size: videoBlob.size,
                type: videoBlob.type,
                timestamp: metadata?.timestamp || new Date().toISOString(),
                duration: metadata?.duration || 0,
                ...metadata
            };
            
            const mediaElement = this.showCapturedMedia(videoBlob, 'video', container, videoMetadata);
            
            // Add video-specific data attributes
            mediaElement.dataset.videoSize = videoMetadata.size;
            mediaElement.dataset.videoDuration = videoMetadata.duration;
            
            // Add duration overlay to video element
            const videoElement = mediaElement.querySelector('video');
            if (videoElement && videoMetadata.duration > 0) {
                const durationOverlay = document.createElement('div');
                durationOverlay.className = 'absolute bottom-1 right-1 bg-black bg-opacity-75 text-white text-xs px-2 py-1 rounded';
                durationOverlay.textContent = this._formatDuration(videoMetadata.duration);
                mediaElement.appendChild(durationOverlay);
            }
            
            return mediaElement;
        } catch (error) {
            console.error('Failed to show captured video:', error);
            throw error;
        }
    }

    createThumbnail(blob, type = 'photo') {
        return new Promise((resolve, reject) => {
            if (type === 'photo') {
                // For photos, create a smaller version
                const img = new Image();
                img.onload = () => {
                    const canvas = document.createElement('canvas');
                    const context = canvas.getContext('2d');
                    
                    // Set thumbnail dimensions
                    const maxSize = 150;
                    let { width, height } = img;
                    
                    if (width > height) {
                        if (width > maxSize) {
                            height = (height * maxSize) / width;
                            width = maxSize;
                        }
                    } else {
                        if (height > maxSize) {
                            width = (width * maxSize) / height;
                            height = maxSize;
                        }
                    }
                    
                    canvas.width = width;
                    canvas.height = height;
                    
                    context.drawImage(img, 0, 0, width, height);
                    
                    canvas.toBlob((thumbnailBlob) => {
                        URL.revokeObjectURL(img.src);
                        if (thumbnailBlob) {
                            resolve(URL.createObjectURL(thumbnailBlob));
                        } else {
                            reject(new Error('Failed to create thumbnail'));
                        }
                    }, 'image/jpeg', 0.7);
                };
                
                img.onerror = () => {
                    URL.revokeObjectURL(img.src);
                    reject(new Error('Failed to load image for thumbnail'));
                };
                
                img.src = URL.createObjectURL(blob);
            } else if (type === 'video') {
                // For videos, create thumbnail from first frame
                this._createVideoThumbnail(blob).then(resolve).catch(reject);
            }
        });
    }

    clearPreview() {
        try {
            console.log('Clearing camera preview and cleaning up resources...');
            
            // Stop quality monitoring
            this._stopQualityMonitoring();
            
            // Enhanced preview element cleanup
            if (this.previewElement) {
                // Stop any playing media
                if (this.previewElement.srcObject) {
                    // Stop all tracks in the stream
                    const stream = this.previewElement.srcObject;
                    if (stream && stream.getTracks) {
                        stream.getTracks().forEach(track => {
                            track.stop();
                        });
                    }
                }
                
                // Clear all media sources
                this.previewElement.srcObject = null;
                this.previewElement.src = '';
                this.previewElement.style.display = 'none';
                
                // Remove event listeners
                this.previewElement.onloadedmetadata = null;
                this.previewElement.oncanplay = null;
                this.previewElement.onerror = null;
                this.previewElement.onended = null;
            }

            // Hide preview container
            const previewContainer = document.querySelector('.camera-preview');
            if (previewContainer) {
                previewContainer.style.display = 'none';
            }

            // Clear quality indicator
            this._hideQualityIndicator();

            // Clear stream reference
            this.currentStream = null;
            
            // Clear any cached preview URLs
            this._cleanupPreviewUrls();
            
            console.log('Camera preview cleared successfully');
        } catch (error) {
            console.error('Error clearing camera preview:', error);
            // Force cleanup
            if (this.previewElement) {
                this.previewElement.srcObject = null;
                this.previewElement.src = '';
            }
            this.currentStream = null;
        }
    }

    _cleanupPreviewUrls() {
        // Clean up any preview-related blob URLs
        const previewProperties = [
            'previewUrl',
            'snapshotUrl',
            'qualityTestUrl'
        ];
        
        previewProperties.forEach(prop => {
            if (this[prop] && this[prop].startsWith('blob:')) {
                URL.revokeObjectURL(this[prop]);
                this[prop] = null;
            }
        });
    }

    clearCapturedMedia() {
        try {
            console.log('Clearing captured media and cleaning up blob URLs...');
            
            if (this.capturedMediaContainer) {
                // Enhanced blob URL cleanup
                const mediaElements = this.capturedMediaContainer.querySelectorAll('img, video, source');
                let cleanedUrls = 0;
                
                mediaElements.forEach(element => {
                    // Clean up src attribute
                    if (element.src && element.src.startsWith('blob:')) {
                        URL.revokeObjectURL(element.src);
                        element.src = '';
                        cleanedUrls++;
                    }
                    
                    // Clean up srcset attribute for responsive images
                    if (element.srcset) {
                        const srcsetUrls = element.srcset.split(',').map(s => s.trim().split(' ')[0]);
                        srcsetUrls.forEach(url => {
                            if (url.startsWith('blob:')) {
                                URL.revokeObjectURL(url);
                                cleanedUrls++;
                            }
                        });
                        element.srcset = '';
                    }
                    
                    // Clean up poster attribute for videos
                    if (element.poster && element.poster.startsWith('blob:')) {
                        URL.revokeObjectURL(element.poster);
                        element.poster = '';
                        cleanedUrls++;
                    }
                    
                    // Remove event listeners to prevent memory leaks
                    if (element.tagName === 'VIDEO') {
                        element.onloadeddata = null;
                        element.oncanplay = null;
                        element.onerror = null;
                        element.onended = null;
                    } else if (element.tagName === 'IMG') {
                        element.onload = null;
                        element.onerror = null;
                    }
                });
                
                console.log(`Cleaned up ${cleanedUrls} blob URLs from media elements`);
                
                // Clear container content
                this.capturedMediaContainer.innerHTML = '';
                
                // Clean up any stored references
                this._cleanupStoredReferences();
            }
            
            console.log('Captured media cleanup completed successfully');
        } catch (error) {
            console.error('Error clearing captured media:', error);
            // Force cleanup even on error
            if (this.capturedMediaContainer) {
                this.capturedMediaContainer.innerHTML = '';
            }
        }
    }

    _cleanupStoredReferences() {
        // Clean up any stored blob URLs in instance variables
        const blobProperties = [
            'lastCapturedPhotoUrl',
            'lastCapturedVideoUrl', 
            'previewThumbnailUrl',
            'tempBlobUrl'
        ];
        
        blobProperties.forEach(prop => {
            if (this[prop] && this[prop].startsWith('blob:')) {
                URL.revokeObjectURL(this[prop]);
                this[prop] = null;
            }
        });
    }

    _createPreviewElement(container) {
        // Create preview container with responsive classes
        const previewContainer = document.createElement('div');
        previewContainer.className = 'camera-preview relative bg-black rounded-lg overflow-hidden shadow-lg';
        previewContainer.style.display = 'none';

        // Create video element with responsive sizing
        this.previewElement = document.createElement('video');
        this.previewElement.className = 'preview-video w-full h-auto object-cover transition-all duration-300';
        this.previewElement.autoplay = true;
        this.previewElement.muted = true;
        this.previewElement.playsInline = true;

        // Add loading indicator
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'preview-loading absolute inset-0 flex items-center justify-center bg-gray-900 bg-opacity-75';
        loadingIndicator.innerHTML = `
            <div class="flex flex-col items-center space-y-2 text-white">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
                <span class="text-sm">Starting camera...</span>
            </div>
        `;

        // Create quality indicator container
        this.qualityIndicator = document.createElement('div');
        this.qualityIndicator.className = 'quality-indicator absolute top-2 left-2 right-2 z-10';
        this.qualityIndicator.style.display = 'none';

        // Add elements to preview container
        previewContainer.appendChild(this.previewElement);
        previewContainer.appendChild(loadingIndicator);
        previewContainer.appendChild(this.qualityIndicator);

        // Remove loading indicator when video starts playing
        this.previewElement.addEventListener('loadeddata', () => {
            loadingIndicator.style.display = 'none';
        });

        // Handle video load errors
        this.previewElement.addEventListener('error', () => {
            loadingIndicator.innerHTML = `
                <div class="flex flex-col items-center space-y-2 text-red-400">
                    <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                    </svg>
                    <span class="text-sm">Camera error</span>
                </div>
            `;
        });

        container.appendChild(previewContainer);
    }

    _createCapturedMediaContainer(container) {
        this.capturedMediaContainer = document.createElement('div');
        this.capturedMediaContainer.className = 'captured-media-container mt-4';
        
        const title = document.createElement('h4');
        title.className = 'text-sm font-medium text-gray-700 mb-2';
        title.textContent = 'Captured Media';
        
        const mediaGrid = document.createElement('div');
        mediaGrid.className = 'grid grid-cols-3 gap-2';
        
        this.capturedMediaContainer.appendChild(title);
        this.capturedMediaContainer.appendChild(mediaGrid);
        container.appendChild(this.capturedMediaContainer);
    }

    addPhotoToGallery(capturedMedia, container) {
        try {
            if (!this.capturedMediaContainer) {
                this._createCapturedMediaContainer(container);
            }

            const photoElement = this._createPhotoGalleryItem(capturedMedia);
            
            // Add to grid container
            const mediaGrid = this.capturedMediaContainer.querySelector('.grid');
            if (mediaGrid) {
                mediaGrid.appendChild(photoElement);
            }

            // Show the container if it was hidden
            this.capturedMediaContainer.style.display = 'block';

            return photoElement;
        } catch (error) {
            console.error('Failed to add photo to gallery:', error);
            throw error;
        }
    }

    _createPhotoGalleryItem(capturedMedia) {
        const photoContainer = document.createElement('div');
        photoContainer.className = 'relative bg-gray-100 rounded-lg overflow-hidden aspect-square group cursor-pointer hover:ring-2 hover:ring-blue-500 transition-all';
        photoContainer.dataset.mediaType = 'photo';
        photoContainer.dataset.mediaId = capturedMedia.id;

        // Create thumbnail image
        const thumbnailImg = document.createElement('img');
        thumbnailImg.className = 'w-full h-full object-cover';
        thumbnailImg.alt = 'Captured photo';
        
        // Use thumbnail blob if available, otherwise use original
        const imageBlob = capturedMedia.thumbnail || capturedMedia.blob;
        thumbnailImg.src = URL.createObjectURL(imageBlob);

        photoContainer.appendChild(thumbnailImg);

        // Add photo index overlay
        const indexOverlay = document.createElement('div');
        indexOverlay.className = 'absolute top-1 left-1 bg-black bg-opacity-75 text-white text-xs rounded-full w-6 h-6 flex items-center justify-center font-medium';
        const photoIndex = document.querySelectorAll('[data-media-type="photo"]').length + 1;
        indexOverlay.textContent = photoIndex;
        photoContainer.appendChild(indexOverlay);

        // Add metadata overlay
        const metadataOverlay = document.createElement('div');
        metadataOverlay.className = 'absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 text-white text-xs p-2 opacity-0 group-hover:opacity-100 transition-opacity';
        
        const sizeText = this._formatFileSize(capturedMedia.size);
        const dimensionsText = capturedMedia.metadata?.dimensions ? 
            `${capturedMedia.metadata.dimensions.width}×${capturedMedia.metadata.dimensions.height}` : '';
        
        metadataOverlay.innerHTML = `
            <div>${sizeText}</div>
            ${dimensionsText ? `<div>${dimensionsText}</div>` : ''}
        `;
        
        photoContainer.appendChild(metadataOverlay);

        // Add delete button
        const deleteButton = document.createElement('button');
        deleteButton.className = 'absolute top-1 right-1 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-red-600 opacity-0 group-hover:opacity-100 transition-opacity';
        deleteButton.innerHTML = '×';
        deleteButton.title = 'Delete photo';
        deleteButton.onclick = (e) => {
            e.stopPropagation();
            this._deletePhotoFromGallery(photoContainer, capturedMedia.id);
        };

        photoContainer.appendChild(deleteButton);

        // Add click handler for photo review
        photoContainer.onclick = () => {
            this._showPhotoReview(capturedMedia);
        };

        // Add loading indicator
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'absolute inset-0 flex items-center justify-center bg-gray-200';
        loadingIndicator.innerHTML = `
            <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
        `;
        photoContainer.appendChild(loadingIndicator);

        // Remove loading indicator when image loads
        thumbnailImg.onload = () => {
            loadingIndicator.remove();
        };

        // Handle image load errors
        thumbnailImg.onerror = () => {
            loadingIndicator.innerHTML = `
                <div class="text-red-500 text-xs text-center">
                    <svg class="w-6 h-6 mx-auto mb-1" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                    </svg>
                    Failed to load
                </div>
            `;
        };

        return photoContainer;
    }

    _deletePhotoFromGallery(photoContainer, mediaId) {
        // Clean up blob URL
        const img = photoContainer.querySelector('img');
        if (img && img.src && img.src.startsWith('blob:')) {
            URL.revokeObjectURL(img.src);
        }
        
        // Dispatch delete event to camera capture instance
        const deleteEvent = new CustomEvent('gallery:delete-photo', {
            detail: { mediaId: mediaId }
        });
        document.dispatchEvent(deleteEvent);
        
        // Remove container with animation
        photoContainer.style.transform = 'scale(0)';
        photoContainer.style.opacity = '0';
        setTimeout(() => {
            photoContainer.remove();
            this._updatePhotoIndices();
        }, 200);
    }

    _showPhotoReview(capturedMedia) {
        // Create modal for photo review
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4';
        
        const reviewContainer = document.createElement('div');
        reviewContainer.className = 'relative max-w-4xl max-h-full bg-white rounded-lg overflow-hidden';
        
        // Photo display
        const photoImg = document.createElement('img');
        photoImg.className = 'max-w-full max-h-96 object-contain';
        photoImg.src = URL.createObjectURL(capturedMedia.blob);
        photoImg.alt = 'Photo review';
        
        reviewContainer.appendChild(photoImg);
        
        // Photo info
        const infoContainer = document.createElement('div');
        infoContainer.className = 'p-4 bg-gray-50';
        
        const timestamp = new Date(capturedMedia.timestamp).toLocaleString();
        const sizeText = this._formatFileSize(capturedMedia.size);
        const dimensionsText = capturedMedia.metadata?.dimensions ? 
            `${capturedMedia.metadata.dimensions.width} × ${capturedMedia.metadata.dimensions.height}` : 'Unknown';
        
        infoContainer.innerHTML = `
            <div class="grid grid-cols-2 gap-4 text-sm">
                <div>
                    <span class="font-medium text-gray-700">Captured:</span>
                    <span class="text-gray-600">${timestamp}</span>
                </div>
                <div>
                    <span class="font-medium text-gray-700">Size:</span>
                    <span class="text-gray-600">${sizeText}</span>
                </div>
                <div>
                    <span class="font-medium text-gray-700">Dimensions:</span>
                    <span class="text-gray-600">${dimensionsText}</span>
                </div>
                <div>
                    <span class="font-medium text-gray-700">Format:</span>
                    <span class="text-gray-600">${capturedMedia.blob.type}</span>
                </div>
            </div>
        `;
        
        reviewContainer.appendChild(infoContainer);
        
        // Action buttons
        const buttonContainer = document.createElement('div');
        buttonContainer.className = 'p-4 bg-gray-50 border-t flex justify-between';
        
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors';
        deleteBtn.textContent = 'Delete Photo';
        deleteBtn.onclick = () => {
            this._deletePhotoFromGallery(
                document.querySelector(`[data-media-id="${capturedMedia.id}"]`), 
                capturedMedia.id
            );
            modal.remove();
        };
        
        const closeBtn = document.createElement('button');
        closeBtn.className = 'px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600 transition-colors';
        closeBtn.textContent = 'Close';
        closeBtn.onclick = () => modal.remove();
        
        buttonContainer.appendChild(deleteBtn);
        buttonContainer.appendChild(closeBtn);
        reviewContainer.appendChild(buttonContainer);
        
        // Add close button
        const closeButton = document.createElement('button');
        closeButton.className = 'absolute top-2 right-2 bg-black bg-opacity-50 text-white rounded-full w-8 h-8 flex items-center justify-center hover:bg-opacity-75';
        closeButton.innerHTML = '×';
        closeButton.onclick = () => modal.remove();
        
        reviewContainer.appendChild(closeButton);
        modal.appendChild(reviewContainer);
        
        // Close on backdrop click
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        };
        
        // Clean up blob URL when modal is removed
        const originalRemove = modal.remove.bind(modal);
        modal.remove = () => {
            if (photoImg.src && photoImg.src.startsWith('blob:')) {
                URL.revokeObjectURL(photoImg.src);
            }
            originalRemove();
        };
        
        document.body.appendChild(modal);
    }

    updatePhotoGalleryCount(count) {
        if (this.capturedMediaContainer) {
            const titleElement = this.capturedMediaContainer.querySelector('h4');
            if (titleElement) {
                titleElement.textContent = `Captured Photos (${count})`;
            }
            
            // Show/hide container based on count
            this.capturedMediaContainer.style.display = count > 0 ? 'block' : 'none';
        }
    }

    _updatePhotoIndices() {
        const photoContainers = document.querySelectorAll('[data-media-type="photo"]');
        photoContainers.forEach((container, index) => {
            const indexOverlay = container.querySelector('.absolute.top-1.left-1');
            if (indexOverlay) {
                indexOverlay.textContent = index + 1;
            }
        });
    }

    _createMediaElement(blob, type, metadata = null) {
        const mediaContainer = document.createElement('div');
        mediaContainer.className = 'relative bg-gray-100 rounded-lg overflow-hidden aspect-square group';
        mediaContainer.dataset.mediaType = type;
        mediaContainer.dataset.mediaId = this._generateMediaId();

        let mediaElement;
        if (type === 'photo') {
            mediaElement = document.createElement('img');
            mediaElement.className = 'w-full h-full object-cover';
            mediaElement.alt = 'Captured photo';
        } else if (type === 'video') {
            mediaElement = document.createElement('video');
            mediaElement.className = 'w-full h-full object-cover';
            mediaElement.controls = true;
            mediaElement.muted = true;
            mediaElement.preload = 'metadata';
            mediaElement.playsInline = true; // Important for mobile devices
            
            // Add play button overlay for better UX
            const playOverlay = document.createElement('div');
            playOverlay.className = 'absolute inset-0 flex items-center justify-center bg-black bg-opacity-30 opacity-100 transition-opacity hover:opacity-75';
            playOverlay.innerHTML = `
                <div class="bg-white bg-opacity-90 rounded-full p-3">
                    <svg class="w-8 h-8 text-gray-800" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clip-rule="evenodd"></path>
                    </svg>
                </div>
            `;
            
            // Hide overlay when video starts playing
            mediaElement.addEventListener('play', () => {
                playOverlay.style.display = 'none';
            });
            
            // Show overlay when video pauses or ends
            mediaElement.addEventListener('pause', () => {
                playOverlay.style.display = 'flex';
            });
            
            mediaElement.addEventListener('ended', () => {
                playOverlay.style.display = 'flex';
            });
            
            mediaContainer.appendChild(playOverlay);
        }

        mediaElement.src = URL.createObjectURL(blob);
        mediaContainer.appendChild(mediaElement);

        // Add loading indicator
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'absolute inset-0 flex items-center justify-center bg-gray-200';
        loadingIndicator.innerHTML = `
            <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
        `;
        mediaContainer.appendChild(loadingIndicator);

        // Remove loading indicator when media loads
        mediaElement.onload = mediaElement.onloadeddata = () => {
            loadingIndicator.remove();
        };

        // Add error handling
        mediaElement.onerror = () => {
            loadingIndicator.innerHTML = `
                <div class="text-red-500 text-xs text-center">
                    <svg class="w-6 h-6 mx-auto mb-1" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                    </svg>
                    Failed to load
                </div>
            `;
        };

        // Add metadata overlay for photos
        if (type === 'photo' && metadata) {
            const metadataOverlay = document.createElement('div');
            metadataOverlay.className = 'absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 text-white text-xs p-2 opacity-0 group-hover:opacity-100 transition-opacity';
            
            const sizeText = this._formatFileSize(metadata.size);
            const dimensionsText = metadata.dimensions ? `${metadata.dimensions.width}×${metadata.dimensions.height}` : '';
            
            metadataOverlay.innerHTML = `
                <div>${sizeText}</div>
                ${dimensionsText ? `<div>${dimensionsText}</div>` : ''}
            `;
            
            mediaContainer.appendChild(metadataOverlay);
        }

        // Add delete button
        const deleteButton = document.createElement('button');
        deleteButton.className = 'absolute top-1 right-1 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-red-600 opacity-0 group-hover:opacity-100 transition-opacity';
        deleteButton.innerHTML = '×';
        deleteButton.title = 'Delete media';
        deleteButton.onclick = (e) => {
            e.stopPropagation();
            this._deleteMediaElement(mediaContainer, mediaElement);
        };

        mediaContainer.appendChild(deleteButton);

        // Add click handler for preview
        mediaContainer.onclick = () => {
            this._showMediaPreview(mediaElement, type, metadata);
        };

        return mediaContainer;
    }

    _generateMediaId() {
        return 'media_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    _formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    _formatDuration(milliseconds) {
        const seconds = Math.floor(milliseconds / 1000);
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    _deleteMediaElement(container, mediaElement) {
        // Clean up blob URL
        if (mediaElement.src && mediaElement.src.startsWith('blob:')) {
            URL.revokeObjectURL(mediaElement.src);
        }
        
        // Dispatch delete event
        const deleteEvent = new CustomEvent('media:deleted', {
            detail: {
                mediaId: container.dataset.mediaId,
                mediaType: container.dataset.mediaType
            }
        });
        document.dispatchEvent(deleteEvent);
        
        // Remove container
        container.remove();
        
        // Update media count
        this._updateMediaCount();
    }

    _updateMediaCount() {
        const mediaGrid = this.capturedMediaContainer?.querySelector('.grid');
        const mediaCount = mediaGrid?.children.length || 0;
        
        const titleElement = this.capturedMediaContainer?.querySelector('h4');
        if (titleElement) {
            titleElement.textContent = `Captured Media (${mediaCount})`;
        }
        
        // Show/hide container based on count
        if (this.capturedMediaContainer) {
            this.capturedMediaContainer.style.display = mediaCount > 0 ? 'block' : 'none';
        }
    }

    _showMediaPreview(mediaElement, type, metadata) {
        // Create modal preview
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4';
        
        const previewContainer = document.createElement('div');
        previewContainer.className = 'relative max-w-4xl max-h-full bg-white rounded-lg overflow-hidden';
        
        let previewElement;
        if (type === 'photo') {
            previewElement = document.createElement('img');
            previewElement.className = 'max-w-full max-h-96 object-contain';
        } else {
            previewElement = document.createElement('video');
            previewElement.className = 'max-w-full max-h-96 object-contain';
            previewElement.controls = true;
        }
        
        previewElement.src = mediaElement.src;
        previewContainer.appendChild(previewElement);
        
        // Add close button
        const closeButton = document.createElement('button');
        closeButton.className = 'absolute top-2 right-2 bg-black bg-opacity-50 text-white rounded-full w-8 h-8 flex items-center justify-center hover:bg-opacity-75';
        closeButton.innerHTML = '×';
        closeButton.onclick = () => modal.remove();
        
        previewContainer.appendChild(closeButton);
        modal.appendChild(previewContainer);
        
        // Close on backdrop click
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        };
        
        document.body.appendChild(modal);
    }

    _createVideoThumbnail(videoBlob) {
        return new Promise((resolve, reject) => {
            const video = document.createElement('video');
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');

            video.onloadedmetadata = () => {
                // Set thumbnail dimensions
                const maxSize = 150;
                let { videoWidth: width, videoHeight: height } = video;
                
                if (width > height) {
                    if (width > maxSize) {
                        height = (height * maxSize) / width;
                        width = maxSize;
                    }
                } else {
                    if (height > maxSize) {
                        width = (width * maxSize) / height;
                        height = maxSize;
                    }
                }
                
                canvas.width = width;
                canvas.height = height;
                video.currentTime = 1; // Seek to 1 second
            };

            video.onseeked = () => {
                context.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                canvas.toBlob((thumbnailBlob) => {
                    URL.revokeObjectURL(video.src);
                    if (thumbnailBlob) {
                        resolve(URL.createObjectURL(thumbnailBlob));
                    } else {
                        reject(new Error('Failed to create video thumbnail'));
                    }
                }, 'image/jpeg', 0.7);
            };

            video.onerror = () => {
                URL.revokeObjectURL(video.src);
                reject(new Error('Failed to load video for thumbnail'));
            };

            video.src = URL.createObjectURL(videoBlob);
        });
    }

    _setupOrientationHandler() {
        this.orientationHandler = () => {
            // Debounce orientation changes
            clearTimeout(this.orientationTimeout);
            this.orientationTimeout = setTimeout(() => {
                this._handleOrientationChange();
            }, 100);
        };

        // Listen for orientation changes
        window.addEventListener('orientationchange', this.orientationHandler);
        window.addEventListener('resize', this.orientationHandler);
    }

    _handleOrientationChange() {
        const previewContainer = document.querySelector('.camera-preview');
        if (previewContainer) {
            this._updateResponsiveLayout(previewContainer);
        }
    }

    _updateResponsiveLayout(previewContainer) {
        const isMobile = window.innerWidth < this.breakpoints.mobile;
        const isTablet = window.innerWidth < this.breakpoints.tablet;
        const isLandscape = window.innerWidth > window.innerHeight;

        // Update preview container classes based on device and orientation
        if (isMobile) {
            if (isLandscape) {
                // Mobile landscape - smaller preview, controls on side
                previewContainer.className = 'camera-preview relative bg-black rounded-lg overflow-hidden shadow-lg max-h-64';
                this.previewElement.className = 'preview-video w-full h-full object-cover';
            } else {
                // Mobile portrait - larger preview, controls at bottom
                previewContainer.className = 'camera-preview relative bg-black rounded-lg overflow-hidden shadow-lg max-h-96';
                this.previewElement.className = 'preview-video w-full h-auto object-cover';
            }
        } else if (isTablet) {
            // Tablet - medium sized preview
            previewContainer.className = 'camera-preview relative bg-black rounded-lg overflow-hidden shadow-lg max-h-80';
            this.previewElement.className = 'preview-video w-full h-auto object-cover';
        } else {
            // Desktop - larger preview
            previewContainer.className = 'camera-preview relative bg-black rounded-lg overflow-hidden shadow-lg max-h-96';
            this.previewElement.className = 'preview-video w-full h-auto object-cover';
        }

        // Dispatch layout change event for controls to adjust
        const layoutEvent = new CustomEvent('preview:layout-changed', {
            detail: { isMobile, isTablet, isLandscape }
        });
        document.dispatchEvent(layoutEvent);
    }

    _startQualityMonitoring() {
        if (!this.previewElement || !this.currentStream) return;

        // Clear any existing monitoring
        this._stopQualityMonitoring();

        // Start monitoring interval
        this.qualityCheckInterval = setInterval(() => {
            this._checkPreviewQuality();
        }, this.qualityThresholds.checkInterval);
    }

    _stopQualityMonitoring() {
        if (this.qualityCheckInterval) {
            clearInterval(this.qualityCheckInterval);
            this.qualityCheckInterval = null;
        }
    }

    _checkPreviewQuality() {
        if (!this.previewElement || !this.previewElement.videoWidth) return;

        try {
            // Create canvas to analyze current frame
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            
            canvas.width = this.previewElement.videoWidth;
            canvas.height = this.previewElement.videoHeight;
            
            // Draw current frame
            context.drawImage(this.previewElement, 0, 0, canvas.width, canvas.height);
            
            // Get image data for analysis
            const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
            const data = imageData.data;
            
            // Analyze brightness
            const brightness = this._calculateBrightness(data);
            
            // Analyze blur (simplified variance-based detection)
            const blurLevel = this._calculateBlurLevel(data, canvas.width, canvas.height);
            
            // Update quality indicator based on analysis
            this._updateQualityIndicator(brightness, blurLevel);
            
        } catch (error) {
            console.warn('Quality monitoring failed:', error);
        }
    }

    _calculateBrightness(imageData) {
        let totalBrightness = 0;
        const pixelCount = imageData.length / 4;
        
        for (let i = 0; i < imageData.length; i += 4) {
            // Calculate luminance using standard formula
            const r = imageData[i];
            const g = imageData[i + 1];
            const b = imageData[i + 2];
            const brightness = (0.299 * r + 0.587 * g + 0.114 * b);
            totalBrightness += brightness;
        }
        
        return totalBrightness / pixelCount;
    }

    _calculateBlurLevel(imageData, width, height) {
        // Simplified blur detection using Laplacian variance
        let variance = 0;
        let mean = 0;
        const pixelCount = width * height;
        
        // Calculate mean
        for (let i = 0; i < imageData.length; i += 4) {
            const gray = (imageData[i] + imageData[i + 1] + imageData[i + 2]) / 3;
            mean += gray;
        }
        mean /= pixelCount;
        
        // Calculate variance (simplified)
        for (let i = 0; i < imageData.length; i += 4) {
            const gray = (imageData[i] + imageData[i + 1] + imageData[i + 2]) / 3;
            variance += Math.pow(gray - mean, 2);
        }
        
        return Math.sqrt(variance / pixelCount);
    }

    _updateQualityIndicator(brightness, blurLevel) {
        if (!this.qualityIndicator) return;

        const warnings = [];
        
        // Check for low light
        if (brightness < this.qualityThresholds.lowLight) {
            warnings.push({
                type: 'low-light',
                message: 'Low light detected - try moving to a brighter area',
                icon: '💡'
            });
        }
        
        // Check for blur
        if (blurLevel < this.qualityThresholds.blurry) {
            warnings.push({
                type: 'blur',
                message: 'Image may be blurry - hold device steady',
                icon: '📷'
            });
        }

        // Update indicator display
        if (warnings.length > 0) {
            this._showQualityWarnings(warnings);
        } else {
            this._hideQualityIndicator();
        }
    }

    _showQualityWarnings(warnings) {
        if (!this.qualityIndicator) return;

        const warningElements = warnings.map(warning => `
            <div class="quality-warning flex items-center space-x-2 bg-yellow-500 bg-opacity-90 text-white px-3 py-2 rounded-lg text-sm mb-1">
                <span class="text-base">${warning.icon}</span>
                <span>${warning.message}</span>
            </div>
        `).join('');

        this.qualityIndicator.innerHTML = warningElements;
        this.qualityIndicator.style.display = 'block';

        // Auto-hide warnings after 5 seconds if conditions improve
        clearTimeout(this.warningTimeout);
        this.warningTimeout = setTimeout(() => {
            this._hideQualityIndicator();
        }, 5000);
    }

    _hideQualityIndicator() {
        if (this.qualityIndicator) {
            this.qualityIndicator.style.display = 'none';
            this.qualityIndicator.innerHTML = '';
        }
        
        if (this.warningTimeout) {
            clearTimeout(this.warningTimeout);
            this.warningTimeout = null;
        }
    }

    // Utility method to check if device is in landscape mode
    _isLandscapeMode() {
        return window.innerWidth > window.innerHeight;
    }

    // Utility method to get current device type
    _getDeviceType() {
        const width = window.innerWidth;
        if (width < this.breakpoints.mobile) return 'mobile';
        if (width < this.breakpoints.tablet) return 'tablet';
        return 'desktop';
    }

    // Method to manually trigger quality check (for testing)
    checkQualityNow() {
        this._checkPreviewQuality();
    }

    // Method to get current quality metrics
    getCurrentQualityMetrics() {
        if (!this.previewElement || !this.previewElement.videoWidth) {
            return null;
        }

        try {
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            
            canvas.width = this.previewElement.videoWidth;
            canvas.height = this.previewElement.videoHeight;
            context.drawImage(this.previewElement, 0, 0, canvas.width, canvas.height);
            
            const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
            const brightness = this._calculateBrightness(imageData.data);
            const blurLevel = this._calculateBlurLevel(imageData.data, canvas.width, canvas.height);
            
            return {
                brightness,
                blurLevel,
                isLowLight: brightness < this.qualityThresholds.lowLight,
                isBlurry: blurLevel < this.qualityThresholds.blurry,
                resolution: `${canvas.width}x${canvas.height}`
            };
        } catch (error) {
            console.warn('Failed to get quality metrics:', error);
            return null;
        }
    }

    // Clean up resources
    cleanup() {
        // Stop quality monitoring
        this._stopQualityMonitoring();
        
        // Remove orientation handlers
        if (this.orientationHandler) {
            window.removeEventListener('orientationchange', this.orientationHandler);
            window.removeEventListener('resize', this.orientationHandler);
        }
        
        // Clear timeouts
        if (this.orientationTimeout) {
            clearTimeout(this.orientationTimeout);
        }
        if (this.warningTimeout) {
            clearTimeout(this.warningTimeout);
        }
        
        this.clearPreview();
        this.clearCapturedMedia();
        
        if (this.previewElement) {
            this.previewElement.remove();
            this.previewElement = null;
        }
        
        if (this.capturedMediaContainer) {
            this.capturedMediaContainer.remove();
            this.capturedMediaContainer = null;
        }
        
        if (this.qualityIndicator) {
            this.qualityIndicator.remove();
            this.qualityIndicator = null;
        }
    }
}/**
 *
 CameraControls Class
 * Handles UI controls and user interactions
 */
class CameraControls {
    constructor(options = {}) {
        this.options = options;
        this.controlsContainer = null;
        this.captureButton = null;
        this.recordButton = null;
        this.switchCameraButton = null;
        this.closeButton = null;
        this.currentMode = 'photo'; // 'photo' or 'video'
        this.eventListeners = [];
        this.currentOrientation = this._getOrientation();
        this.orientationHandler = null;
        this.hapticSupported = this._checkHapticSupport();
        
        // Touch-friendly sizing
        this.buttonSizes = {
            primary: { width: '4rem', height: '4rem' }, // 64px - main capture button
            secondary: { width: '3rem', height: '3rem' }, // 48px - other controls
            mobile: { width: '4.5rem', height: '4.5rem' } // 72px - larger for mobile
        };
        
        this._setupOrientationHandler();
    }

    renderControls(container, mode = 'photo') {
        this.currentMode = mode;
        
        // Remove existing controls
        this.cleanup();

        // Create controls container with responsive layout
        this.controlsContainer = document.createElement('div');
        this._updateControlsLayout();

        // Create controls based on mode
        if (mode === 'photo') {
            this._createPhotoControls();
        } else if (mode === 'video') {
            this._createVideoControls();
        }

        // Add common controls
        this._createCommonControls();

        // Find camera preview container and add controls
        const previewContainer = container.querySelector('.camera-preview');
        if (previewContainer) {
            previewContainer.appendChild(this.controlsContainer);
        }

        // Bind event listeners
        this.bindEventListeners();
        
        // Start orientation monitoring
        this._startOrientationMonitoring();
    }

    _createPhotoControls() {
        // Capture photo button - large and touch-friendly
        this.captureButton = document.createElement('button');
        this.captureButton.className = 'capture-btn bg-white border-4 border-gray-300 rounded-full flex items-center justify-center hover:border-blue-500 active:scale-95 transition-all duration-150 touch-manipulation';
        this._applySizing(this.captureButton, 'primary');
        
        this.captureButton.innerHTML = `
            <div class="bg-white rounded-full border-2 border-gray-400 transition-all duration-150" style="width: 75%; height: 75%;"></div>
        `;
        this.captureButton.title = 'Take Photo';
        this.captureButton.setAttribute('aria-label', 'Take Photo');

        this.controlsContainer.appendChild(this.captureButton);

        // Create photo count indicator
        this._createPhotoCountIndicator();
    }

    _createPhotoCountIndicator() {
        this.photoCountIndicator = document.createElement('div');
        this.photoCountIndicator.className = 'photo-count-indicator absolute bg-blue-500 text-white rounded-full min-w-6 h-6 flex items-center justify-center text-xs font-bold px-2 opacity-0 transition-all duration-200';
        this.photoCountIndicator.style.display = 'none';
        
        // Position the indicator relative to the capture button
        const orientation = this._getOrientation();
        if (orientation === 'portrait') {
            // Position above the capture button in portrait mode
            this.photoCountIndicator.style.top = '-2rem';
            this.photoCountIndicator.style.left = '50%';
            this.photoCountIndicator.style.transform = 'translateX(-50%)';
        } else {
            // Position to the left of the capture button in landscape mode
            this.photoCountIndicator.style.left = '-2.5rem';
            this.photoCountIndicator.style.top = '50%';
            this.photoCountIndicator.style.transform = 'translateY(-50%)';
        }
        
        this.controlsContainer.appendChild(this.photoCountIndicator);
    }

    updatePhotoCount(count) {
        if (!this.photoCountIndicator) {
            this._createPhotoCountIndicator();
        }
        
        if (count > 0) {
            this.photoCountIndicator.textContent = count.toString();
            this.photoCountIndicator.style.display = 'flex';
            this.photoCountIndicator.style.opacity = '1';
            
            // Add animation when count changes
            this.photoCountIndicator.style.transform += ' scale(1.2)';
            setTimeout(() => {
                if (this.photoCountIndicator) {
                    const currentTransform = this.photoCountIndicator.style.transform.replace(' scale(1.2)', '');
                    this.photoCountIndicator.style.transform = currentTransform;
                }
            }, 200);
        } else {
            this.photoCountIndicator.style.opacity = '0';
            setTimeout(() => {
                if (this.photoCountIndicator) {
                    this.photoCountIndicator.style.display = 'none';
                }
            }, 200);
        }
    }

    _createVideoControls() {
        // Record video button - large and touch-friendly
        this.recordButton = document.createElement('button');
        this.recordButton.className = 'record-btn bg-red-500 border-4 border-white rounded-full flex items-center justify-center hover:bg-red-600 active:scale-95 transition-all duration-150 touch-manipulation';
        this._applySizing(this.recordButton, 'primary');
        
        this.recordButton.innerHTML = `
            <div class="bg-white rounded-full transition-all duration-150" style="width: 40%; height: 40%;"></div>
        `;
        this.recordButton.title = 'Start Recording';
        this.recordButton.setAttribute('aria-label', 'Start Recording');

        this.controlsContainer.appendChild(this.recordButton);
    }

    _createCommonControls() {
        // Switch camera button (will be hidden if only one camera)
        this.switchCameraButton = document.createElement('button');
        this.switchCameraButton.className = 'switch-camera-btn bg-black bg-opacity-50 text-white rounded-full flex items-center justify-center hover:bg-opacity-70 active:scale-95 transition-all duration-150 touch-manipulation';
        this._applySizing(this.switchCameraButton, 'secondary');
        
        this.switchCameraButton.innerHTML = `
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
        `;
        this.switchCameraButton.title = 'Switch Camera';
        this.switchCameraButton.setAttribute('aria-label', 'Switch Camera');

        // Close button
        this.closeButton = document.createElement('button');
        this.closeButton.className = 'close-btn bg-black bg-opacity-50 text-white rounded-full flex items-center justify-center hover:bg-opacity-70 active:scale-95 transition-all duration-150 touch-manipulation';
        this._applySizing(this.closeButton, 'secondary');
        
        this.closeButton.innerHTML = `
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
        `;
        this.closeButton.title = 'Close Camera';
        this.closeButton.setAttribute('aria-label', 'Close Camera');

        // Add buttons to container
        this.controlsContainer.appendChild(this.switchCameraButton);
        this.controlsContainer.appendChild(this.closeButton);
    }

    bindEventListeners() {
        // Photo capture
        if (this.captureButton) {
            const captureHandler = this._handlePhotoCapture.bind(this);
            this.captureButton.addEventListener('click', captureHandler);
            this.eventListeners.push({ element: this.captureButton, event: 'click', handler: captureHandler });
        }

        // Video recording
        if (this.recordButton) {
            const recordHandler = this._handleVideoRecord.bind(this);
            this.recordButton.addEventListener('click', recordHandler);
            this.eventListeners.push({ element: this.recordButton, event: 'click', handler: recordHandler });
        }

        // Camera switch
        if (this.switchCameraButton) {
            const switchHandler = this._handleCameraSwitch.bind(this);
            this.switchCameraButton.addEventListener('click', switchHandler);
            this.eventListeners.push({ element: this.switchCameraButton, event: 'click', handler: switchHandler });
        }

        // Close camera
        if (this.closeButton) {
            const closeHandler = this._handleClose.bind(this);
            this.closeButton.addEventListener('click', closeHandler);
            this.eventListeners.push({ element: this.closeButton, event: 'click', handler: closeHandler });
        }
    }

    updateControlStates(cameraCapture) {
        // Update switch camera button visibility and state
        if (this.switchCameraButton && cameraCapture.cameraManager) {
            const hasMultipleCameras = cameraCapture.cameraManager.hasMultipleCameras();
            const availableCameras = cameraCapture.state.availableCameras;
            
            if (hasMultipleCameras) {
                this.switchCameraButton.style.display = 'flex';
                
                // Update button title with current camera info
                const currentCamera = cameraCapture.cameraManager.getCurrentCamera();
                if (currentCamera && availableCameras.length > 1) {
                    const nextIndex = (cameraCapture.cameraManager.currentCameraIndex + 1) % availableCameras.length;
                    const nextCamera = availableCameras[nextIndex];
                    this.switchCameraButton.title = `Switch to ${nextCamera.label}`;
                    this.switchCameraButton.setAttribute('aria-label', `Switch to ${nextCamera.label}`);
                } else {
                    this.switchCameraButton.title = 'Switch Camera';
                    this.switchCameraButton.setAttribute('aria-label', 'Switch Camera');
                }
                
                // Enable/disable button based on camera availability
                this.switchCameraButton.disabled = false;
                this.switchCameraButton.style.opacity = '1';
            } else {
                this.switchCameraButton.style.display = 'none';
            }
        }

        // Update recording button state
        if (this.recordButton && cameraCapture.state.isRecording) {
            this.recordButton.className = 'record-btn bg-gray-500 border-4 border-white rounded-full w-16 h-16 flex items-center justify-center';
            this.recordButton.innerHTML = `
                <div class="bg-white rounded w-6 h-6"></div>
            `;
            this.recordButton.title = 'Stop Recording';
        }
    }

    showRecordingIndicator() {
        // Create recording indicator if it doesn't exist
        let indicator = this.controlsContainer.querySelector('.recording-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'recording-indicator absolute top-4 left-4 bg-red-500 text-white px-3 py-1 rounded-full text-sm font-medium flex items-center space-x-2';
            indicator.innerHTML = `
                <div class="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                <span class="recording-time">00:00</span>
            `;
            
            // Add to preview container instead of controls container
            const previewContainer = this.controlsContainer.closest('.camera-preview');
            if (previewContainer) {
                previewContainer.appendChild(indicator);
            }
        }

        // Start timer
        this._startRecordingTimer();
    }

    hideRecordingIndicator() {
        const indicator = document.querySelector('.recording-indicator');
        if (indicator) {
            indicator.remove();
        }
        
        if (this.recordingTimer) {
            clearInterval(this.recordingTimer);
            this.recordingTimer = null;
        }
    }

    _handlePhotoCapture(event) {
        event.preventDefault();
        
        // Add haptic feedback
        this._triggerHapticFeedback('light');
        
        // Add visual feedback
        this._showCaptureFlash();
        
        // Add button animation feedback
        this._animateButton(this.captureButton);
        
        // Dispatch custom event
        const captureEvent = new CustomEvent('camera:capture-photo');
        document.dispatchEvent(captureEvent);
    }

    _handleVideoRecord(event) {
        event.preventDefault();
        
        // Add haptic feedback
        this._triggerHapticFeedback('medium');
        
        // Add button animation feedback
        this._animateButton(this.recordButton);
        
        // Dispatch custom event
        const recordEvent = new CustomEvent('camera:toggle-recording');
        document.dispatchEvent(recordEvent);
    }

    _handleCameraSwitch(event) {
        event.preventDefault();
        
        // Prevent multiple rapid switches
        if (this.switchCameraButton.disabled) {
            return;
        }
        
        // Add haptic feedback
        this._triggerHapticFeedback('light');
        
        // Add button animation feedback
        this._animateButton(this.switchCameraButton);
        
        // Disable button temporarily to prevent rapid switching
        this.switchCameraButton.disabled = true;
        this.switchCameraButton.style.opacity = '0.6';
        
        // Show switching indicator
        this._showSwitchingIndicator();
        
        // Dispatch custom event
        const switchEvent = new CustomEvent('camera:switch-camera');
        document.dispatchEvent(switchEvent);
        
        // Re-enable button after a short delay
        setTimeout(() => {
            this.switchCameraButton.disabled = false;
            this.switchCameraButton.style.opacity = '1';
            this._hideSwitchingIndicator();
        }, 1000);
    }

    _handleClose(event) {
        event.preventDefault();
        
        // Add haptic feedback
        this._triggerHapticFeedback('light');
        
        // Add button animation feedback
        this._animateButton(this.closeButton);
        
        // Dispatch custom event
        const closeEvent = new CustomEvent('camera:close');
        document.dispatchEvent(closeEvent);
    }

    _showCaptureFlash() {
        // Create flash overlay
        const flash = document.createElement('div');
        flash.className = 'absolute inset-0 bg-white opacity-0 pointer-events-none';
        
        const previewContainer = this.controlsContainer.closest('.camera-preview');
        if (previewContainer) {
            previewContainer.appendChild(flash);
            
            // Animate flash
            flash.style.opacity = '0.8';
            setTimeout(() => {
                flash.style.opacity = '0';
                setTimeout(() => flash.remove(), 200);
            }, 100);
        }
    }

    _startRecordingTimer() {
        let seconds = 0;
        this.recordingTimer = setInterval(() => {
            seconds++;
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            const timeString = `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
            
            const timeElement = document.querySelector('.recording-time');
            if (timeElement) {
                timeElement.textContent = timeString;
            }
        }, 1000);
    }

    // Helper methods for responsive layout and touch interactions
    
    _getOrientation() {
        if (screen.orientation) {
            return screen.orientation.angle === 0 || screen.orientation.angle === 180 ? 'portrait' : 'landscape';
        } else if (window.orientation !== undefined) {
            return Math.abs(window.orientation) === 90 ? 'landscape' : 'portrait';
        }
        return window.innerWidth > window.innerHeight ? 'landscape' : 'portrait';
    }

    _updateControlsLayout() {
        const orientation = this._getOrientation();
        const isMobile = this._isMobileDevice();
        
        // Base classes for controls container
        let containerClasses = 'camera-controls absolute inset-0 flex items-center justify-center pointer-events-none';
        
        if (orientation === 'portrait') {
            // Portrait layout - controls at bottom
            containerClasses = 'camera-controls absolute bottom-0 left-0 right-0 flex flex-col items-center justify-end p-4 pointer-events-none';
            
            // Create control row for buttons
            const controlRow = document.createElement('div');
            controlRow.className = 'flex items-center justify-center space-x-4 mb-4';
            
            // Main capture button container
            const captureContainer = document.createElement('div');
            captureContainer.className = 'relative flex items-center justify-center';
            
            this.controlsContainer.className = containerClasses;
            this.controlsContainer.appendChild(controlRow);
            this.controlsContainer.appendChild(captureContainer);
            
        } else {
            // Landscape layout - controls on right side
            containerClasses = 'camera-controls absolute top-0 right-0 bottom-0 flex flex-col items-center justify-center p-4 pointer-events-none';
            
            // Create control column for buttons
            const controlColumn = document.createElement('div');
            controlColumn.className = 'flex flex-col items-center justify-center space-y-4 mr-4';
            
            // Main capture button container
            const captureContainer = document.createElement('div');
            captureContainer.className = 'relative flex items-center justify-center';
            
            this.controlsContainer.className = containerClasses;
            this.controlsContainer.appendChild(controlColumn);
            this.controlsContainer.appendChild(captureContainer);
        }
        
        // Add mobile-specific classes
        if (isMobile) {
            this.controlsContainer.classList.add('mobile-controls');
        }
    }

    updateLayoutForOrientation(orientation) {
        if (!this.controlsContainer) return;
        
        this.currentOrientation = orientation;
        
        // Remove existing layout classes
        this.controlsContainer.className = this.controlsContainer.className
            .replace(/camera-controls.*?pointer-events-none/g, '')
            .trim();
        
        // Apply new layout
        this._updateControlsLayout();
        
        // Reposition photo count indicator if it exists
        if (this.photoCountIndicator) {
            this._repositionPhotoCountIndicator(orientation);
        }
        
        // Update button sizes for orientation
        this._updateButtonSizesForOrientation(orientation);
    }

    _repositionPhotoCountIndicator(orientation) {
        if (!this.photoCountIndicator) return;
        
        // Reset positioning styles
        this.photoCountIndicator.style.top = '';
        this.photoCountIndicator.style.left = '';
        this.photoCountIndicator.style.right = '';
        this.photoCountIndicator.style.bottom = '';
        this.photoCountIndicator.style.transform = '';
        
        if (orientation === 'portrait' || orientation === 'portrait-primary' || orientation === 'portrait-secondary') {
            // Position above the capture button in portrait mode
            this.photoCountIndicator.style.top = '-2rem';
            this.photoCountIndicator.style.left = '50%';
            this.photoCountIndicator.style.transform = 'translateX(-50%)';
        } else {
            // Position to the left of the capture button in landscape mode
            this.photoCountIndicator.style.left = '-2.5rem';
            this.photoCountIndicator.style.top = '50%';
            this.photoCountIndicator.style.transform = 'translateY(-50%)';
        }
    }

    _updateButtonSizesForOrientation(orientation) {
        const isMobile = this._isMobileDevice();
        const isLandscape = orientation.includes('landscape');
        
        // Adjust button sizes based on orientation and device type
        const sizeKey = isMobile ? (isLandscape ? 'primary' : 'mobile') : 'primary';
        
        if (this.captureButton) {
            this._applySizing(this.captureButton, sizeKey);
        }
        
        if (this.recordButton) {
            this._applySizing(this.recordButton, sizeKey);
        }
        
        // Secondary buttons stay the same size
        if (this.switchCameraButton) {
            this._applySizing(this.switchCameraButton, 'secondary');
        }
        
        if (this.closeButton) {
            this._applySizing(this.closeButton, 'secondary');
        }
    }

    _applySizing(button, sizeKey) {
        const size = this.buttonSizes[sizeKey] || this.buttonSizes.primary;
        button.style.width = size.width;
        button.style.height = size.height;
        button.style.minWidth = size.width;
        button.style.minHeight = size.height;
        
        // Ensure pointer events are enabled for buttons
        button.style.pointerEvents = 'auto';
    }

    _setupOrientationHandler() {
        if (this._isMobileDevice()) {
            // Listen for orientation changes
            if (screen.orientation) {
                screen.orientation.addEventListener('change', () => {
                    setTimeout(() => {
                        this.updateLayoutForOrientation(this._getOrientation());
                    }, 100);
                });
            } else {
                window.addEventListener('orientationchange', () => {
                    setTimeout(() => {
                        this.updateLayoutForOrientation(this._getOrientation());
                    }, 100);
                });
            }
        }
    }

    _startOrientationMonitoring() {
        if (!this._isMobileDevice()) return;
        
        // Monitor orientation changes during camera use
        this.orientationMonitor = setInterval(() => {
            const currentOrientation = this._getOrientation();
            if (currentOrientation !== this.currentOrientation) {
                this.updateLayoutForOrientation(currentOrientation);
            }
        }, 500);
    }

    _stopOrientationMonitoring() {
        if (this.orientationMonitor) {
            clearInterval(this.orientationMonitor);
            this.orientationMonitor = null;
        }
    }

    _animateButton(button) {
        if (!button) return;
        
        // Add scale animation
        button.style.transform = 'scale(0.95)';
        button.style.transition = 'transform 0.1s ease-in-out';
        
        setTimeout(() => {
            button.style.transform = 'scale(1)';
        }, 100);
    }

    _triggerHapticFeedback(intensity = 'light') {
        if (!this.hapticSupported || !this._isMobileDevice()) return;
        
        try {
            if (navigator.vibrate) {
                const patterns = {
                    light: [10],
                    medium: [20],
                    heavy: [30, 10, 30]
                };
                navigator.vibrate(patterns[intensity] || patterns.light);
            }
        } catch (error) {
            console.warn('Haptic feedback failed:', error);
        }
    }

    _showSwitchingIndicator() {
        // Create switching indicator
        let indicator = document.querySelector('.switching-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'switching-indicator absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-black bg-opacity-75 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center space-x-2';
            indicator.innerHTML = `
                <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                </svg>
                <span>Switching...</span>
            `;
            
            const previewContainer = this.controlsContainer.closest('.camera-preview');
            if (previewContainer) {
                previewContainer.appendChild(indicator);
            }
        }
    }

    _hideSwitchingIndicator() {
        const indicator = document.querySelector('.switching-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    _checkHapticSupport() {
        return 'vibrate' in navigator || 'hapticFeedback' in navigator;
    }

    cleanup() {
        // Stop orientation monitoring
        this._stopOrientationMonitoring();
        
        // Remove event listeners
        this.eventListeners.forEach(({ element, event, handler }) => {
            element.removeEventListener(event, handler);
        });
        this.eventListeners = [];

        // Remove recording indicator
        this.hideRecordingIndicator();

        // Remove controls container
        if (this.controlsContainer) {
            this.controlsContainer.remove();
            this.controlsContainer = null;
        }

        // Reset button references
        this.captureButton = null;
        this.recordButton = null;
        this.switchCameraButton = null;
        this.closeButton = null;
        this.photoCountIndicator = null;
    }

    _showSwitchingIndicator() {
        // Remove existing indicator
        this._hideSwitchingIndicator();
        
        // Create switching indicator
        const indicator = document.createElement('div');
        indicator.className = 'camera-switching-indicator absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-black bg-opacity-75 text-white px-4 py-2 rounded-lg text-sm font-medium flex items-center space-x-2 z-50';
        indicator.innerHTML = `
            <div class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
            <span>Switching camera...</span>
        `;
        
        // Add to preview container
        const previewContainer = this.controlsContainer.closest('.camera-preview');
        if (previewContainer) {
            previewContainer.appendChild(indicator);
        }
    }

    _hideSwitchingIndicator() {
        const indicator = document.querySelector('.camera-switching-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
}

/**
 * FallbackHandler Class
 * Handles graceful degradation to file upload when camera is unavailable
 */
class FallbackHandler {
    constructor(options = {}) {
        this.options = options;
        this.fallbackContainer = null;
        this.supportStatus = {
            getUserMedia: false,
            mediaRecorder: false,
            enumerateDevices: false,
            isSecureContext: false
        };
    }

    async checkCameraSupport() {
        try {
            // Check if we're in a secure context (HTTPS or localhost)
            this.supportStatus.isSecureContext = window.isSecureContext || 
                location.protocol === 'https:' || 
                location.hostname === 'localhost' || 
                location.hostname === '127.0.0.1';

            if (!this.supportStatus.isSecureContext) {
                console.warn('Camera API requires HTTPS or localhost');
                return false;
            }

            // Check if navigator.mediaDevices exists
            if (!navigator.mediaDevices) {
                console.warn('navigator.mediaDevices not supported');
                return false;
            }

            // Check if getUserMedia is supported
            this.supportStatus.getUserMedia = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
            if (!this.supportStatus.getUserMedia) {
                console.warn('getUserMedia not supported');
                return false;
            }

            // Check if enumerateDevices is supported
            this.supportStatus.enumerateDevices = !!(navigator.mediaDevices && navigator.mediaDevices.enumerateDevices);
            if (!this.supportStatus.enumerateDevices) {
                console.warn('enumerateDevices not supported');
            }

            // Check if MediaRecorder is supported for video
            this.supportStatus.mediaRecorder = !!(window.MediaRecorder && MediaRecorder.isTypeSupported);
            if (!this.supportStatus.mediaRecorder) {
                console.warn('MediaRecorder not supported - video recording will be unavailable');
            }

            // Test basic camera access (without actually requesting permissions)
            try {
                // Check if we can at least enumerate devices
                if (this.supportStatus.enumerateDevices) {
                    const devices = await navigator.mediaDevices.enumerateDevices();
                    const videoDevices = devices.filter(device => device.kind === 'videoinput');
                    
                    if (videoDevices.length === 0) {
                        console.warn('No video input devices found');
                        return false;
                    }
                }
            } catch (enumerateError) {
                console.warn('Device enumeration failed:', enumerateError);
                // Don't fail completely, as this might work with permissions
            }

            return true;
        } catch (error) {
            console.error('Camera support check failed:', error);
            return false;
        }
    }

    showFallbackInterface(container = null, message = null) {
        // Find container if not provided
        if (!container) {
            container = document.querySelector('.camera-capture-container') || 
                       document.querySelector('.camera-container') ||
                       document.body;
        }

        if (!container) {
            console.error('No container found for fallback interface');
            return;
        }

        // Remove existing fallback interface
        this.hideFallbackInterface();

        // Create fallback container
        this.fallbackContainer = document.createElement('div');
        this.fallbackContainer.className = 'camera-fallback bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-6 text-center';

        // Default message
        const defaultMessage = 'Camera not available. Please use the file upload option below.';
        const displayMessage = message || defaultMessage;

        this.fallbackContainer.innerHTML = `
            <div class="flex flex-col items-center space-y-4">
                <svg class="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"></path>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"></path>
                </svg>
                <div>
                    <h3 class="text-lg font-medium text-gray-900 mb-2">Camera Unavailable</h3>
                    <p class="text-gray-600">${displayMessage}</p>
                </div>
            </div>
        `;

        container.appendChild(this.fallbackContainer);
        
        // Dispatch event to notify that fallback interface is shown
        const fallbackEvent = new CustomEvent('camera:fallback-shown', {
            detail: { 
                reason: 'general',
                container: container,
                supportStatus: this.supportStatus
            }
        });
        document.dispatchEvent(fallbackEvent);
    }

    handlePermissionDenied(container = null, context = 'general') {
        const browserName = FallbackHandler.getBrowserName();
        const isMobile = FallbackHandler.isMobileDevice();
        const isIOS = FallbackHandler.isIOSDevice();
        
        let instructions = '';
        let troubleshooting = '';
        
        if (isMobile) {
            if (isIOS) {
                instructions = `
                    <div class="space-y-3">
                        <div class="bg-blue-50 p-3 rounded-lg">
                            <h4 class="font-semibold text-blue-900 mb-2">📱 Enable Camera on iOS Safari:</h4>
                            <ol class="list-decimal list-inside space-y-1 text-sm text-blue-800">
                                <li>Look for the camera icon in the address bar</li>
                                <li>Tap "Allow" when prompted for camera access</li>
                                <li>If you missed the prompt, tap the "aA" icon and select "Website Settings"</li>
                                <li>Enable "Camera" permission</li>
                                <li>Refresh this page</li>
                            </ol>
                        </div>
                    </div>
                `;
                troubleshooting = `
                    <div class="mt-4 p-3 bg-yellow-50 rounded-lg">
                        <h5 class="font-medium text-yellow-800 mb-2">Still having trouble?</h5>
                        <ul class="text-sm text-yellow-700 space-y-1">
                            <li>• Check if camera access is restricted in Settings → Screen Time → Content & Privacy</li>
                            <li>• Try closing and reopening Safari</li>
                            <li>• Make sure iOS is up to date</li>
                        </ul>
                    </div>
                `;
            } else {
                instructions = `
                    <div class="space-y-3">
                        <div class="bg-green-50 p-3 rounded-lg">
                            <h4 class="font-semibold text-green-900 mb-2">📱 Enable Camera on Android:</h4>
                            <ol class="list-decimal list-inside space-y-1 text-sm text-green-800">
                                <li>Look for the camera icon in your browser</li>
                                <li>Tap "Allow" when prompted for camera access</li>
                                <li>If blocked, tap the lock/info icon next to the URL</li>
                                <li>Select "Permissions" and enable "Camera"</li>
                                <li>Refresh this page</li>
                            </ol>
                        </div>
                    </div>
                `;
                troubleshooting = `
                    <div class="mt-4 p-3 bg-yellow-50 rounded-lg">
                        <h5 class="font-medium text-yellow-800 mb-2">Still having trouble?</h5>
                        <ul class="text-sm text-yellow-700 space-y-1">
                            <li>• Check app permissions in Android Settings</li>
                            <li>• Clear browser cache and cookies</li>
                            <li>• Try using Chrome browser</li>
                        </ul>
                    </div>
                `;
            }
        } else {
            instructions = `
                <div class="space-y-3">
                    <div class="bg-blue-50 p-3 rounded-lg">
                        <h4 class="font-semibold text-blue-900 mb-2">🖥️ Enable Camera in ${browserName}:</h4>
                        <ol class="list-decimal list-inside space-y-1 text-sm text-blue-800">
                            <li>Click the camera icon in your browser's address bar</li>
                            <li>Select "Allow" for camera access</li>
                            <li>If you don't see the icon, click the lock icon next to the URL</li>
                            <li>Set camera permission to "Allow"</li>
                            <li>Refresh this page and try again</li>
                        </ol>
                    </div>
                </div>
            `;
            troubleshooting = `
                <div class="mt-4 p-3 bg-yellow-50 rounded-lg">
                    <h5 class="font-medium text-yellow-800 mb-2">Alternative solutions:</h5>
                    <ul class="text-sm text-yellow-700 space-y-1">
                        <li>• Check if another application is using your camera</li>
                        <li>• Try restarting your browser</li>
                        <li>• Clear browser cache and cookies</li>
                        <li>• Check system privacy settings</li>
                    </ul>
                </div>
            `;
        }
        
        const contextMessage = context === 'photo' ? 'photo capture' : 
                              context === 'video' ? 'video recording' : 'camera access';
        
        const message = `
            <div class="text-left">
                <div class="mb-4">
                    <h3 class="text-lg font-semibold text-red-600 mb-2">🚫 Camera Access Denied</h3>
                    <p class="text-gray-700 mb-4">
                        We need camera permission for ${contextMessage}. Don't worry - we'll help you fix this!
                    </p>
                </div>
                ${instructions}
                ${troubleshooting}
                <div class="mt-6 p-4 bg-gray-50 rounded-lg border-l-4 border-blue-500">
                    <h5 class="font-medium text-gray-900 mb-2">📁 Alternative Option</h5>
                    <p class="text-sm text-gray-600">
                        You can still upload photos and videos from your device using the file upload button below.
                    </p>
                </div>
            </div>
        `;
        
        this.showFallbackInterface(container, message);
        this.showRetryOption(container, this._createPermissionRetryCallback());
        
        // Dispatch event to show file upload
        const fallbackEvent = new CustomEvent('camera:fallback-to-upload', {
            detail: { 
                reason: 'permission-denied',
                context: context,
                canRetry: true,
                instructions: instructions,
                browserName: browserName,
                isMobile: isMobile,
                isIOS: isIOS
            }
        });
        document.dispatchEvent(fallbackEvent);
    }

    handleCameraNotFound(container = null) {
        const message = `
            No camera was detected on this device. 
            <br><br>
            This could be because:
            <br>
            • Your device doesn't have a camera
            <br>
            • The camera is disabled in system settings
            <br>
            • Another application is using the camera
            <br><br>
            Please use the file upload option below to select photos/videos from your device.
        `;
        
        this.showFallbackInterface(container, message);
        
        // Dispatch event to show file upload
        const fallbackEvent = new CustomEvent('camera:fallback-to-upload', {
            detail: { 
                reason: 'camera-not-found',
                canRetry: false
            }
        });
        document.dispatchEvent(fallbackEvent);
    }

    handleUnsupportedBrowser(container = null) {
        const browserName = FallbackHandler.getBrowserName();
        const isSecure = this.supportStatus.isSecureContext;
        
        let message = '';
        if (!isSecure) {
            message = `
                Camera access requires a secure connection (HTTPS).
                <br><br>
                Please access this site using HTTPS or use the file upload option below.
            `;
        } else {
            message = `
                Your browser (${browserName}) doesn't fully support camera capture.
                <br><br>
                For the best experience, please try using:
                <br>
                • Chrome (recommended)
                <br>
                • Firefox
                <br>
                • Safari
                <br>
                • Edge
                <br><br>
                Or use the file upload option below to select photos/videos from your device.
            `;
        }
        
        this.showFallbackInterface(container, message);
        
        // Dispatch event to show file upload
        const fallbackEvent = new CustomEvent('camera:fallback-to-upload', {
            detail: { 
                reason: 'unsupported-browser',
                browserName: browserName,
                isSecure: isSecure,
                canRetry: false
            }
        });
        document.dispatchEvent(fallbackEvent);
    }

    handleCameraInUse(container = null, context = 'general') {
        const contextMessage = context === 'photo' ? 'photo capture' : 
                              context === 'video' ? 'video recording' : 'camera access';
        
        const message = `
            <div class="text-left">
                <div class="mb-4">
                    <h3 class="text-lg font-semibold text-orange-600 mb-2">📹 Camera Currently in Use</h3>
                    <p class="text-gray-700 mb-4">
                        Another application is currently using your camera, preventing ${contextMessage}.
                    </p>
                </div>
                <div class="bg-orange-50 p-3 rounded-lg mb-4">
                    <h4 class="font-semibold text-orange-900 mb-2">🔧 Quick Fixes:</h4>
                    <ol class="list-decimal list-inside space-y-1 text-sm text-orange-800">
                        <li>Close other apps that might be using the camera (video calls, camera apps, etc.)</li>
                        <li>Close other browser tabs that might have camera access</li>
                        <li>Restart your browser completely</li>
                        <li>If on mobile, check if the camera app is running in the background</li>
                    </ol>
                </div>
                <div class="mt-4 p-4 bg-gray-50 rounded-lg border-l-4 border-blue-500">
                    <h5 class="font-medium text-gray-900 mb-2">📁 Alternative Option</h5>
                    <p class="text-sm text-gray-600">
                        You can upload photos and videos from your device using the file upload button below.
                    </p>
                </div>
            </div>
        `;
        
        this.showFallbackInterface(container, message);
        this.showRetryOption(container, this._createGenericRetryCallback());
        
        const fallbackEvent = new CustomEvent('camera:fallback-to-upload', {
            detail: { 
                reason: 'camera-in-use',
                context: context,
                canRetry: true,
                errorType: 'camera-in-use'
            }
        });
        document.dispatchEvent(fallbackEvent);
    }

    handleConstraintError(error, container = null, context = 'general') {
        const contextMessage = context === 'photo' ? 'photo capture' : 
                              context === 'video' ? 'video recording' : 'camera access';
        
        const message = `
            <div class="text-left">
                <div class="mb-4">
                    <h3 class="text-lg font-semibold text-red-600 mb-2">⚙️ Camera Settings Not Supported</h3>
                    <p class="text-gray-700 mb-4">
                        Your camera doesn't support the required settings for ${contextMessage}.
                    </p>
                </div>
                <div class="bg-red-50 p-3 rounded-lg mb-4">
                    <h4 class="font-semibold text-red-900 mb-2">🔍 What this means:</h4>
                    <ul class="list-disc list-inside space-y-1 text-sm text-red-800">
                        <li>Your camera may not support the requested resolution or frame rate</li>
                        <li>The camera might be an older model with limited capabilities</li>
                        <li>Some camera features may not be available on your device</li>
                    </ul>
                </div>
                <div class="bg-blue-50 p-3 rounded-lg mb-4">
                    <h4 class="font-semibold text-blue-900 mb-2">💡 Try these solutions:</h4>
                    <ol class="list-decimal list-inside space-y-1 text-sm text-blue-800">
                        <li>Try using a different camera if your device has multiple cameras</li>
                        <li>Update your browser to the latest version</li>
                        <li>Check if your device drivers are up to date</li>
                    </ol>
                </div>
                <div class="mt-4 p-4 bg-gray-50 rounded-lg border-l-4 border-blue-500">
                    <h5 class="font-medium text-gray-900 mb-2">📁 Alternative Option</h5>
                    <p class="text-sm text-gray-600">
                        You can upload photos and videos from your device using the file upload button below.
                    </p>
                </div>
            </div>
        `;
        
        this.showFallbackInterface(container, message);
        
        const fallbackEvent = new CustomEvent('camera:fallback-to-upload', {
            detail: { 
                reason: 'constraints-error',
                context: context,
                canRetry: false,
                errorType: 'constraints-error',
                constraintError: error.constraint
            }
        });
        document.dispatchEvent(fallbackEvent);
    }

    handleSecurityError(container = null, context = 'general') {
        const contextMessage = context === 'photo' ? 'photo capture' : 
                              context === 'video' ? 'video recording' : 'camera access';
        
        const message = `
            <div class="text-left">
                <div class="mb-4">
                    <h3 class="text-lg font-semibold text-red-600 mb-2">🔒 Security Settings Blocking Camera</h3>
                    <p class="text-gray-700 mb-4">
                        Your browser's security settings are preventing ${contextMessage}.
                    </p>
                </div>
                <div class="bg-red-50 p-3 rounded-lg mb-4">
                    <h4 class="font-semibold text-red-900 mb-2">🛡️ Security Check:</h4>
                    <ul class="list-disc list-inside space-y-1 text-sm text-red-800">
                        <li>Make sure you're accessing this site via HTTPS (secure connection)</li>
                        <li>Check if your browser has strict privacy settings enabled</li>
                        <li>Some browser extensions might be blocking camera access</li>
                    </ul>
                </div>
                <div class="bg-blue-50 p-3 rounded-lg mb-4">
                    <h4 class="font-semibold text-blue-900 mb-2">🔧 Solutions to try:</h4>
                    <ol class="list-decimal list-inside space-y-1 text-sm text-blue-800">
                        <li>Temporarily disable browser extensions</li>
                        <li>Check browser privacy/security settings</li>
                        <li>Try using an incognito/private browsing window</li>
                        <li>Clear browser cache and cookies</li>
                    </ol>
                </div>
                <div class="mt-4 p-4 bg-gray-50 rounded-lg border-l-4 border-blue-500">
                    <h5 class="font-medium text-gray-900 mb-2">📁 Alternative Option</h5>
                    <p class="text-sm text-gray-600">
                        You can upload photos and videos from your device using the file upload button below.
                    </p>
                </div>
            </div>
        `;
        
        this.showFallbackInterface(container, message);
        this.showRetryOption(container, this._createGenericRetryCallback());
        
        const fallbackEvent = new CustomEvent('camera:fallback-to-upload', {
            detail: { 
                reason: 'security-error',
                context: context,
                canRetry: true,
                errorType: 'security-error'
            }
        });
        document.dispatchEvent(fallbackEvent);
    }

    handleInterruptedError(container = null, context = 'general') {
        const contextMessage = context === 'photo' ? 'photo capture' : 
                              context === 'video' ? 'video recording' : 'camera access';
        
        const message = `
            <div class="text-left">
                <div class="mb-4">
                    <h3 class="text-lg font-semibold text-yellow-600 mb-2">⚠️ Camera Access Interrupted</h3>
                    <p class="text-gray-700 mb-4">
                        The ${contextMessage} was interrupted unexpectedly.
                    </p>
                </div>
                <div class="bg-yellow-50 p-3 rounded-lg mb-4">
                    <h4 class="font-semibold text-yellow-900 mb-2">🔄 This usually happens when:</h4>
                    <ul class="list-disc list-inside space-y-1 text-sm text-yellow-800">
                        <li>The page was refreshed during camera access</li>
                        <li>Another app requested camera access</li>
                        <li>The device went to sleep or was locked</li>
                        <li>Network connectivity was lost temporarily</li>
                    </ul>
                </div>
                <div class="bg-green-50 p-3 rounded-lg mb-4">
                    <h4 class="font-semibold text-green-900 mb-2">✅ Easy fix:</h4>
                    <p class="text-sm text-green-800">
                        Simply click "Try Again" below to restart camera access.
                    </p>
                </div>
                <div class="mt-4 p-4 bg-gray-50 rounded-lg border-l-4 border-blue-500">
                    <h5 class="font-medium text-gray-900 mb-2">📁 Alternative Option</h5>
                    <p class="text-sm text-gray-600">
                        You can upload photos and videos from your device using the file upload button below.
                    </p>
                </div>
            </div>
        `;
        
        this.showFallbackInterface(container, message);
        this.showRetryOption(container, this._createGenericRetryCallback());
        
        const fallbackEvent = new CustomEvent('camera:fallback-to-upload', {
            detail: { 
                reason: 'interrupted',
                context: context,
                canRetry: true,
                errorType: 'interrupted'
            }
        });
        document.dispatchEvent(fallbackEvent);
    }

    handleGenericError(error, container = null, context = 'general') {
        console.error('Camera error:', error);
        
        const contextMessage = context === 'photo' ? 'photo capture' : 
                              context === 'video' ? 'video recording' : 'camera access';
        
        let message = '';
        let canRetry = false;
        let errorType = 'unknown';
        
        // Provide more specific messages for known errors
        if (error.name === 'TypeError') {
            message = `
                <div class="text-left">
                    <div class="mb-4">
                        <h3 class="text-lg font-semibold text-red-600 mb-2">⚙️ Camera Configuration Error</h3>
                        <p class="text-gray-700 mb-4">
                            There was a problem configuring the camera for ${contextMessage}.
                        </p>
                    </div>
                    <div class="bg-blue-50 p-3 rounded-lg mb-4">
                        <h4 class="font-semibold text-blue-900 mb-2">🔧 Quick fixes:</h4>
                        <ol class="list-decimal list-inside space-y-1 text-sm text-blue-800">
                            <li>Refresh the page and try again</li>
                            <li>Clear your browser cache and cookies</li>
                            <li>Try using a different browser</li>
                            <li>Restart your device if the problem persists</li>
                        </ol>
                    </div>
                    <div class="mt-4 p-4 bg-gray-50 rounded-lg border-l-4 border-blue-500">
                        <h5 class="font-medium text-gray-900 mb-2">📁 Alternative Option</h5>
                        <p class="text-sm text-gray-600">
                            You can upload photos and videos from your device using the file upload button below.
                        </p>
                    </div>
                </div>
            `;
            canRetry = true;
            errorType = 'configuration-error';
        } else {
            // Generic error message for unknown errors
            message = `
                <div class="text-left">
                    <div class="mb-4">
                        <h3 class="text-lg font-semibold text-gray-600 mb-2">📷 Camera Unavailable</h3>
                        <p class="text-gray-700 mb-4">
                            We're having trouble accessing your camera for ${contextMessage}.
                        </p>
                    </div>
                    <div class="bg-gray-50 p-3 rounded-lg mb-4">
                        <h4 class="font-semibold text-gray-900 mb-2">🔍 This could be due to:</h4>
                        <ul class="list-disc list-inside space-y-1 text-sm text-gray-700">
                            <li>Temporary technical issues</li>
                            <li>Browser compatibility problems</li>
                            <li>Device hardware limitations</li>
                            <li>System-level restrictions</li>
                        </ul>
                    </div>
                    <div class="bg-blue-50 p-3 rounded-lg mb-4">
                        <h4 class="font-semibold text-blue-900 mb-2">💡 Try these steps:</h4>
                        <ol class="list-decimal list-inside space-y-1 text-sm text-blue-800">
                            <li>Refresh the page and try again</li>
                            <li>Check if other apps are using the camera</li>
                            <li>Try using a different browser</li>
                            <li>Restart your device</li>
                        </ol>
                    </div>
                    <div class="mt-4 p-4 bg-gray-50 rounded-lg border-l-4 border-blue-500">
                        <h5 class="font-medium text-gray-900 mb-2">📁 Alternative Option</h5>
                        <p class="text-sm text-gray-600">
                            You can upload photos and videos from your device using the file upload button below.
                        </p>
                    </div>
                </div>
            `;
            canRetry = true;
            errorType = 'unknown';
        }
        
        this.showFallbackInterface(container, message);
        
        if (canRetry) {
            this.showRetryOption(container, this._createGenericRetryCallback());
        }
        
        // Dispatch event to show file upload
        const fallbackEvent = new CustomEvent('camera:fallback-to-upload', {
            detail: { 
                reason: 'generic-error', 
                error: error,
                errorType: errorType,
                context: context,
                canRetry: canRetry
            }
        });
        document.dispatchEvent(fallbackEvent);
    }

    _createPermissionRetryCallback() {
        return async () => {
            // Show permission request flow
            this._showPermissionRequestFlow();
            
            try {
                // Request permissions again
                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                stream.getTracks().forEach(track => track.stop());
                
                // Dispatch success event
                const successEvent = new CustomEvent('camera:permission-granted', {
                    detail: { timestamp: Date.now() }
                });
                document.dispatchEvent(successEvent);
                
                // Hide fallback interface
                this.hideFallbackInterface();
                
                return true;
            } catch (error) {
                console.error('Permission retry failed:', error);
                throw error;
            }
        };
    }

    _createGenericRetryCallback() {
        return async () => {
            // Show retry progress
            this._showRetryProgress();
            
            try {
                // Test camera access
                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                stream.getTracks().forEach(track => track.stop());
                
                // Dispatch success event
                const successEvent = new CustomEvent('camera:retry-success', {
                    detail: { timestamp: Date.now() }
                });
                document.dispatchEvent(successEvent);
                
                // Hide fallback interface
                this.hideFallbackInterface();
                
                return true;
            } catch (error) {
                console.error('Camera retry failed:', error);
                throw error;
            }
        };
    }

    _showPermissionRequestFlow() {
        // Show a modal explaining the permission request
        const modal = document.createElement('div');
        modal.className = 'permission-request-modal fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-md mx-4 text-center">
                <div class="mb-4">
                    <div class="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                        <svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"></path>
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"></path>
                        </svg>
                    </div>
                    <h3 class="text-lg font-semibold text-gray-900 mb-2">Camera Permission Required</h3>
                    <p class="text-gray-600 mb-4">
                        We need access to your camera to take photos and record videos. 
                        Your privacy is important - we only access the camera when you're actively using this feature.
                    </p>
                </div>
                <div class="bg-blue-50 p-3 rounded-lg mb-4 text-left">
                    <h4 class="font-medium text-blue-900 mb-2">🔒 Privacy Promise:</h4>
                    <ul class="text-sm text-blue-800 space-y-1">
                        <li>• Camera is only active when you're taking photos/videos</li>
                        <li>• No data is transmitted during preview</li>
                        <li>• You can revoke permission at any time</li>
                        <li>• All processing happens on your device</li>
                    </ul>
                </div>
                <p class="text-sm text-gray-500 mb-4">
                    Click "Allow" when your browser asks for camera permission.
                </p>
                <div class="animate-pulse flex items-center justify-center">
                    <div class="w-4 h-4 bg-blue-500 rounded-full mr-2"></div>
                    <span class="text-blue-600">Requesting permission...</span>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Remove modal after 10 seconds
        setTimeout(() => {
            if (modal.parentNode) {
                modal.remove();
            }
        }, 10000);
        
        this.permissionModal = modal;
    }

    _showRetryProgress() {
        // Show retry progress indicator
        const progress = document.createElement('div');
        progress.className = 'retry-progress-modal fixed inset-0 flex items-center justify-center bg-black bg-opacity-50 z-50';
        progress.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-sm mx-4 text-center">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <h3 class="text-lg font-semibold text-gray-900 mb-2">Retrying Camera Access</h3>
                <p class="text-gray-600">Please wait while we attempt to reconnect to your camera...</p>
            </div>
        `;
        
        document.body.appendChild(progress);
        
        // Remove progress after 10 seconds
        setTimeout(() => {
            if (progress.parentNode) {
                progress.remove();
            }
        }, 10000);
        
        this.retryModal = progress;
    }

    showRetryOption(container = null, retryCallback = null) {
        if (!this.fallbackContainer) {
            console.warn('No fallback container available for retry option');
            return;
        }

        // Check if retry button already exists
        const existingRetryButton = this.fallbackContainer.querySelector('.retry-button');
        if (existingRetryButton) {
            return; // Don't add duplicate retry buttons
        }

        // Add retry button
        const retryButton = document.createElement('button');
        retryButton.className = 'retry-button mt-4 bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2';
        retryButton.textContent = 'Try Camera Again';
        retryButton.setAttribute('aria-label', 'Retry camera access');
        
        retryButton.onclick = async () => {
            // Disable button during retry
            retryButton.disabled = true;
            retryButton.textContent = 'Retrying...';
            retryButton.className = retryButton.className.replace('bg-blue-500 hover:bg-blue-600', 'bg-gray-400 cursor-not-allowed');
            
            try {
                this.hideFallbackInterface();
                
                if (retryCallback) {
                    await retryCallback();
                } else {
                    // Default retry behavior - dispatch retry event
                    const retryEvent = new CustomEvent('camera:retry-requested', {
                        detail: { timestamp: Date.now() }
                    });
                    document.dispatchEvent(retryEvent);
                }
            } catch (error) {
                console.error('Retry failed:', error);
                // Re-enable button if retry fails
                retryButton.disabled = false;
                retryButton.textContent = 'Try Camera Again';
                retryButton.className = 'retry-button mt-4 bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2';
            }
        };

        this.fallbackContainer.appendChild(retryButton);
    }

    hideFallbackInterface() {
        if (this.fallbackContainer) {
            this.fallbackContainer.remove();
            this.fallbackContainer = null;
            
            // Dispatch event to notify that fallback interface is hidden
            const hideEvent = new CustomEvent('camera:fallback-hidden', {
                detail: { timestamp: Date.now() }
            });
            document.dispatchEvent(hideEvent);
        }
    }

    // Get detailed support information for debugging
    getSupportStatus() {
        return {
            ...this.supportStatus,
            userAgent: navigator.userAgent,
            isMobile: FallbackHandler.isMobileDevice(),
            isIOS: FallbackHandler.isIOSDevice(),
            browserName: FallbackHandler.getBrowserName(),
            timestamp: new Date().toISOString()
        };
    }

    // Display detailed error information for debugging (development mode only)
    showDetailedError(error, container = null) {
        if (process.env.NODE_ENV === 'production') {
            return this.handleGenericError(error, container);
        }

        const supportStatus = this.getSupportStatus();
        const message = `
            <div class="text-left">
                <strong>Debug Information:</strong>
                <br><br>
                <strong>Error:</strong> ${error.name} - ${error.message}
                <br>
                <strong>Browser:</strong> ${supportStatus.browserName}
                <br>
                <strong>Mobile:</strong> ${supportStatus.isMobile ? 'Yes' : 'No'}
                <br>
                <strong>Secure Context:</strong> ${supportStatus.isSecureContext ? 'Yes' : 'No'}
                <br>
                <strong>getUserMedia:</strong> ${supportStatus.getUserMedia ? 'Supported' : 'Not Supported'}
                <br>
                <strong>MediaRecorder:</strong> ${supportStatus.mediaRecorder ? 'Supported' : 'Not Supported'}
                <br><br>
                Please use the file upload option below.
            </div>
        `;
        
        this.showFallbackInterface(container, message);
        
        // Dispatch detailed error event
        const errorEvent = new CustomEvent('camera:detailed-error', {
            detail: { 
                error: error,
                supportStatus: supportStatus
            }
        });
        document.dispatchEvent(errorEvent);
    }

    // Utility method to detect mobile devices
    static isMobileDevice() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
               (navigator.maxTouchPoints && navigator.maxTouchPoints > 2);
    }

    // Utility method to detect iOS devices
    static isIOSDevice() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent) ||
               (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    }

    // Utility method to detect Android devices
    static isAndroidDevice() {
        return /Android/i.test(navigator.userAgent);
    }

    // Utility method to get user-friendly browser name
    static getBrowserName() {
        const userAgent = navigator.userAgent;
        
        if (userAgent.includes('Edg/')) return 'Edge';
        if (userAgent.includes('Chrome/') && !userAgent.includes('Edg/')) return 'Chrome';
        if (userAgent.includes('Firefox/')) return 'Firefox';
        if (userAgent.includes('Safari/') && !userAgent.includes('Chrome/')) return 'Safari';
        if (userAgent.includes('Opera/') || userAgent.includes('OPR/')) return 'Opera';
        
        return 'your browser';
    }

    // Utility method to check if browser supports specific media types
    static checkMediaTypeSupport() {
        const support = {
            photo: {
                jpeg: true, // Basic support assumed
                png: true,
                webp: false
            },
            video: {
                mp4: false,
                webm: false,
                mov: false
            }
        };

        // Check video format support
        if (window.MediaRecorder) {
            support.video.mp4 = MediaRecorder.isTypeSupported('video/mp4');
            support.video.webm = MediaRecorder.isTypeSupported('video/webm');
            support.video.mov = MediaRecorder.isTypeSupported('video/quicktime');
        }

        // Check WebP support for photos
        const canvas = document.createElement('canvas');
        canvas.width = 1;
        canvas.height = 1;
        support.photo.webp = canvas.toDataURL('image/webp').indexOf('data:image/webp') === 0;

        return support;
    }

    // Utility method to get recommended settings for current device
    static getRecommendedSettings() {
        const isMobile = FallbackHandler.isMobileDevice();
        const isIOS = FallbackHandler.isIOSDevice();
        const isAndroid = FallbackHandler.isAndroidDevice();

        return {
            photo: {
                width: isMobile ? 720 : 1280,
                height: isMobile ? 480 : 720,
                quality: isMobile ? 0.7 : 0.8,
                format: 'image/jpeg'
            },
            video: {
                width: isMobile ? 720 : 1280,
                height: isMobile ? 480 : 720,
                frameRate: isMobile ? 24 : 30,
                bitrate: isMobile ? 1000000 : 2000000, // 1Mbps mobile, 2Mbps desktop
                format: isIOS ? 'video/mp4' : 'video/webm'
            },
            constraints: {
                facingMode: isMobile ? 'environment' : 'user',
                audio: !isIOS // iOS has issues with audio in some contexts
            }
        };
    }

    // Create enhanced file input with camera attributes for mobile
    createEnhancedFileInput(type = 'photo', options = {}) {
        const input = document.createElement('input');
        input.type = 'file';
        input.className = options.className || 'hidden';
        
        // Set multiple attribute if specified
        if (options.multiple) {
            input.multiple = true;
        }

        if (type === 'photo') {
            input.accept = 'image/*';
            // Add capture attribute for mobile devices to prefer camera
            if (FallbackHandler.isMobileDevice()) {
                input.capture = 'environment'; // Use back camera by default
            }
        } else if (type === 'video') {
            input.accept = 'video/*';
            if (FallbackHandler.isMobileDevice()) {
                input.capture = 'environment';
            }
        } else if (type === 'both') {
            input.accept = 'image/*,video/*';
            if (FallbackHandler.isMobileDevice()) {
                input.capture = 'environment';
            }
        }

        // Add accessibility attributes
        input.setAttribute('aria-label', `Select ${type} file${options.multiple ? 's' : ''}`);
        
        // Add change event listener if callback provided
        if (options.onChange) {
            input.addEventListener('change', options.onChange);
        }
        
        return input;
    }

    // Create a user-friendly fallback button that triggers file input
    createFallbackButton(type = 'photo', options = {}) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = options.className || 'bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2';
        
        const icon = type === 'video' ? '🎥' : '📷';
        const text = options.text || `Select ${type === 'photo' ? 'Photo' : 'Video'}${options.multiple ? 's' : ''}`;
        
        button.innerHTML = `${icon} ${text}`;
        button.setAttribute('aria-label', text);

        // Create hidden file input
        const fileInput = this.createEnhancedFileInput(type, options);
        
        // Connect button to file input
        button.onclick = () => {
            fileInput.click();
        };

        return { button, fileInput };
    }

    cleanup() {
        this.hideFallbackInterface();
        
        // Clear support status
        this.supportStatus = {
            getUserMedia: false,
            mediaRecorder: false,
            enumerateDevices: false,
            isSecureContext: false
        };
    }
}

/**
 * TouchGestureHandler Class
 * Handles touch gestures for mobile camera interface
 */
class TouchGestureHandler {
    constructor(options = {}) {
        this.options = {
            tapThreshold: 10, // pixels
            doubleTapDelay: 300, // ms
            pinchThreshold: 0.1,
            swipeThreshold: 50, // pixels
            swipeVelocityThreshold: 0.3, // pixels/ms
            ...options
        };

        this.isActive = false;
        this.touches = new Map();
        this.lastTap = null;
        this.gestureStartDistance = 0;
        this.gestureStartTime = 0;

        this.callbacks = {
            onTap: options.onTap || (() => {}),
            onDoubleTap: options.onDoubleTap || (() => {}),
            onPinch: options.onPinch || (() => {}),
            onSwipe: options.onSwipe || (() => {})
        };

        this._bindEvents();
    }

    _bindEvents() {
        document.addEventListener('touchstart', this._handleTouchStart.bind(this), { passive: false });
        document.addEventListener('touchmove', this._handleTouchMove.bind(this), { passive: false });
        document.addEventListener('touchend', this._handleTouchEnd.bind(this), { passive: false });
        document.addEventListener('touchcancel', this._handleTouchCancel.bind(this), { passive: false });
    }

    _handleTouchStart(event) {
        const cameraContainer = event.target.closest('.camera-capture-container');
        if (!cameraContainer) return;

        this.isActive = true;
        this.gestureStartTime = Date.now();

        // Store touch information
        for (let i = 0; i < event.touches.length; i++) {
            const touch = event.touches[i];
            this.touches.set(touch.identifier, {
                startX: touch.clientX,
                startY: touch.clientY,
                currentX: touch.clientX,
                currentY: touch.clientY,
                startTime: Date.now()
            });
        }

        // Handle pinch gesture start
        if (event.touches.length === 2) {
            const touch1 = event.touches[0];
            const touch2 = event.touches[1];
            this.gestureStartDistance = this._getDistance(touch1, touch2);
        }
    }

    _handleTouchMove(event) {
        if (!this.isActive) return;

        // Update touch positions
        for (let i = 0; i < event.touches.length; i++) {
            const touch = event.touches[i];
            const touchData = this.touches.get(touch.identifier);
            if (touchData) {
                touchData.currentX = touch.clientX;
                touchData.currentY = touch.clientY;
            }
        }

        // Handle pinch gesture
        if (event.touches.length === 2 && this.gestureStartDistance > 0) {
            event.preventDefault();
            const touch1 = event.touches[0];
            const touch2 = event.touches[1];
            const currentDistance = this._getDistance(touch1, touch2);
            const scale = currentDistance / this.gestureStartDistance;

            if (Math.abs(scale - 1) > this.options.pinchThreshold) {
                this.callbacks.onPinch({
                    scale: scale,
                    center: {
                        x: (touch1.clientX + touch2.clientX) / 2,
                        y: (touch1.clientY + touch2.clientY) / 2
                    }
                });
            }
        }
    }

    _handleTouchEnd(event) {
        if (!this.isActive) return;

        const now = Date.now();
        const remainingTouches = event.touches.length;

        // Handle single touch end
        if (remainingTouches === 0) {
            const touchData = Array.from(this.touches.values())[0];
            if (touchData) {
                const deltaX = touchData.currentX - touchData.startX;
                const deltaY = touchData.currentY - touchData.startY;
                const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
                const duration = now - touchData.startTime;

                if (distance < this.options.tapThreshold) {
                    // Handle tap
                    this._handleTap(event, touchData);
                } else if (distance > this.options.swipeThreshold) {
                    // Handle swipe
                    const velocity = distance / duration;
                    if (velocity > this.options.swipeVelocityThreshold) {
                        this.callbacks.onSwipe({
                            deltaX: deltaX,
                            deltaY: deltaY,
                            distance: distance,
                            velocity: velocity,
                            direction: this._getSwipeDirection(deltaX, deltaY)
                        });
                    }
                }
            }

            this._reset();
        }

        // Remove ended touches
        for (let i = 0; i < event.changedTouches.length; i++) {
            const touch = event.changedTouches[i];
            this.touches.delete(touch.identifier);
        }
    }

    _handleTouchCancel(event) {
        this._reset();
    }

    _handleTap(event, touchData) {
        const now = Date.now();

        // Check for double tap
        if (this.lastTap && (now - this.lastTap.time) < this.options.doubleTapDelay) {
            const distance = Math.sqrt(
                Math.pow(touchData.startX - this.lastTap.x, 2) +
                Math.pow(touchData.startY - this.lastTap.y, 2)
            );

            if (distance < this.options.tapThreshold) {
                this.callbacks.onDoubleTap(event);
                this.lastTap = null;
                return;
            }
        }

        // Single tap
        this.callbacks.onTap(event);
        this.lastTap = {
            x: touchData.startX,
            y: touchData.startY,
            time: now
        };
    }

    _getDistance(touch1, touch2) {
        const dx = touch1.clientX - touch2.clientX;
        const dy = touch1.clientY - touch2.clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    _getSwipeDirection(deltaX, deltaY) {
        const absDeltaX = Math.abs(deltaX);
        const absDeltaY = Math.abs(deltaY);

        if (absDeltaX > absDeltaY) {
            return deltaX > 0 ? 'right' : 'left';
        } else {
            return deltaY > 0 ? 'down' : 'up';
        }
    }

    _reset() {
        this.isActive = false;
        this.touches.clear();
        this.gestureStartDistance = 0;
        this.gestureStartTime = 0;
    }

    cleanup() {
        document.removeEventListener('touchstart', this._handleTouchStart.bind(this));
        document.removeEventListener('touchmove', this._handleTouchMove.bind(this));
        document.removeEventListener('touchend', this._handleTouchEnd.bind(this));
        document.removeEventListener('touchcancel', this._handleTouchCancel.bind(this));
        this._reset();
    }
}

/**
 * OrientationHandler Class
 * Handles device orientation changes for mobile camera interface
 */
class OrientationHandler {
    constructor(options = {}) {
        this.options = {
            debounceMs: 250,
            ...options
        };

        this.currentOrientation = this._getCurrentOrientation();
        this.debounceTimer = null;
        this.callback = options.onOrientationChange || (() => {});

        this._bindEvents();
    }

    _bindEvents() {
        // Modern orientation API
        if (screen.orientation) {
            screen.orientation.addEventListener('change', this._handleOrientationChange.bind(this));
        }
        
        // Fallback for older browsers
        window.addEventListener('orientationchange', this._handleOrientationChange.bind(this));
        
        // Additional fallback using resize
        window.addEventListener('resize', this._handleResize.bind(this));
    }

    _handleOrientationChange() {
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        this.debounceTimer = setTimeout(() => {
            const newOrientation = this._getCurrentOrientation();
            if (newOrientation !== this.currentOrientation) {
                this.currentOrientation = newOrientation;
                this.callback(newOrientation);
            }
        }, this.options.debounceMs);
    }

    _handleResize() {
        // Use resize as a fallback for orientation detection
        this._handleOrientationChange();
    }

    _getCurrentOrientation() {
        // Try modern API first
        if (screen.orientation) {
            return screen.orientation.type;
        }
        
        // Fallback to window.orientation
        if (window.orientation !== undefined) {
            const angle = window.orientation;
            switch (angle) {
                case 0: return 'portrait-primary';
                case 90: return 'landscape-primary';
                case 180: return 'portrait-secondary';
                case -90: return 'landscape-secondary';
                default: return 'portrait-primary';
            }
        }
        
        // Final fallback using window dimensions
        const width = window.innerWidth;
        const height = window.innerHeight;
        return width > height ? 'landscape-primary' : 'portrait-primary';
    }

    getCurrentOrientation() {
        return this.currentOrientation;
    }

    isPortrait() {
        return this.currentOrientation.includes('portrait');
    }

    isLandscape() {
        return this.currentOrientation.includes('landscape');
    }

    cleanup() {
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        if (screen.orientation) {
            screen.orientation.removeEventListener('change', this._handleOrientationChange.bind(this));
        }
        
        window.removeEventListener('orientationchange', this._handleOrientationChange.bind(this));
        window.removeEventListener('resize', this._handleResize.bind(this));
    }
}

// Export classes for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        CameraCapture,
        CameraManager,
        MediaCapture,
        MediaPreview,
        CameraControls,
        FallbackHandler,
        TouchGestureHandler,
        OrientationHandler
    };
}