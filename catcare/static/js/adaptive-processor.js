/**
 * Adaptive Processor
 * Provides intelligent processing optimization based on device and network capabilities
 * Implements adaptive compression, mobile optimization, and performance monitoring
 */

class AdaptiveProcessor {
    constructor(options = {}) {
        this.options = {
            // Performance monitoring
            performanceMonitoringEnabled: true,
            performanceHistorySize: 100,
            adaptationThreshold: 0.1, // 10% performance change threshold
            
            // Storage monitoring
            storageMonitoringEnabled: true,
            lowStorageThreshold: 100 * 1024 * 1024, // 100MB
            criticalStorageThreshold: 50 * 1024 * 1024, // 50MB
            
            // Network adaptation
            networkAdaptationEnabled: true,
            slowNetworkThreshold: 1, // Mbps
            fastNetworkThreshold: 10, // Mbps
            
            // Device adaptation
            deviceAdaptationEnabled: true,
            lowMemoryThreshold: 2, // GB
            lowCoreThreshold: 2,
            
            // Processing profiles
            profiles: {
                'high-performance': {
                    quality: 0.9,
                    maxWidth: 2560,
                    maxHeight: 1440,
                    compressionThreshold: 5 * 1024 * 1024,
                    useWebWorkers: true,
                    maxConcurrent: 4
                },
                'balanced': {
                    quality: 0.8,
                    maxWidth: 1920,
                    maxHeight: 1080,
                    compressionThreshold: 2 * 1024 * 1024,
                    useWebWorkers: true,
                    maxConcurrent: 3
                },
                'mobile-optimized': {
                    quality: 0.75,
                    maxWidth: 1280,
                    maxHeight: 720,
                    compressionThreshold: 1 * 1024 * 1024,
                    useWebWorkers: false,
                    maxConcurrent: 1
                },
                'low-bandwidth': {
                    quality: 0.6,
                    maxWidth: 800,
                    maxHeight: 600,
                    compressionThreshold: 500 * 1024,
                    useWebWorkers: false,
                    maxConcurrent: 1
                },
                'storage-constrained': {
                    quality: 0.5,
                    maxWidth: 640,
                    maxHeight: 480,
                    compressionThreshold: 200 * 1024,
                    useWebWorkers: false,
                    maxConcurrent: 1
                }
            },
            
            ...options
        };

        // State management
        this.deviceCapabilities = null;
        this.networkInfo = null;
        this.storageInfo = null;
        this.currentProfile = 'balanced';
        this.performanceHistory = [];
        this.adaptationCallbacks = [];
        
        // Initialize capabilities detection
        this._initializeCapabilityDetection();
        
        // Start monitoring if enabled
        if (this.options.performanceMonitoringEnabled) {
            this._startPerformanceMonitoring();
        }
        
        if (this.options.storageMonitoringEnabled) {
            this._startStorageMonitoring();
        }
        
        if (this.options.networkAdaptationEnabled) {
            this._startNetworkMonitoring();
        }
    }

    /**
     * Get optimal processing settings based on current conditions
     * @param {Object} overrides - Optional setting overrides
     * @returns {Object} Optimized processing settings
     */
    getOptimalSettings(overrides = {}) {
        const profile = this._selectOptimalProfile();
        const settings = {
            ...this.options.profiles[profile],
            profile: profile,
            adaptationReason: this._getAdaptationReason(),
            timestamp: Date.now(),
            ...overrides
        };
        
        // Apply real-time adjustments
        this._applyRealTimeAdjustments(settings);
        
        return settings;
    }

    /**
     * Detect device capabilities
     * @returns {Object} Device capability information
     */
    detectDeviceCapabilities() {
        const userAgent = navigator.userAgent;
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(userAgent);
        const isTablet = /iPad|Android(?!.*Mobile)/i.test(userAgent);
        const isDesktop = !isMobile && !isTablet;
        
        // Hardware detection
        const memory = navigator.deviceMemory || this._estimateMemory();
        const cores = navigator.hardwareConcurrency || this._estimateCores();
        const pixelRatio = window.devicePixelRatio || 1;
        
        // Screen information
        const screen = {
            width: window.screen.width,
            height: window.screen.height,
            availWidth: window.screen.availWidth,
            availHeight: window.screen.availHeight,
            pixelRatio: pixelRatio
        };
        
        // Performance estimation
        const performanceScore = this._calculatePerformanceScore(memory, cores, isMobile);
        
        this.deviceCapabilities = {
            type: isMobile ? 'mobile' : (isTablet ? 'tablet' : 'desktop'),
            isMobile,
            isTablet,
            isDesktop,
            memory,
            cores,
            screen,
            performanceScore,
            supportedFeatures: this._detectSupportedFeatures(),
            batteryInfo: this._getBatteryInfo(),
            timestamp: Date.now()
        };
        
        return this.deviceCapabilities;
    }

