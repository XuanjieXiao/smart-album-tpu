// static/controls.js
document.addEventListener('DOMContentLoaded', () => {
    // 设置元素
    const qwenAnalysisToggleControls = document.getElementById('qwen-analysis-toggle-controls');
    const qwenStatusTextControls = document.getElementById('qwen-status-text-controls');
    const useEnhancedSearchToggleControls = document.getElementById('use-enhanced-search-toggle-controls');
    
    // 新增的Qwen配置输入框
    const qwenModelNameInput = document.getElementById('qwen-model-name-input');
    const qwenApiKeyInput = document.getElementById('qwen-api-key-input');
    const qwenBaseUrlInput = document.getElementById('qwen-base-url-input');

    // 保存按钮和状态
    const saveAllSettingsButton = document.getElementById('save-all-settings-button');
    const saveSettingsStatus = document.getElementById('save-settings-status');

    // 上传元素
    const unifiedUploadInputControls = document.getElementById('unified-upload-input-controls');
    const unifiedUploadButtonControls = document.getElementById('unified-upload-button-controls');
    const cancelUploadButtonControls = document.getElementById('cancel-upload-button-controls');
    const uploadStatusControls = document.getElementById('upload-status-controls');
    
    let currentUploadAbortController = null; // 用于中止上传

    // 加载所有应用设置
    function loadAppSettings() {
        fetch('/config/settings')
            .then(response => response.json())
            .then(data => {
                // 填充开关状态
                if (qwenAnalysisToggleControls) {
                    qwenAnalysisToggleControls.checked = data.qwen_vl_analysis_enabled === true;
                    qwenStatusTextControls.textContent = data.qwen_vl_analysis_enabled ? '已开启' : '已关闭';
                }
                if (useEnhancedSearchToggleControls) {
                    useEnhancedSearchToggleControls.checked = data.use_enhanced_search === true;
                }
                
                // 填充Qwen服务配置
                if (qwenModelNameInput) {
                    qwenModelNameInput.value = data.qwen_model_name || '';
                }
                if (qwenApiKeyInput) {
                    qwenApiKeyInput.value = data.qwen_api_key || '';
                }
                if (qwenBaseUrlInput) {
                    qwenBaseUrlInput.value = data.qwen_base_url || '';
                }
            })
            .catch(error => {
                console.error('获取应用设置失败 (controls):', error);
                if(saveSettingsStatus) saveSettingsStatus.textContent = '获取设置失败';
            });
    }

    // 页面加载时执行
    loadAppSettings();
    
    const qwenApiKeyInputJs = document.getElementById('qwen-api-key-input');
    const toggleApiKeyVisibilityButton = document.getElementById('toggle-api-key-visibility');

    if (toggleApiKeyVisibilityButton && qwenApiKeyInputJs) {
        // 使用 mousedown 事件而不是 click，以防止在切换类型时输入框失去焦点
        toggleApiKeyVisibilityButton.addEventListener('mousedown', (e) => {
            e.preventDefault(); // 防止按钮抢占输入框的焦点
        });

        toggleApiKeyVisibilityButton.addEventListener('click', () => {
            const icon = toggleApiKeyVisibilityButton.querySelector('i');
            if (qwenApiKeyInputJs.type === 'password') {
                qwenApiKeyInputJs.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                qwenApiKeyInputJs.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    }
    // "保存所有设置" 按钮的事件监听
    if (saveAllSettingsButton) {
        saveAllSettingsButton.addEventListener('click', () => {
            // 从所有输入元素收集数据
            const settingsToSave = {
                qwen_vl_analysis_enabled: qwenAnalysisToggleControls ? qwenAnalysisToggleControls.checked : undefined,
                use_enhanced_search: useEnhancedSearchToggleControls ? useEnhancedSearchToggleControls.checked : undefined,
                qwen_model_name: qwenModelNameInput ? qwenModelNameInput.value.trim() : undefined,
                qwen_api_key: qwenApiKeyInput ? qwenApiKeyInput.value.trim() : undefined,
                qwen_base_url: qwenBaseUrlInput ? qwenBaseUrlInput.value.trim() : undefined,
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
                // 使用后端返回的已确认数据更新UI，确保同步
                if (data.settings) {
                    loadAppSettings(); // 简单地重新加载所有设置即可
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
        });
    }

    // --- 上传相关的功能 (保持不变) ---
    if (unifiedUploadButtonControls) {
        unifiedUploadButtonControls.addEventListener('click', () => {
            handleUnifiedUploadControls();
        });
    }
    if (cancelUploadButtonControls) {
        cancelUploadButtonControls.addEventListener('click', () => {
            if (currentUploadAbortController) {
                currentUploadAbortController.abort();
            }
        });
    }
    
    function resetUploadButtonsControls() {
        unifiedUploadButtonControls.disabled = false;
        cancelUploadButtonControls.style.display = 'none';
        if (unifiedUploadInputControls) unifiedUploadInputControls.value = null;
        currentUploadAbortController = null;
    }

    function handleUnifiedUploadControls() {
        const files = unifiedUploadInputControls.files;
        if (!files || files.length === 0) {
            uploadStatusControls.textContent = '请先选择文件。';
            return;
        }

        currentUploadAbortController = new AbortController();
        const signal = currentUploadAbortController.signal;

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
            resetUploadButtonsControls();
            return;
        }

        uploadStatusControls.textContent = `正在上传 ${fileCount} 张图片...`;
        unifiedUploadButtonControls.disabled = true;
        cancelUploadButtonControls.style.display = 'inline-block';

        fetch('/upload_images', {
            method: 'POST',
            body: formData,
            signal: signal
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
            resetUploadButtonsControls();
        });
    }
});