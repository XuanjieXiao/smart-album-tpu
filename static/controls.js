// // static/controls.js
// document.addEventListener('DOMContentLoaded', () => {
//     // Settings Elements
//     const qwenAnalysisToggleControls = document.getElementById('qwen-analysis-toggle-controls');
//     const qwenStatusTextControls = document.getElementById('qwen-status-text-controls');
//     const useEnhancedSearchToggleControls = document.getElementById('use-enhanced-search-toggle-controls');
//     // const useEnhancedSearchStatusControls = document.getElementById('use-enhanced-search-status-controls'); // Not strictly needed if checkbox state is clear
//     const saveSettingsButton = document.getElementById('save-settings-button');
//     const saveSettingsStatus = document.getElementById('save-settings-status');

//     // Upload elements for controls.html
//     const unifiedUploadInputControls = document.getElementById('unified-upload-input-controls');
//     const unifiedUploadButtonControls = document.getElementById('unified-upload-button-controls');
//     const cancelUploadButtonControls = document.getElementById('cancel-upload-button-controls');
//     const uploadStatusControls = document.getElementById('upload-status-controls');
    
//     let currentUploadAbortController = null; // For aborting uploads

//     // --- Initial State Setup for Controls Page ---
//     function loadAppSettings() {
//         fetch('/config/settings')
//             .then(response => response.json())
//             .then(data => {
//                 if (qwenAnalysisToggleControls) {
//                     qwenAnalysisToggleControls.checked = data.qwen_vl_analysis_enabled === true;
//                     qwenStatusTextControls.textContent = data.qwen_vl_analysis_enabled ? '已开启' : '已关闭';
//                 }
//                 if (useEnhancedSearchToggleControls) {
//                     useEnhancedSearchToggleControls.checked = data.use_enhanced_search === true;
//                 }
//             })
//             .catch(error => {
//                 console.error('获取应用设置失败 (controls):', error);
//                 if(qwenStatusTextControls) qwenStatusTextControls.textContent = '获取配置失败';
//                 if(saveSettingsStatus) saveSettingsStatus.textContent = '获取设置失败';
//             });
//     }

//     if (qwenAnalysisToggleControls || useEnhancedSearchToggleControls) {
//         loadAppSettings();
//     }
    
//     // --- Event Listeners for Controls Page ---
//     if (saveSettingsButton) {
//         saveSettingsButton.addEventListener('click', () => {
//             const settingsToSave = {
//                 qwen_vl_analysis_enabled: qwenAnalysisToggleControls ? qwenAnalysisToggleControls.checked : undefined,
//                 use_enhanced_search: useEnhancedSearchToggleControls ? useEnhancedSearchToggleControls.checked : undefined,
//             };

//             // Filter out undefined values if some toggles don't exist on the page
//             const payload = Object.fromEntries(Object.entries(settingsToSave).filter(([_, v]) => v !== undefined));

//             saveSettingsStatus.textContent = '正在保存...';
//             saveSettingsButton.disabled = true;

//             fetch('/config/settings', {
//                 method: 'POST',
//                 headers: { 'Content-Type': 'application/json' },
//                 body: JSON.stringify(payload)
//             })
//             .then(response => response.json())
//             .then(data => {
//                 if (data.message) {
//                     saveSettingsStatus.textContent = data.message;
//                 }
//                 // Update UI based on potentially modified settings from backend (if backend modifies them)
//                 if (data.settings) {
//                      if (qwenAnalysisToggleControls && data.settings.qwen_vl_analysis_enabled !== undefined) {
//                         qwenAnalysisToggleControls.checked = data.settings.qwen_vl_analysis_enabled;
//                         qwenStatusTextControls.textContent = data.settings.qwen_vl_analysis_enabled ? '已开启' : '已关闭';
//                     }
//                     if (useEnhancedSearchToggleControls && data.settings.use_enhanced_search !== undefined) {
//                         useEnhancedSearchToggleControls.checked = data.settings.use_enhanced_search;
//                     }
//                 }
//                  setTimeout(() => { saveSettingsStatus.textContent = ''; }, 3000);
//             })
//             .catch(error => {
//                 console.error('保存设置失败 (controls):', error);
//                 saveSettingsStatus.textContent = '保存设置失败!';
//             })
//             .finally(() => {
//                  saveSettingsButton.disabled = false;
//             });
//         });
//     }
    