    /**
     * Detect network capabilities
     * @returns {Object} Network capability information
     */
    detectNetworkCapabilities() {
        const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
        
        if (!connection) {
            // Fallback network estimation
            this.networkInfo = this._estimateNetworkCapabilities();
        } else {
            this.networkInfo = {
                effectiveType: connection.effectiveType || '4g',
                downlink: connection.downlink || 10,
                downlinkMax: connection.downlinkMax || 10,
                rtt: connection.rtt || 100,
                saveData: connection.saveData || false,
                type: connection.type || 'unknown',
                isSlowConnection: this._isSlowConnection(connection),
                isFastConnection: this._isFastConnection(connection),
                timestamp: Date.now()
            };
        }
        
        return this.networkInfo;
    }

    /**
     * Detect storage capabilities and usage
     * @returns {Promise<Object>} Storage information
     */
    async detectStorageCapabilities() {
        try {
            if ('storage' in navigator && 'estimate' in navigator.storage) {
                const estimate = await navigator.storage.estimate();
                const usage = estimate.usage || 0;
                const quota = estimate.quota || 0;
                const available = quota - usage;
                
                this.storageInfo = {
                    usage,
                    quota,
                    available,
                    usagePercentage: quota > 0 ? (usage / quota) * 100 : 0,
                    isLowStorage: available < this.options.lowStorageThreshold,
                    isCriticalStorage: available < this.options.criticalStorageThreshold,
                    timestamp: Date.now()
                };
            } else {
                // Fallback storage estimation
                this.storageInfo = this._estimateStorageCapabilities();
            }
        } catch (error) {
            console.warn('Storage detection failed:', error);
            this.storageInfo = this._estimateStorageCapabilities();
        }
        
        return this.storageInfo;
    }

    /**
     * Monitor processing performance and adapt settings
     * @param {Object} processingResult - Result from image processing
     */
    recordProcessingPerformance(processingResult) {
        if (!this.options.performanceMonitoringEnabled) return;
        
        const performanceData = {
            timestamp: Date.now(),
            processingTime: processingResult.processingTime || 0,
            fileSize: processingResult.originalSize || 0,
            compressionRatio: processingResult.compressionRatio || 1,
            profile: this.currentProfile,
            success: !processingResult.error,
            error: processingResult.error || null
        };
        
        // Add to history
        this.performanceHistory.push(performanceData);
        
        // Maintain history size limit
        if (this.performanceHistory.length > this.options.performanceHistorySize) {
            this.performanceHistory.shift();
        }
        
        // Check if adaptation is needed
        this._checkPerformanceAdaptation();
    }

    /**
     * Get current adaptation status and recommendations
     * @returns {Object} Adaptation status
     */
    getAdaptationStatus() {
        return {
            currentProfile: this.currentProfile,
            deviceCapabilities: this.deviceCapabilities,
            networkInfo: this.networkInfo,
            storageInfo: this.storageInfo,
            performanceMetrics: this._getPerformanceMetrics(),
            recommendations: this._getAdaptationRecommendations(),
            lastAdaptation: this._getLastAdaptation()
        };
    }

    /**
     * Force adaptation to specific profile
     * @param {string} profileName - Profile to switch to
     * @param {string} reason - Reason for manual adaptation
     */
    forceAdaptation(profileName, reason = 'manual') {
        if (!this.options.profiles[profileName]) {
            throw new Error(`Unknown profile: ${profileName}`);
        }
        
        const previousProfile = this.currentProfile;
        this.currentProfile = profileName;
        
        this._notifyAdaptationChange({
            previousProfile,
            newProfile: profileName,
            reason,
            timestamp: Date.now(),
            manual: true
        });
    }

