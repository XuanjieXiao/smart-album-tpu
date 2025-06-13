// AlbumForSearch/static/script.js
document.addEventListener('DOMContentLoaded', () => {
    // Nav Upload Elements
    const navUploadButton = document.getElementById('nav-upload-button');
    const hiddenUploadInput = document.getElementById('unified-upload-input-hidden');
    const mainUploadStatus = document.getElementById('upload-status-main'); 

    // Search Elements
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const searchStatus = document.getElementById('search-status');
    // New: Image Search Elements
    const imageSearchUploadButtonHero = document.getElementById('image-search-upload-button-hero');
    const imageSearchInputHero = document.getElementById('image-search-input-hero');
    const imageSearchPreviewHero = document.getElementById('image-search-preview-hero');
    const imageSearchFilenameHero = document.getElementById('image-search-filename-hero');
    const clearImageSearchHero = document.getElementById('clear-image-search-hero');
    let uploadedImageForSearchFile = null; // Stores the file for image search
    
    // Gallery Elements
    const imageGallery = document.getElementById('image-gallery');
    const loadingGallery = document.getElementById('loading-gallery');
    const totalImagesCountSpan = document.getElementById('total-images-count');
    const searchResultsTitleSpan = document.getElementById('search-results-title');
    const noMoreResultsDiv = document.getElementById('no-more-results');

    // Modal elements (Image Detail)
    const modal = document.getElementById('image-modal');
    const modalImageElement = document.getElementById('modal-image-element');
    const modalFilename = document.getElementById('modal-filename');
    const modalSimilarity = document.getElementById('modal-similarity');
    const modalSimilarityContainer = document.getElementById('modal-similarity-container');
    const modalQwenDescription = document.getElementById('modal-qwen-description');
    const modalQwenKeywords = document.getElementById('modal-qwen-keywords');
    const modalUserTags = document.getElementById('modal-user-tags');
    const modalIsEnhanced = document.getElementById('modal-is-enhanced');
    const modalEnhanceButton = document.getElementById('modal-enhance-button');
    const closeModalButton = modal.querySelector('.close-button');
    let currentModalImageId = null;

    // Batch Action Buttons (Nav Bar)
    const batchDeleteButton = document.getElementById('batch-delete-button');
    const batchTagButton = document.getElementById('batch-tag-button');
    
    // Gallery Controls
    const selectionInfoSpan = document.getElementById('selection-info');
    const selectedCountSpan = document.getElementById('selected-count');
    const clearSelectionButton = document.getElementById('clear-selection-button');

    // Confirm Delete Modal Elements
    const confirmDeleteModal = document.getElementById('confirm-delete-modal');
    const cancelDeleteButton = document.getElementById('cancel-delete-button');
    const confirmDeleteActionButton = document.getElementById('confirm-delete-action-button');
    const deleteCountSpan = document.getElementById('delete-count');
    const closeConfirmDeleteModalButton = confirmDeleteModal.querySelector('.close-button');

    // Add Tag Modal Elements
    const addTagModal = document.getElementById('add-tag-modal');
    const userTagsInput = document.getElementById('user-tags-input');
    const cancelTagButton = document.getElementById('cancel-tag-button');
    const confirmTagActionButton = document.getElementById('confirm-tag-action-button');
    const tagTargetCountSpan = document.getElementById('tag-target-count');
    const closeAddTagModalButton = addTagModal.querySelector('.close-button');
    
    let galleryCurrentPage = 1; 
    const GALLERY_IMAGES_PER_FETCH = 40; 
    let galleryTotalImages = 0;
    let displayedGalleryImagesCount = 0;
    let isLoadingMoreGalleryImages = false;

    let currentSearchResults = [];
    let displayedSearchResultsCount = 0;
    const searchResultsBatchSize = 20; 
    const ENHANCED_SEARCH_THRESHOLD = 0.50; 
    const CLIP_ONLY_SEARCH_THRESHOLD = 0.19; 
    const IMAGE_SEARCH_SIMILARITY_THRESHOLD = 0.6; // For image-to-image search
    let isLoadingMoreSearchResults = false;
    let navUploadAbortController = null; 

    let selectedImageIds = new Set(); 

    // --- Initial Setup ---
    if (navUploadButton && hiddenUploadInput) {
        navUploadButton.addEventListener('click', () => {
            hiddenUploadInput.value = null; 
            hiddenUploadInput.click(); 
        });
        hiddenUploadInput.addEventListener('change', () => {
            if (hiddenUploadInput.files.length > 0) {
                handleUnifiedUpload(hiddenUploadInput.files, navUploadButton, hiddenUploadInput, mainUploadStatus);
            }
        });
    }
    
    if (searchButton) searchButton.addEventListener('click', performSearch);
    if (searchInput) {
        searchInput.addEventListener('keypress', (event) => { 
            if (event.key === 'Enter') performSearch(); 
        });
    }

    // --- New Image Search UI Event Listeners ---
    if (imageSearchUploadButtonHero && imageSearchInputHero) {
        imageSearchUploadButtonHero.addEventListener('click', () => {
            imageSearchInputHero.value = null; // Reset file input
            imageSearchInputHero.click();
        });

        imageSearchInputHero.addEventListener('change', (event) => {
            const file = event.target.files[0];
            if (file) {
                uploadedImageForSearchFile = file;
                imageSearchFilenameHero.textContent = file.name.length > 20 ? file.name.substring(0, 17) + '...' : file.name;
                imageSearchPreviewHero.style.display = 'flex';
                searchInput.disabled = true;
                searchInput.placeholder = '图搜图模式，已选图片，将限制使用文字搜索功能';
                imageSearchUploadButtonHero.style.display = 'none'; // Hide upload button
            }
        });
    }

    if (clearImageSearchHero) {
        clearImageSearchHero.addEventListener('click', () => {
            uploadedImageForSearchFile = null;
            imageSearchInputHero.value = null; // Clear the file input
            imageSearchPreviewHero.style.display = 'none';
            imageSearchFilenameHero.textContent = '';
            searchInput.disabled = false;
            searchInput.placeholder = '输入中文描述搜索图片...';
            imageSearchUploadButtonHero.style.display = 'inline-flex'; // Show upload button
        });
    }


    // --- Batch Action Button Event Listeners ---
    if (batchDeleteButton) batchDeleteButton.addEventListener('click', openConfirmDeleteModal);
    if (batchTagButton) batchTagButton.addEventListener('click', openAddTagModal);
    if (clearSelectionButton) clearSelectionButton.addEventListener('click', clearAllSelections);

    // --- Modal Event Listeners ---
    if (closeModalButton) closeModalButton.addEventListener('click', closeImageDetailModal);
    window.addEventListener('click', (event) => { 
        if (event.target === modal) closeImageDetailModal();
        if (event.target === confirmDeleteModal) closeConfirmDeleteModal();
        if (event.target === addTagModal) closeAddTagModal();
    });

    if (cancelDeleteButton) cancelDeleteButton.addEventListener('click', closeConfirmDeleteModal);
    if (confirmDeleteActionButton) confirmDeleteActionButton.addEventListener('click', handleDeleteSelectedImages);
    if (closeConfirmDeleteModalButton) closeConfirmDeleteModalButton.addEventListener('click', closeConfirmDeleteModal);
    
    if (cancelTagButton) cancelTagButton.addEventListener('click', closeAddTagModal);
    if (confirmTagActionButton) confirmTagActionButton.addEventListener('click', handleAddTagsToSelectedImages);
    if (closeAddTagModalButton) closeAddTagModalButton.addEventListener('click', closeAddTagModal);


    // --- Core Functions ---
    function handleUnifiedUpload(files, buttonElement, inputElement, statusElement) {
        if (!files || files.length === 0) {
            if(statusElement) statusElement.textContent = '请先选择文件。';
            return;
        }
        if (navUploadAbortController) { 
            navUploadAbortController.abort();
        }
        navUploadAbortController = new AbortController();
        const signal = navUploadAbortController.signal;

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            if (files[i].type && !files[i].type.startsWith('image/')) {
                 console.warn(`(Main Page Upload) 跳过非图片文件: ${files[i].name} (type: ${files[i].type})`);
                 continue;
            }
            formData.append('files', files[i]);
        }
        const fileCount = formData.getAll('files').length;
        if (fileCount === 0) {
            if(statusElement) statusElement.textContent = '选择的文件中没有有效的图片文件。';
            if (inputElement) inputElement.value = null;
            return;
        }

        if(statusElement) statusElement.textContent = `正在上传 ${fileCount} 张图片...`;
        if (buttonElement) buttonElement.disabled = true;

        fetch('/upload_images', {
            method: 'POST',
            body: formData,
            signal: signal
        })
        .then(response => response.json())
        .then(data => {
            if (signal.aborted) return; 
            if (data.error) {
                if(statusElement) statusElement.textContent = `上传失败: ${data.error}`;
            } else {
                if(statusElement) statusElement.textContent = data.message || `成功处理 ${data.processed_files?.length || 0} 张图片。`;
                switchToGalleryView(true); 
            }
        })
        .catch(error => {
            if (error.name === 'AbortError') {
                if(statusElement) statusElement.textContent = '上传已取消。';
            } else {
                console.error('上传错误 (Main Page):', error);
                if(statusElement) statusElement.textContent = '上传过程中发生网络错误。';
            }
        })
        .finally(() => {
            if (buttonElement) buttonElement.disabled = false;
            if (inputElement) inputElement.value = null;
            navUploadAbortController = null;
            setTimeout(() => {
                if (statusElement && (statusElement.textContent.includes("上传") || statusElement.textContent.includes("处理"))) {
                  if(statusElement) statusElement.textContent = ''; 
                }
            }, 7000);
        });
    }

    function performSearch() {
        clearAllSelections();
        imageGallery.innerHTML = '';
        currentSearchResults = [];
        displayedSearchResultsCount = 0;
        loadingGallery.style.display = 'flex';
        if(searchButton) searchButton.disabled = true;
        if(searchStatus) searchStatus.textContent = '正在搜索...';
        if(mainUploadStatus) mainUploadStatus.textContent = '';
        if(searchResultsTitleSpan) searchResultsTitleSpan.style.display = 'inline';
        if(noMoreResultsDiv) noMoreResultsDiv.style.display = 'none';

        if (uploadedImageForSearchFile) {
            // Perform image-to-image search
            const formData = new FormData();
            formData.append('image_query_file', uploadedImageForSearchFile);
            if(searchStatus) searchStatus.textContent = `正在以图搜图: ${uploadedImageForSearchFile.name}...`;

            fetch('/search_by_uploaded_image', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    if(searchStatus) searchStatus.textContent = `图搜图失败: ${data.error}`;
                    imageGallery.innerHTML = `<p>图搜图失败: ${data.error}</p>`;
                } else {
                    // Filter by IMAGE_SEARCH_SIMILARITY_THRESHOLD is done backend now
                    currentSearchResults = data.results; 
                    const queryFileNameDisplay = data.query_filename || "上传的图片";
                    if (currentSearchResults.length > 0) {
                        if(searchStatus) searchStatus.textContent = `图搜图 "${queryFileNameDisplay}": 找到 ${currentSearchResults.length} 张相似图片 (阈值 > ${IMAGE_SEARCH_SIMILARITY_THRESHOLD.toFixed(2)})。`;
                        loadMoreSearchResults();
                    } else {
                        if(searchStatus) searchStatus.textContent = `图搜图 "${queryFileNameDisplay}": 未找到相似度 > ${IMAGE_SEARCH_SIMILARITY_THRESHOLD.toFixed(2)} 的图片。`;
                        imageGallery.innerHTML = `<p>未找到与图片 "${queryFileNameDisplay}" 匹配且相似度足够高的图片 (阈值: ${IMAGE_SEARCH_SIMILARITY_THRESHOLD.toFixed(2)})。</p>`;
                    }
                }
            })
            .catch(error => {
                console.error('图搜图API错误:', error);
                if(searchStatus) searchStatus.textContent = '图搜图过程中发生网络错误。';
                imageGallery.innerHTML = '<p>图搜图过程中发生网络错误。</p>';
            })
            .finally(() => {
                loadingGallery.style.display = 'none';
                if(searchButton) searchButton.disabled = false;
            });

        } else {
            // Perform text search
            const queryText = searchInput.value.trim();
            if (!queryText) {
                if(searchStatus) searchStatus.textContent = '请输入搜索描述。';
                loadingGallery.style.display = 'none';
                if(searchButton) searchButton.disabled = false;
                return;
            }
            if(searchStatus) searchStatus.textContent = `正在文搜图: "${queryText}"...`;

            fetch('/search_images', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query_text: queryText, top_k: 200 }) 
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    if(searchStatus) searchStatus.textContent = `搜索失败: ${data.error}`;
                    imageGallery.innerHTML = `<p>搜索失败: ${data.error}</p>`;
                } else {
                    const activeSimilarityThreshold = data.search_mode_is_enhanced ? ENHANCED_SEARCH_THRESHOLD : CLIP_ONLY_SEARCH_THRESHOLD;
                    currentSearchResults = data.results.filter(img => img.similarity >= activeSimilarityThreshold);
                    
                    if (currentSearchResults.length > 0) {
                        if(searchStatus) searchStatus.textContent = `文搜图 "${queryText}": 找到 ${currentSearchResults.length} 张相似度 >= ${activeSimilarityThreshold.toFixed(2)} 的相关图片。`;
                        loadMoreSearchResults(); 
                    } else {
                        if(searchStatus) searchStatus.textContent = `文搜图 "${queryText}": 未找到相似度 >= ${activeSimilarityThreshold.toFixed(2)} 的图片。`;
                        imageGallery.innerHTML = `<p>未找到与描述 "${queryText}" 匹配且相似度足够高的图片 (阈值: ${activeSimilarityThreshold.toFixed(2)})。</p>`;
                    }
                }
            })
            .catch(error => {
                console.error('文搜图API错误:', error);
                if(searchStatus) searchStatus.textContent = '文搜图过程中发生网络错误。';
                imageGallery.innerHTML = '<p>文搜图过程中发生网络错误。</p>';
            })
            .finally(() => {
                loadingGallery.style.display = 'none';
                if(searchButton) searchButton.disabled = false;
            });
        }
    }


    function loadMoreSearchResults() {
        if (isLoadingMoreSearchResults || displayedSearchResultsCount >= currentSearchResults.length) return;
        isLoadingMoreSearchResults = true;
        loadingGallery.style.display = 'flex';

        const nextBatch = currentSearchResults.slice(
            displayedSearchResultsCount,
            displayedSearchResultsCount + searchResultsBatchSize
        );

        if (nextBatch.length > 0) {
            displayImages(nextBatch, true, true); 
            displayedSearchResultsCount += nextBatch.length;
            if(noMoreResultsDiv) noMoreResultsDiv.style.display = 'none';
        } else {
             if(noMoreResultsDiv && displayedSearchResultsCount > 0) noMoreResultsDiv.style.display = 'block';
        }
        isLoadingMoreSearchResults = false;
        loadingGallery.style.display = 'none';
    }

    function displayImages(images, isSearchResult = false, append = false) {
        if (!append) {
            imageGallery.innerHTML = '';
        }
        if (!images || images.length === 0) {
            if (!append) { 
                 const activeThreshold = isSearchResult ? 
                    (currentSearchResults.length > 0 && !JSON.parse(sessionStorage.getItem('appSettings') || '{}').use_enhanced_search ? CLIP_ONLY_SEARCH_THRESHOLD : ENHANCED_SEARCH_THRESHOLD) 
                    : ENHANCED_SEARCH_THRESHOLD; 
                 if (isSearchResult) { // This message is now more generic as performSearch sets specific messages
                    imageGallery.innerHTML = `<p>未找到符合条件的图片。</p>`;
                 } else {
                    imageGallery.innerHTML = '<p>图片库为空，请上传图片。</p>';
                 }
            }
            return;
        }
        images.forEach(img => {
            const item = document.createElement('div');
            item.classList.add('gallery-item');
            item.dataset.imageId = img.id; 
            item.dataset.originalUrl = img.original_url;
            item.dataset.filename = img.filename;
            if (isSearchResult && img.similarity !== undefined) {
                item.dataset.similarity = img.similarity.toFixed(4);
            }

            const imgElement = document.createElement('img');
            imgElement.src = img.thumbnail_url || 'https://placehold.co/160x130/eee/ccc?text=NoThumb';
            imgElement.alt = img.filename;
            imgElement.onerror = () => { imgElement.src = 'https://placehold.co/160x130/eee/ccc?text=Error'; };
            
            const nameElement = document.createElement('p');
            nameElement.textContent = img.filename.length > 20 ? img.filename.substring(0, 17) + '...' : img.filename;
            
            item.appendChild(imgElement);
            item.appendChild(nameElement);
            
            if (isSearchResult && img.similarity !== undefined) {
                const similarityElement = document.createElement('p');
                similarityElement.classList.add('similarity');
                similarityElement.textContent = `相似度: ${img.similarity.toFixed(4)}`;
                item.appendChild(similarityElement);
            }
            if (img.is_enhanced) {
                const enhancedBadge = document.createElement('span');
                enhancedBadge.classList.add('enhanced-badge');
                enhancedBadge.textContent = '已增强';
                item.appendChild(enhancedBadge);
            }

            item.addEventListener('click', (event) => {
                event.stopPropagation(); 
                toggleImageSelection(img.id, item);
            });
            
             item.addEventListener('dblclick', () => {
                 openImageDetailModal(img.id, img.original_url, img.filename, isSearchResult, item.dataset.similarity);
             });

            if (selectedImageIds.has(String(img.id))) {
                item.classList.add('selected');
            }

            imageGallery.appendChild(item);
        });
    }

    function toggleImageSelection(imageId, itemElement) {
        const idStr = String(imageId);
        if (selectedImageIds.has(idStr)) {
            selectedImageIds.delete(idStr);
            itemElement.classList.remove('selected');
        } else {
            selectedImageIds.add(idStr);
            itemElement.classList.add('selected');
        }
        updateSelectionControls();
    }

    function updateSelectionControls() {
        const count = selectedImageIds.size;
        if (selectedCountSpan) selectedCountSpan.textContent = count;

        if (count > 0) {
            if (batchDeleteButton) batchDeleteButton.style.display = 'inline-flex';
            if (batchTagButton) batchTagButton.style.display = 'inline-flex';
            if (selectionInfoSpan) selectionInfoSpan.style.display = 'inline';
            if (clearSelectionButton) clearSelectionButton.style.display = 'inline-flex';
        } else {
            if (batchDeleteButton) batchDeleteButton.style.display = 'none';
            if (batchTagButton) batchTagButton.style.display = 'none';
            if (selectionInfoSpan) selectionInfoSpan.style.display = 'none';
            if (clearSelectionButton) clearSelectionButton.style.display = 'none';
        }
    }
    
    function clearAllSelections() {
        selectedImageIds.forEach(id => {
            const item = imageGallery.querySelector(`.gallery-item[data-image-id='${id}']`);
            if (item) {
                item.classList.remove('selected');
            }
        });
        selectedImageIds.clear();
        updateSelectionControls();
    }


    function openImageDetailModal(imageId, originalUrl, filename, isSearchResult, similarityScore) {
        currentModalImageId = imageId;
        if (modalImageElement) modalImageElement.src = originalUrl || 'https://placehold.co/600x400?text=No+Image';
        if (modalFilename) modalFilename.textContent = filename || '未知文件';
        
        if (modalSimilarityContainer && modalSimilarity) {
            if (isSearchResult && similarityScore !== undefined && similarityScore !== 'N/A') {
                modalSimilarity.textContent = similarityScore;
                modalSimilarityContainer.style.display = 'block';
            } else {
                modalSimilarity.textContent = 'N/A';
                modalSimilarityContainer.style.display = 'none';
            }
        }

        if(modalQwenDescription) modalQwenDescription.textContent = '加载中...';
        if(modalQwenKeywords) modalQwenKeywords.textContent = '加载中...';
        if(modalUserTags) modalUserTags.textContent = '加载中...'; 
        if(modalIsEnhanced) modalIsEnhanced.textContent = '加载中...';
        if(modalEnhanceButton) modalEnhanceButton.style.display = 'none'; 
        
        if(modal) modal.style.display = 'flex';

        fetch(`/image_details/${imageId}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    if(modalQwenDescription) modalQwenDescription.textContent = '获取详情失败';
                    if(modalQwenKeywords) modalQwenKeywords.textContent = '获取详情失败';
                    if(modalUserTags) modalUserTags.textContent = '获取详情失败';
                    if(modalIsEnhanced) modalIsEnhanced.textContent = '获取详情失败';
                    return;
                }
                if(modalQwenDescription) modalQwenDescription.textContent = data.qwen_description || '无';
                if(modalQwenKeywords) modalQwenKeywords.textContent = data.qwen_keywords && data.qwen_keywords.length > 0 ? data.qwen_keywords.join(', ') : '无';
                if(modalUserTags) modalUserTags.textContent = data.user_tags && data.user_tags.length > 0 ? data.user_tags.join(', ') : '无';
                
                const isEnhanced = data.is_enhanced;
                if(modalIsEnhanced) modalIsEnhanced.textContent = isEnhanced ? '是' : '否';
                
                if(modalEnhanceButton){ 
                    if (!isEnhanced) {
                        modalEnhanceButton.style.display = 'inline-block';
                    } else {
                        modalEnhanceButton.style.display = 'none';
                    }
                }
            })
            .catch(error => {
                console.error('获取图片详情API错误:', error);
                if(modalQwenDescription) modalQwenDescription.textContent = '网络错误';
                if(modalQwenKeywords) modalQwenKeywords.textContent = '网络错误';
                if(modalUserTags) modalUserTags.textContent = '网络错误';
                if(modalIsEnhanced) modalIsEnhanced.textContent = '网络错误';
            });
    }

    function closeImageDetailModal() {
        if(modal) modal.style.display = 'none';
        currentModalImageId = null;
    }
    
    function openConfirmDeleteModal() {
        const count = selectedImageIds.size;
        if (count === 0) {
            alert("请先选择要删除的图片。");
            return;
        }
        if (deleteCountSpan) deleteCountSpan.textContent = count;
        if (confirmDeleteModal) confirmDeleteModal.style.display = 'flex';
    }

    function closeConfirmDeleteModal() {
        if (confirmDeleteModal) confirmDeleteModal.style.display = 'none';
    }

    function handleDeleteSelectedImages() {
        const idsToDelete = Array.from(selectedImageIds);
        if (idsToDelete.length === 0) return;

        confirmDeleteActionButton.disabled = true;
        confirmDeleteActionButton.textContent = '正在删除...';

        fetch('/delete_images_batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_ids: idsToDelete })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message || `${idsToDelete.length} 张图片已成功删除。`);
                idsToDelete.forEach(id => {
                    const item = imageGallery.querySelector(`.gallery-item[data-image-id='${id}']`);
                    if (item) item.remove();
                });
                galleryTotalImages -= idsToDelete.length; 
                if(totalImagesCountSpan) totalImagesCountSpan.textContent = galleryTotalImages;
                clearAllSelections();
            } else {
                alert(`删除失败: ${data.error || '未知错误'}`);
            }
        })
        .catch(error => {
            console.error('删除图片API错误:', error);
            alert('删除过程中发生网络错误。');
        })
        .finally(() => {
            confirmDeleteActionButton.disabled = false;
            confirmDeleteActionButton.textContent = '确认删除';
            closeConfirmDeleteModal();
        });
    }

    function openAddTagModal() {
        const count = selectedImageIds.size;
        if (count === 0) {
            alert("请先选择要添加标签的图片。");
            return;
        }
        if (tagTargetCountSpan) tagTargetCountSpan.textContent = count;
        if (userTagsInput) userTagsInput.value = ''; 
        if (addTagModal) addTagModal.style.display = 'flex';
    }

    function closeAddTagModal() {
        if (addTagModal) addTagModal.style.display = 'none';
    }

    function handleAddTagsToSelectedImages() {
        const idsToTag = Array.from(selectedImageIds);
        const tagsString = userTagsInput.value.trim();
        if (idsToTag.length === 0) return;
        if (!tagsString) {
            alert("请输入要添加的标签。");
            return;
        }
        const tagsArray = tagsString.split(',').map(tag => tag.trim()).filter(tag => tag.length > 0);
        if (tagsArray.length === 0) {
            alert("请输入有效的标签。");
            return;
        }

        confirmTagActionButton.disabled = true;
        confirmTagActionButton.textContent = '正在添加...';

        fetch('/add_user_tags_batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_ids: idsToTag, user_tags: tagsArray })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert(data.message || `标签已成功添加到 ${idsToTag.length} 张图片。`);
            } else {
                alert(`添加标签失败: ${data.error || '未知错误'}`);
            }
        })
        .catch(error => {
            console.error('添加标签API错误:', error);
            alert('添加标签过程中发生网络错误。');
        })
        .finally(() => {
            confirmTagActionButton.disabled = false;
            confirmTagActionButton.textContent = '确认添加';
            closeAddTagModal();
        });
    }


    if (modalEnhanceButton) {
        modalEnhanceButton.addEventListener('click', () => {
            if (!currentModalImageId) return;
            modalEnhanceButton.disabled = true;
            modalEnhanceButton.textContent = '正在增强...';
            fetch(`/enhance_image/${currentModalImageId}`, { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        alert(`增强失败: ${data.error}`);
                        if(data.is_enhanced !== undefined) { 
                            if(modalIsEnhanced) modalIsEnhanced.textContent = data.is_enhanced ? '是' : '否';
                            if (data.qwen_description && modalQwenDescription) modalQwenDescription.textContent = data.qwen_description;
                            if (data.qwen_keywords && modalQwenKeywords) modalQwenKeywords.textContent = data.qwen_keywords.join(', ');
                            if(data.is_enhanced && modalEnhanceButton) modalEnhanceButton.style.display = 'none';
                        }
                    } else {
                        alert(data.message || '增强请求已发送，图片已更新。');
                        if(modalQwenDescription) modalQwenDescription.textContent = data.qwen_description || '无';
                        if(modalQwenKeywords) modalQwenKeywords.textContent = data.qwen_keywords && data.qwen_keywords.length > 0 ? data.qwen_keywords.join(', ') : '无';
                        if(modalIsEnhanced) modalIsEnhanced.textContent = data.is_enhanced ? '是' : '否';
                        if (data.is_enhanced && modalEnhanceButton) {
                            modalEnhanceButton.style.display = 'none';
                        }
                        const galleryItem = document.querySelector(`.gallery-item[data-image-id='${currentModalImageId}']`);
                        if (galleryItem) {
                            const existingBadge = galleryItem.querySelector('.enhanced-badge');
                            if (data.is_enhanced && !existingBadge) {
                                 const enhancedBadge = document.createElement('span');
                                 enhancedBadge.classList.add('enhanced-badge');
                                 enhancedBadge.textContent = '已增强';
                                 galleryItem.appendChild(enhancedBadge);
                            } else if (!data.is_enhanced && existingBadge) {
                                existingBadge.remove();
                            }
                        }
                    }
                })
                .catch(error => {
                    console.error('增强图片API错误:', error);
                    alert('增强请求失败。');
                })
                .finally(() => {
                    modalEnhanceButton.disabled = false;
                    modalEnhanceButton.textContent = '对此图片进行增强分析';
                });
        });
    }
    
    function switchToGalleryView(forceRefresh = false) {
        // Clear search state
        if (uploadedImageForSearchFile && clearImageSearchHero) { // If image search was active
             clearImageSearchHero.click(); // Simulate click to reset UI
        }
        currentSearchResults = []; 
        displayedSearchResultsCount = 0;
        if(searchInput) searchInput.value = '';
        if(searchStatus) searchStatus.textContent = '';
        if(mainUploadStatus) mainUploadStatus.textContent = ''; 
        if(searchResultsTitleSpan) searchResultsTitleSpan.style.display = 'none';
        if(noMoreResultsDiv) noMoreResultsDiv.style.display = 'none';
        
        if (forceRefresh) {
            imageGallery.innerHTML = ''; 
            galleryCurrentPage = 1;
            displayedGalleryImagesCount = 0;
            galleryTotalImages = 0; 
            clearAllSelections(); 
        }
        loadGalleryImagesBatch(); 
    }

    function loadGalleryImagesBatch() {
        if (isLoadingMoreGalleryImages) return;
        if (galleryTotalImages > 0 && displayedGalleryImagesCount >= galleryTotalImages && galleryCurrentPage > 1) { 
            if(noMoreResultsDiv && displayedGalleryImagesCount > 0) noMoreResultsDiv.style.display = 'block';
            return;
        }

        isLoadingMoreGalleryImages = true;
        loadingGallery.style.display = 'flex';

        fetch(`/images?page=${galleryCurrentPage}&limit=${GALLERY_IMAGES_PER_FETCH}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    imageGallery.innerHTML = `<p>加载图片库失败: ${data.error}</p>`;
                } else {
                    if (galleryCurrentPage === 1 && displayedGalleryImagesCount === 0) { 
                        imageGallery.innerHTML = ''; 
                    }
                    displayImages(data.images, false, true); 
                    displayedGalleryImagesCount += data.images.length;
                    galleryTotalImages = data.total_count;
                    if(totalImagesCountSpan) totalImagesCountSpan.textContent = galleryTotalImages;

                    if (displayedGalleryImagesCount >= galleryTotalImages) {
                        if(noMoreResultsDiv && displayedGalleryImagesCount > 0) noMoreResultsDiv.style.display = 'block';
                    } else {
                        if(noMoreResultsDiv) noMoreResultsDiv.style.display = 'none';
                        galleryCurrentPage++; 
                    }
                }
            })
            .catch(error => {
                console.error('加载图片库错误:', error);
                imageGallery.innerHTML = '<p>加载图片库时发生网络错误。</p>';
            })
            .finally(() => {
                loadingGallery.style.display = 'none';
                isLoadingMoreGalleryImages = false;
            });
    }

    window.addEventListener('scroll', () => {
        const inSearchMode = currentSearchResults.length > 0 && displayedSearchResultsCount < currentSearchResults.length;
        const inGalleryMode = !currentSearchResults.length && (galleryTotalImages === 0 || displayedGalleryImagesCount < galleryTotalImages);

        if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 300) { 
            if (inSearchMode && !isLoadingMoreSearchResults) {
                 loadMoreSearchResults();
            } else if (inGalleryMode && !isLoadingMoreGalleryImages) {
                 loadGalleryImagesBatch();
            }
        }
    });

    fetch('/config/settings').then(r => r.json()).then(settings => {
        sessionStorage.setItem('appSettings', JSON.stringify(settings));
    }).catch(e => console.error("Failed to fetch initial app settings for JS:", e));

    switchToGalleryView(true);
    updateSelectionControls(); 
});