//     // Unified Upload Handler for Controls Page
//     if (unifiedUploadButtonControls) {
//         unifiedUploadButtonControls.addEventListener('click', () => {
//             handleUnifiedUploadControls();
//         });
//     }
//     if (cancelUploadButtonControls) {
//         cancelUploadButtonControls.addEventListener('click', () => {
//             if (currentUploadAbortController) {
//                 currentUploadAbortController.abort();
//                 uploadStatusControls.textContent = '上传已取消。';
//                 console.log("Upload cancelled by user.");
//                 resetUploadButtonsControls();
//             }
//         });
//     }
    
//     function resetUploadButtonsControls() {
//         unifiedUploadButtonControls.disabled = false;
//         cancelUploadButtonControls.style.display = 'none';
//         if (unifiedUploadInputControls) unifiedUploadInputControls.value = null; // Clear file input
//     }

//     function handleUnifiedUploadControls() {
//         const files = unifiedUploadInputControls.files;
//         if (!files || files.length === 0) {
//             uploadStatusControls.textContent = '请先选择文件。';
//             return;
//         }

//         currentUploadAbortController = new AbortController(); // Create a new AbortController for this upload
//         const signal = currentUploadAbortController.signal;

//         const formData = new FormData();
//         for (let i = 0; i < files.length; i++) {
//             if (files[i].type && !files[i].type.startsWith('image/')) {
//                  console.warn(`(Controls) 跳过非图片文件: ${files[i].name} (type: ${files[i].type})`);
//                  continue;
//             }
//             formData.append('files', files[i]);
//         }

//         const fileCount = formData.getAll('files').length;
//         if (fileCount === 0) {
//             uploadStatusControls.textContent = '选择的文件中没有有效的图片文件。';
//             resetUploadButtonsControls();
//             return;
//         }

//         uploadStatusControls.textContent = `正在上传 ${fileCount} 张图片... (0%)`;
//         unifiedUploadButtonControls.disabled = true;
//         cancelUploadButtonControls.style.display = 'inline-block';

//         // Basic progress simulation (xhr would be better for real progress)
//         let progress = 0;
//         const progressInterval = setInterval(() => {
//             if (signal.aborted) {
//                 clearInterval(progressInterval);
//                 return;
//             }
//             progress += 10;
//             if (progress < 100) {
//                 uploadStatusControls.textContent = `正在上传 ${fileCount} 张图片... (${progress}%)`;
//             }
//         }, 200);


//         fetch('/upload_images', {
//             method: 'POST',
//             body: formData,
//             signal: signal // Pass the abort signal to fetch
//         })
//         .then(response => {
//             clearInterval(progressInterval);
//             if (!response.ok) { // Check for HTTP errors like 500
//                 // Try to get error message from response if possible
//                 return response.json().then(errData => {
//                     throw new Error(errData.error || `HTTP error! status: ${response.status}`);
//                 }).catch(() => { // Fallback if response is not JSON or no error field
//                     throw new Error(`HTTP error! status: ${response.status}`);
//                 });
//             }
//             return response.json();
//         })
//         .then(data => {
//             if (data.error) { // Application-level error from our JSON response
//                 uploadStatusControls.textContent = `上传失败: ${data.error}`;
//             } else {
//                 uploadStatusControls.textContent = (data.message || `成功处理 ${data.processed_files?.length || 0} 张图片。`) + " 返回主页可查看。";
//             }
//         })
//         .catch(error => {
//             clearInterval(progressInterval);
//             if (error.name === 'AbortError') {
//                 uploadStatusControls.textContent = '上传已由用户取消。';
//                 console.log('Fetch aborted by user.');
//             } else {
//                 console.error('上传错误 (controls):', error);
//                 uploadStatusControls.textContent = `上传过程中发生错误: ${error.message}`;
//             }
//         })
//         .finally(() => {
//             clearInterval(progressInterval); // Ensure interval is cleared
//             resetUploadButtonsControls();
//             currentUploadAbortController = null; // Clear the controller
//         });
//     }
// });

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