    /**
     * Register callback for adaptation changes
     * @param {Function} callback - Callback function
     */
    onAdaptationChange(callback) {
        if (typeof callback === 'function') {
            this.adaptationCallbacks.push(callback);
        }
    }

    /**
     * Get user-friendly adaptation message
     * @returns {string} Human-readable adaptation status
     */
    getAdaptationMessage() {
        const profile = this.currentProfile;
        const reason = this._getAdaptationReason();
        
        const messages = {
            'high-performance': 'Using high-quality processing for optimal results',
            'balanced': 'Using balanced processing for good quality and performance',
            'mobile-optimized': 'Optimized for mobile device - reduced processing for better performance',
            'low-bandwidth': 'Optimized for slow connection - using aggressive compression',
            'storage-constrained': 'Optimized for limited storage - prioritizing smaller file sizes'
        };
        
        let message = messages[profile] || `Using ${profile} processing profile`;
        
        if (reason && reason !== 'balanced') {
            const reasonMessages = {
                'slow-network': ' due to slow network connection',
                'low-storage': ' due to limited device storage',
                'low-performance': ' due to device performance constraints',
                'battery-saving': ' to conserve battery life',
                'save-data': ' due to data saver mode'
            };
            
            message += reasonMessages[reason] || ` (${reason})`;
        }
        
        return message;
    }

    // Private methods

    _initializeCapabilityDetection() {
        // Initial detection
        this.detectDeviceCapabilities();
        this.detectNetworkCapabilities();
        this.detectStorageCapabilities();
        
        // Set initial profile
        this.currentProfile = this._selectOptimalProfile();
    }

    _selectOptimalProfile() {
        const device = this.deviceCapabilities;
        const network = this.networkInfo;
        const storage = this.storageInfo;
        
        // Priority order: storage > network > device performance
        
        // Critical storage constraint
        if (storage && storage.isCriticalStorage) {
            return 'storage-constrained';
        }
        
        // Network constraints
        if (network) {
            if (network.saveData || network.isSlowConnection) {
                return 'low-bandwidth';
            }
        }
        
        // Low storage constraint
        if (storage && storage.isLowStorage) {
            return 'storage-constrained';
        }
        
        // Device constraints
        if (device) {
            if (device.isMobile && device.performanceScore < 0.5) {
                return 'mobile-optimized';
            }
            
            if (device.memory < this.options.lowMemoryThreshold || 
                device.cores < this.options.lowCoreThreshold) {
                return 'mobile-optimized';
            }
            
            // High-performance devices with good network
            if (device.performanceScore > 0.8 && 
                network && network.isFastConnection) {
                return 'high-performance';
            }
        }
        
        return 'balanced';
    }

    _getAdaptationReason() {
        const device = this.deviceCapabilities;
        const network = this.networkInfo;
        const storage = this.storageInfo;
        
        if (storage && storage.isCriticalStorage) return 'critical-storage';
        if (storage && storage.isLowStorage) return 'low-storage';
        if (network && network.saveData) return 'save-data';
        if (network && network.isSlowConnection) return 'slow-network';
        if (device && device.isMobile && device.performanceScore < 0.5) return 'low-performance';
        if (device && device.batteryInfo && device.batteryInfo.level < 0.2) return 'battery-saving';
        
        return 'balanced';
    }

    _applyRealTimeAdjustments(settings) {
        // Adjust based on current performance
        const recentPerformance = this._getRecentPerformanceMetrics();
        
        if (recentPerformance.averageProcessingTime > 5000) { // 5 seconds
            // Processing is too slow, reduce quality
            settings.quality = Math.max(0.5, settings.quality - 0.1);
            settings.maxWidth = Math.min(settings.maxWidth, 1280);
            settings.maxHeight = Math.min(settings.maxHeight, 720);
        }
        
        // Adjust for battery level
        if (this.deviceCapabilities && this.deviceCapabilities.batteryInfo) {
            const battery = this.deviceCapabilities.batteryInfo;
            if (battery.level < 0.2 && !battery.charging) {
                settings.quality = Math.max(0.5, settings.quality - 0.2);
                settings.useWebWorkers = false;
                settings.maxConcurrent = 1;
            }
        }
        
        // Adjust for memory pressure
        if (this.deviceCapabilities && this.deviceCapabilities.memory < 2) {
            settings.maxConcurrent = 1;
            settings.useWebWorkers = false;
        }
    }

