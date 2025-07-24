// static/controls.js
document.addEventListener('DOMContentLoaded', () => {
    // --- 元素获取 ---
    
    // 原有Qwen设置元素
    const qwenAnalysisToggleControls = document.getElementById('qwen-analysis-toggle-controls');
    const qwenStatusTextControls = document.getElementById('qwen-status-text-controls'); // 已恢复此元素
    const useEnhancedSearchToggleControls = document.getElementById('use-enhanced-search-toggle-controls');
    const qwenModelNameInput = document.getElementById('qwen-model-name-input');
    const qwenApiKeyInput = document.getElementById('qwen-api-key-input');
    const qwenBaseUrlInput = document.getElementById('qwen-base-url-input');

    // 新增人脸设置元素
    const faceRecognitionToggleControls = document.getElementById('face-recognition-toggle-controls');
    const faceApiUrlInput = document.getElementById('face-api-url-input');
    const faceClusterThresholdInput = document.getElementById('face-cluster-threshold-input');

    // 通用按钮和状态
    const saveAllSettingsButton = document.getElementById('save-all-settings-button');
    const saveSettingsStatus = document.getElementById('save-settings-status');
    const toggleApiKeyVisibilityButton = document.getElementById('toggle-api-key-visibility');

    // 上传元素
    const unifiedUploadInputControls = document.getElementById('unified-upload-input-controls');
    const unifiedUploadButtonControls = document.getElementById('unified-upload-button-controls');
    const cancelUploadButtonControls = document.getElementById('cancel-upload-button-controls');
    const uploadStatusControls = document.getElementById('upload-status-controls');
    
    // 批量增强分析元素
    const batchEnhanceButton = document.getElementById('batch-enhance-button');
    const batchEnhanceStatus = document.getElementById('batch-enhance-status');
    const batchEnhanceProgress = document.getElementById('batch-enhance-progress');
    const batchEnhanceProgressBar = document.getElementById('batch-enhance-progress-bar');
    const batchEnhanceProgressText = document.getElementById('batch-enhance-progress-text');
    
    let currentUploadAbortController = null; // 用于中止上传
    let batchEnhancePollingInterval = null; // 用于轮询批量增强状态

    // --- 功能函数 ---

    /**
     * 从后端加载并填充所有应用设置到UI
     */
    function loadAppSettings() {
        fetch('/config/settings')
            .then(response => response.json())
            .then(data => {
                // 填充原有Qwen设置
                if (qwenAnalysisToggleControls) {
                    qwenAnalysisToggleControls.checked = data.qwen_vl_analysis_enabled === true;
                    // 恢复对 qwenStatusTextControls 的更新
                    if (qwenStatusTextControls) {
                        qwenStatusTextControls.textContent = data.qwen_vl_analysis_enabled ? '已开启' : '已关闭';
                    }
                }
                if (useEnhancedSearchToggleControls) {
                    useEnhancedSearchToggleControls.checked = data.use_enhanced_search === true;
                }
                if (qwenModelNameInput) qwenModelNameInput.value = data.qwen_model_name || '';
                if (qwenApiKeyInput) qwenApiKeyInput.value = data.qwen_api_key || '';
                if (qwenBaseUrlInput) qwenBaseUrlInput.value = data.qwen_base_url || '';
                
                // 填充新增的人脸设置
                if (faceRecognitionToggleControls) faceRecognitionToggleControls.checked = data.face_recognition_enabled === true;
                if (faceApiUrlInput) faceApiUrlInput.value = data.face_api_url || '';
                if (faceClusterThresholdInput) faceClusterThresholdInput.value = data.face_cluster_threshold ?? 0.5;
            })
            .catch(error => {
                console.error('获取应用设置失败 (controls):', error);
                if(saveSettingsStatus) saveSettingsStatus.textContent = '获取设置失败';
            });
    }

    /**
     * 保存所有设置
     */
    function saveAllSettings() {
        // 从所有输入元素收集数据
        const settingsToSave = {
            // 原有Qwen设置
            qwen_vl_analysis_enabled: qwenAnalysisToggleControls?.checked,
            use_enhanced_search: useEnhancedSearchToggleControls?.checked,
            qwen_model_name: qwenModelNameInput?.value.trim(),
            qwen_api_key: qwenApiKeyInput?.value.trim(),
            qwen_base_url: qwenBaseUrlInput?.value.trim(),
            
            // 新增人脸设置
            face_recognition_enabled: faceRecognitionToggleControls?.checked,
            face_api_url: faceApiUrlInput?.value.trim(),
            face_cluster_threshold: faceClusterThresholdInput ? parseFloat(faceClusterThresholdInput.value) : undefined,
        };

        // 过滤掉未定义的条目
        const payload = Object.fromEntries(Object.entries(settingsToSave).filter(([_, v]) => v !== undefined));

        saveSettingsStatus.textContent = '正在保存...';
        saveAllSettingsButton.disabled = true;

        fetch('/config/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                saveSettingsStatus.textContent = data.message;
            }
            // 使用后端返回的已确认数据重新加载UI，确保同步
            if (data.settings) {
                loadAppSettings(); 
            }
            setTimeout(() => { saveSettingsStatus.textContent = ''; }, 4000);
        })
        .catch(error => {
            console.error('保存设置失败 (controls):', error);
            saveSettingsStatus.textContent = '保存设置失败!';
        })
        .finally(() => {
             saveAllSettingsButton.disabled = false;
        });
    }

    /**
     * 处理文件上传逻辑
     */
    function handleUnifiedUploadControls() {
        const files = unifiedUploadInputControls.files;
        if (!files || files.length === 0) {
            uploadStatusControls.textContent = '请先选择文件。';
            return;
        }

        currentUploadAbortController = new AbortController();
        const formData = new FormData();
        let fileCount = 0;
        for (const file of files) {
            if (file.type && file.type.startsWith('image/')) {
                formData.append('files', file);
                fileCount++;
            }
        }

        if (fileCount === 0) {
            uploadStatusControls.textContent = '选择的文件中没有有效的图片。';
            return;
        }

        uploadStatusControls.textContent = `正在上传 ${fileCount} 张图片...`;
        unifiedUploadButtonControls.disabled = true;
        cancelUploadButtonControls.style.display = 'inline-block';

        fetch('/upload_images', {
            method: 'POST',
            body: formData,
            signal: currentUploadAbortController.signal
        })
        .then(response => response.json().then(data => ({ ok: response.ok, data })))
        .then(({ ok, data }) => {
            if (!ok) throw new Error(data.error || '服务器响应错误');
            uploadStatusControls.textContent = (data.message || `成功处理 ${data.processed_files?.length || 0} 张图片。`) + " 返回主页可查看。";
        })
        .catch(error => {
            if (error.name === 'AbortError') {
                uploadStatusControls.textContent = '上传已由用户取消。';
            } else {
                console.error('上传错误 (controls):', error);
                uploadStatusControls.textContent = `上传过程中发生错误: ${error.message}`;
            }
        })
        .finally(() => {
            unifiedUploadButtonControls.disabled = false;
            cancelUploadButtonControls.style.display = 'none';
            if (unifiedUploadInputControls) unifiedUploadInputControls.value = null;
            currentUploadAbortController = null;
        });
    }

    /**
     * 获取批量增强分析状态
     */
    function getBatchEnhanceStatus() {
        return fetch('/batch_enhance/status')
            .then(response => response.json())
            .catch(error => {
                console.error('获取批量增强状态失败:', error);
                return { is_running: false, error: error.message };
            });
    }

    /**
     * 更新批量增强分析UI状态
     */
    function updateBatchEnhanceUI(status) {
        if (!status) return;

        if (status.is_running) {
            // 分析中状态
            batchEnhanceButton.textContent = '终止分析';
            batchEnhanceButton.className = 'action-button batch-enhance-running';
            batchEnhanceButton.innerHTML = '<i class="fas fa-stop"></i> 终止分析';
            
            // 显示进度
            if (batchEnhanceProgress) {
                batchEnhanceProgress.style.display = 'block';
                const percentage = status.total_images > 0 ? 
                    (status.processed_count / status.total_images * 100) : 0;
                batchEnhanceProgressBar.style.width = `${percentage}%`;
                batchEnhanceProgressText.textContent = 
                    `${status.processed_count} / ${status.total_images}`;
            }
            
            // 显示状态信息
            let statusText = '正在分析中...';
            if (status.current_image_filename) {
                statusText += ` 当前: ${status.current_image_filename}`;
            }
            if (status.last_error) {
                statusText += ` (上次错误: ${status.last_error})`;
            }
            batchEnhanceStatus.textContent = statusText;
            
        } else {
            // 空闲状态
            batchEnhanceButton.textContent = '一键增强分析';
            batchEnhanceButton.className = 'action-button primary-action';
            batchEnhanceButton.innerHTML = '<i class="fas fa-magic"></i> 一键增强分析';
            
            // 隐藏进度条
            if (batchEnhanceProgress) {
                batchEnhanceProgress.style.display = 'none';
            }
            
            // 显示完成状态
            if (status.processed_count > 0) {
                let statusText = `已完成 ${status.processed_count} 张图片的增强分析`;
                if (status.errors && status.errors.length > 0) {
                    statusText += `, 失败 ${status.errors.length} 张`;
                }
                batchEnhanceStatus.textContent = statusText;
                setTimeout(() => { batchEnhanceStatus.textContent = ''; }, 5000);
            } else if (status.error) {
                batchEnhanceStatus.textContent = `错误: ${status.error}`;
                setTimeout(() => { batchEnhanceStatus.textContent = ''; }, 5000);
            }
        }
    }

    /**
     * 开始轮询批量增强分析状态
     */
    function startBatchEnhanceStatusPolling() {
        if (batchEnhancePollingInterval) return;
        
        batchEnhancePollingInterval = setInterval(() => {
            getBatchEnhanceStatus().then(status => {
                updateBatchEnhanceUI(status);
                
                // 如果不在运行中，停止轮询
                if (!status.is_running) {
                    stopBatchEnhanceStatusPolling();
                }
            });
        }, 2000); // 每2秒轮询一次
    }

    /**
     * 停止轮询批量增强分析状态
     */
    function stopBatchEnhanceStatusPolling() {
        if (batchEnhancePollingInterval) {
            clearInterval(batchEnhancePollingInterval);
            batchEnhancePollingInterval = null;
        }
    }

    /**
     * 处理批量增强分析按钮点击
     */
    function handleBatchEnhanceClick() {
        getBatchEnhanceStatus().then(status => {
            if (status.is_running) {
                // 当前在运行中，询问是否终止
                if (confirm('确定要终止当前的批量增强分析吗？')) {
                    fetch('/batch_enhance/stop', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            batchEnhanceStatus.textContent = data.message || '分析已终止';
                            stopBatchEnhanceStatusPolling();
                            // 更新UI状态
                            setTimeout(() => {
                                getBatchEnhanceStatus().then(updateBatchEnhanceUI);
                            }, 1000);
                        })
                        .catch(error => {
                            console.error('终止批量增强分析失败:', error);
                            batchEnhanceStatus.textContent = '终止分析失败';
                        });
                }
            } else {
                // 当前空闲，询问是否开始
                if (confirm('将对图库中所有未增强分析的照片进行增强分析，耗费时间较长，是否继续？')) {
                    batchEnhanceStatus.textContent = '正在启动批量增强分析...';
                    
                    fetch('/batch_enhance/start', { method: 'POST' })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                batchEnhanceStatus.textContent = data.message || '批量增强分析已启动';
                                startBatchEnhanceStatusPolling();
                                // 立即更新一次状态
                                setTimeout(() => {
                                    getBatchEnhanceStatus().then(updateBatchEnhanceUI);
                                }, 500);
                            } else {
                                batchEnhanceStatus.textContent = data.error || '启动失败';
                            }
                        })
                        .catch(error => {
                            console.error('启动批量增强分析失败:', error);
                            batchEnhanceStatus.textContent = '启动分析失败';
                        });
                }
            }
        });
    }

    /**
     * 初始化所有事件监听器
     */
    function initializeEventListeners() {
        // API Key 可见性切换
        if (toggleApiKeyVisibilityButton && qwenApiKeyInput) {
            // 使用 mousedown 防止按钮抢占输入框的焦点
            toggleApiKeyVisibilityButton.addEventListener('mousedown', (e) => e.preventDefault());
            toggleApiKeyVisibilityButton.addEventListener('click', () => {
                const icon = toggleApiKeyVisibilityButton.querySelector('i');
                if (qwenApiKeyInput.type === 'password') {
                    qwenApiKeyInput.type = 'text';
                    icon.classList.remove('fa-eye');
                    icon.classList.add('fa-eye-slash');
                } else {
                    qwenApiKeyInput.type = 'password';
                    icon.classList.remove('fa-eye-slash');
                    icon.classList.add('fa-eye');
                }
            });
        }
        
        // 保存按钮
        if (saveAllSettingsButton) {
            saveAllSettingsButton.addEventListener('click', saveAllSettings);
        }

        // 上传按钮
        if (unifiedUploadButtonControls) {
            unifiedUploadButtonControls.addEventListener('click', handleUnifiedUploadControls);
        }

        // 取消上传按钮
        if (cancelUploadButtonControls) {
            cancelUploadButtonControls.addEventListener('click', () => currentUploadAbortController?.abort());
        }

        // 批量增强分析按钮
        if (batchEnhanceButton) {
            batchEnhanceButton.addEventListener('click', handleBatchEnhanceClick);
        }
    }

    // --- 页面启动时执行 ---
    loadAppSettings();
    initializeEventListeners();
    
    // 检查批量增强分析状态
    getBatchEnhanceStatus().then(status => {
        updateBatchEnhanceUI(status);
        // 如果正在运行，开始轮询
        if (status.is_running) {
            startBatchEnhanceStatusPolling();
        }
    });
});