    _calculatePerformanceScore(memory, cores, isMobile) {
        let score = 0;
        
        // Memory contribution (40%)
        score += Math.min(memory / 8, 1) * 0.4;
        
        // CPU cores contribution (30%)
        score += Math.min(cores / 8, 1) * 0.3;
        
        // Device type contribution (30%)
        if (isMobile) {
            score += 0.15; // Mobile devices get lower base score
        } else {
            score += 0.3; // Desktop devices get higher base score
        }
        
        return Math.min(score, 1);
    }

    _detectSupportedFeatures() {
        return {
            webWorkers: typeof Worker !== 'undefined',
            canvas: this._supportsCanvas(),
            webGL: this._supportsWebGL(),
            offscreenCanvas: typeof OffscreenCanvas !== 'undefined',
            imageCapture: 'ImageCapture' in window,
            webAssembly: typeof WebAssembly !== 'undefined'
        };
    }

    _getBatteryInfo() {
        if ('getBattery' in navigator) {
            navigator.getBattery().then(battery => {
                this.deviceCapabilities.batteryInfo = {
                    level: battery.level,
                    charging: battery.charging,
                    chargingTime: battery.chargingTime,
                    dischargingTime: battery.dischargingTime
                };
            }).catch(() => {
                // Battery API not available
            });
        }
        
        return null;
    }

    _estimateMemory() {
        // Rough estimation based on user agent and screen resolution
        const screenPixels = window.screen.width * window.screen.height;
        
        if (screenPixels > 2073600) { // > 1920x1080
            return 8;
        } else if (screenPixels > 921600) { // > 1280x720
            return 4;
        } else {
            return 2;
        }
    }

    _estimateCores() {
        // Rough estimation
        return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent) ? 4 : 2;
    }

    _estimateNetworkCapabilities() {
        // Fallback network estimation using timing
        const startTime = performance.now();
        
        return {
            effectiveType: '4g',
            downlink: 10,
            rtt: 100,
            saveData: false,
            isSlowConnection: false,
            isFastConnection: true,
            estimated: true,
            timestamp: Date.now()
        };
    }

    _estimateStorageCapabilities() {
        return {
            usage: 0,
            quota: 1024 * 1024 * 1024, // 1GB estimate
            available: 1024 * 1024 * 1024,
            usagePercentage: 0,
            isLowStorage: false,
            isCriticalStorage: false,
            estimated: true,
            timestamp: Date.now()
        };
    }

    _isSlowConnection(connection) {
        return connection.effectiveType === 'slow-2g' || 
               connection.effectiveType === '2g' ||
               (connection.downlink && connection.downlink < this.options.slowNetworkThreshold);
    }

    _isFastConnection(connection) {
        return connection.effectiveType === '4g' &&
               connection.downlink && connection.downlink > this.options.fastNetworkThreshold;
    }

    _startPerformanceMonitoring() {
        // Monitor performance every 30 seconds
        setInterval(() => {
            this._checkPerformanceAdaptation();
        }, 30000);
    }

    _startStorageMonitoring() {
        // Check storage every 60 seconds
        setInterval(async () => {
            await this.detectStorageCapabilities();
            this._checkStorageAdaptation();
        }, 60000);
    }

    _startNetworkMonitoring() {
        // Listen for network changes
        if ('connection' in navigator && navigator.connection && navigator.connection.addEventListener) {
            const connection = navigator.connection;
            connection.addEventListener('change', () => {
                this.detectNetworkCapabilities();
                this._checkNetworkAdaptation();
            });
        }
    }

    _checkPerformanceAdaptation() {
        const metrics = this._getRecentPerformanceMetrics();
        
        if (metrics.averageProcessingTime > 10000 && this.currentProfile !== 'mobile-optimized') {
            // Performance is degrading, switch to mobile-optimized
            this._adaptToProfile('mobile-optimized', 'performance-degradation');
        } else if (metrics.averageProcessingTime < 2000 && this.currentProfile === 'mobile-optimized') {
            // Performance improved, can upgrade profile
            this._adaptToProfile('balanced', 'performance-improvement');
        }
    }

    _checkStorageAdaptation() {
        if (!this.storageInfo) return;
        
        if (this.storageInfo.isCriticalStorage && this.currentProfile !== 'storage-constrained') {
            this._adaptToProfile('storage-constrained', 'critical-storage');
        } else if (!this.storageInfo.isLowStorage && this.currentProfile === 'storage-constrained') {
            this._adaptToProfile('balanced', 'storage-recovered');
        }
    }

    _checkNetworkAdaptation() {
        if (!this.networkInfo) return;
        
        if (this.networkInfo.isSlowConnection && this.currentProfile !== 'low-bandwidth') {
            this._adaptToProfile('low-bandwidth', 'slow-network');
        } else if (this.networkInfo.isFastConnection && this.currentProfile === 'low-bandwidth') {
            this._adaptToProfile('balanced', 'network-improved');
        }
    }

    _adaptToProfile(profileName, reason) {
        const previousProfile = this.currentProfile;
        this.currentProfile = profileName;
        
        this._notifyAdaptationChange({
            previousProfile,
            newProfile: profileName,
            reason,
            timestamp: Date.now(),
            automatic: true
        });
    }

    _notifyAdaptationChange(changeInfo) {
        this.adaptationCallbacks.forEach(callback => {
            try {
                callback(changeInfo);
            } catch (error) {
                console.error('Adaptation callback error:', error);
            }
        });
    }

    _getRecentPerformanceMetrics() {
        const recentData = this.performanceHistory.slice(-10); // Last 10 operations
        
        if (recentData.length === 0) {
            return {
                averageProcessingTime: 0,
                successRate: 1,
                averageCompressionRatio: 1
            };
        }
        
        const totalTime = recentData.reduce((sum, data) => sum + data.processingTime, 0);
        const successCount = recentData.filter(data => data.success).length;
        const totalCompressionRatio = recentData.reduce((sum, data) => sum + data.compressionRatio, 0);
        
        return {
            averageProcessingTime: totalTime / recentData.length,
            successRate: successCount / recentData.length,
            averageCompressionRatio: totalCompressionRatio / recentData.length
        };
    }

    _getPerformanceMetrics() {
        if (this.performanceHistory.length === 0) {
            return null;
        }
        
        const totalTime = this.performanceHistory.reduce((sum, data) => sum + data.processingTime, 0);
        const successCount = this.performanceHistory.filter(data => data.success).length;
        const totalCompressionRatio = this.performanceHistory.reduce((sum, data) => sum + data.compressionRatio, 0);
        
        return {
            totalOperations: this.performanceHistory.length,
            averageProcessingTime: totalTime / this.performanceHistory.length,
            successRate: successCount / this.performanceHistory.length,
            averageCompressionRatio: totalCompressionRatio / this.performanceHistory.length,
            recentMetrics: this._getRecentPerformanceMetrics()
        };
    }

    _getAdaptationRecommendations() {
        const recommendations = [];
        
        if (this.storageInfo && this.storageInfo.isLowStorage) {
            recommendations.push({
                type: 'storage',
                message: 'Consider clearing device storage for better performance',
                priority: 'high'
            });
        }
        
        if (this.networkInfo && this.networkInfo.isSlowConnection) {
            recommendations.push({
                type: 'network',
                message: 'Slow network detected - using optimized compression',
                priority: 'medium'
            });
        }
        
        if (this.deviceCapabilities && this.deviceCapabilities.memory < 2) {
            recommendations.push({
                type: 'memory',
                message: 'Limited memory detected - reducing concurrent processing',
                priority: 'medium'
            });
        }
        
        return recommendations;
    }

    _getLastAdaptation() {
        // This would be stored in a more persistent way in a real implementation
        return {
            timestamp: Date.now(),
            profile: this.currentProfile,
            reason: this._getAdaptationReason()
        };
    }

    _supportsCanvas() {
        const canvas = document.createElement('canvas');
        return !!(canvas.getContext && canvas.getContext('2d'));
    }

    _supportsWebGL() {
        try {
            const canvas = document.createElement('canvas');
            return !!(canvas.getContext('webgl') || canvas.getContext('experimental-webgl'));
        } catch (e) {
            return false;
        }
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdaptiveProcessor;
}