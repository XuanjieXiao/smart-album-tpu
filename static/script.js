// AlbumForSearch/static/script.js
document.addEventListener('DOMContentLoaded', () => {
    // ---- 视图和状态管理 ----
    let currentView = 'gallery'; // 'gallery' or 'face'
    let selectedImageIds = new Set();
    
    // ---- 元素获取 ----
    // 导航
    const navUploadButton = document.getElementById('nav-upload-button');
    const hiddenUploadInput = document.getElementById('unified-upload-input-hidden');
    const navFaceViewButton = document.getElementById('nav-face-view-button');
    const navBrandLink = document.getElementById('nav-brand-link');

    // 视图容器
    const galleryViewContainer = document.getElementById('gallery-view-container');
    const faceViewContainer = document.getElementById('face-view-container');

    // 主搜索 (图库视图)
    const searchInput = document.getElementById('search-input');
    const searchButton = document.getElementById('search-button');
    const searchStatus = document.getElementById('search-status');
    const imageSearchUploadButtonHero = document.getElementById('image-search-upload-button-hero');
    const imageSearchInputHero = document.getElementById('image-search-input-hero');
    const imageSearchPreviewHero = document.getElementById('image-search-preview-hero');
    const imageSearchFilenameHero = document.getElementById('image-search-filename-hero');
    const clearImageSearchHero = document.getElementById('clear-image-search-hero');
    let uploadedImageForSearchFile = null;

    // 人脸视图元素
    const faceClusterCarousel = document.getElementById('face-cluster-carousel');
    const loadingClusters = document.getElementById('loading-clusters');
    const carouselArrowLeft = document.getElementById('carousel-arrow-left');
    const carouselArrowRight = document.getElementById('carousel-arrow-right');
    const faceSearchInputText = document.getElementById('face-search-input-text');
    const faceSearchButtonAction = document.getElementById('face-search-button-action');
    const faceSearchStatus = document.getElementById('face-search-status');
    const faceSearchUploadButton = document.getElementById('face-search-upload-button');
    const faceSearchInputImage = document.getElementById('face-search-input-image');
    const faceSearchPreview = document.getElementById('face-search-preview');
    const faceSearchFilename = document.getElementById('face-search-filename');
    const clearFaceSearchImage = document.getElementById('clear-face-search-image');
    let uploadedImageForFaceSearchFile = null;

    // 通用图库区域
    const gallerySection = document.querySelector('.gallery-section');
    const galleryTitle = document.getElementById('gallery-title');
    const imageGallery = document.getElementById('image-gallery');
    const loadingGallery = document.getElementById('loading-gallery');
    const totalImagesCountSpan = document.getElementById('total-images-count');
    const noMoreResultsDiv = document.getElementById('no-more-results');
    const mainUploadStatus = document.getElementById('upload-status-main');
    
    // 批量操作
    const batchDeleteButton = document.getElementById('batch-delete-button');
    const batchTagButton = document.getElementById('batch-tag-button');
    const selectionInfoSpan = document.getElementById('selection-info');
    const selectedCountSpan = document.getElementById('selected-count');
    const clearSelectionButton = document.getElementById('clear-selection-button');
    
    // 弹窗 (Modals)
    const modal = document.getElementById('image-modal');
    const confirmDeleteModal = document.getElementById('confirm-delete-modal');
    const addTagModal = document.getElementById('add-tag-modal');
    // (Modal-specific elements are referenced inside their functions)
    let currentModalImageId = null;

    // ---- 数据和加载状态 ----
    let galleryCurrentPage = 1, galleryTotalImages = 0, displayedGalleryImagesCount = 0, isLoadingMoreGalleryImages = false;
    const GALLERY_IMAGES_PER_FETCH = 40;
    
    let currentSearchResults = [], displayedSearchResultsCount = 0, isLoadingMoreSearchResults = false;
    const searchResultsBatchSize = 40;
    
    const ENHANCED_SEARCH_THRESHOLD = 0.50; 
    const CLIP_ONLY_SEARCH_THRESHOLD = 0.19; 
    const IMAGE_SEARCH_SIMILARITY_THRESHOLD = 0.6;
    
    let navUploadAbortController = null;

    // ===================================================================
    // ==================== 1. 初始化和事件监听设置 ====================
    // ===================================================================

    function initializeEventListeners() {
        // 导航栏按钮
        navUploadButton?.addEventListener('click', () => hiddenUploadInput.click());
        hiddenUploadInput?.addEventListener('change', () => {
            if (hiddenUploadInput.files.length > 0) handleUnifiedUpload(hiddenUploadInput.files);
        });
        navFaceViewButton?.addEventListener('click', switchToFaceView);
        navBrandLink?.addEventListener('click', (e) => {
            e.preventDefault();
            switchToGalleryView(true);
        });

        // 图库视图搜索
        searchButton?.addEventListener('click', performSearch);
        searchInput?.addEventListener('keypress', (e) => { if (e.key === 'Enter') performSearch(); });
        imageSearchUploadButtonHero?.addEventListener('click', () => imageSearchInputHero.click());
        imageSearchInputHero?.addEventListener('change', handleImageSearchFileSelect);
        clearImageSearchHero?.addEventListener('click', clearImageSearchFile);

        // 人脸视图搜索
        faceSearchButtonAction?.addEventListener('click', performFaceSearch);
        faceSearchInputText?.addEventListener('keypress', (e) => { if (e.key === 'Enter') performFaceSearch(); });
        faceSearchUploadButton?.addEventListener('click', () => faceSearchInputImage.click());
        faceSearchInputImage?.addEventListener('change', handleFaceSearchFileSelect);
        clearFaceSearchImage?.addEventListener('click', clearFaceSearchFile);

        // 人脸聚类轮播箭头
        carouselArrowLeft?.addEventListener('click', () => scrollCarousel(-1));
        carouselArrowRight?.addEventListener('click', () => scrollCarousel(1));

        // 批量操作
        batchDeleteButton?.addEventListener('click', openConfirmDeleteModal);
        batchTagButton?.addEventListener('click', openAddTagModal);
        clearSelectionButton?.addEventListener('click', clearAllSelections);

        // 弹窗关闭事件
        modal?.querySelector('.close-button')?.addEventListener('click', closeImageDetailModal);
        confirmDeleteModal?.querySelector('.close-button')?.addEventListener('click', closeConfirmDeleteModal);
        addTagModal?.querySelector('.close-button')?.addEventListener('click', closeAddTagModal);
        window.addEventListener('click', (event) => { 
            if (event.target === modal) closeImageDetailModal();
            if (event.target === confirmDeleteModal) closeConfirmDeleteModal();
            if (event.target === addTagModal) closeAddTagModal();
        });

        // 弹窗动作按钮
        confirmDeleteModal?.querySelector('#confirm-delete-action-button')?.addEventListener('click', handleDeleteSelectedImages);
        confirmDeleteModal?.querySelector('#cancel-delete-button')?.addEventListener('click', closeConfirmDeleteModal);
        addTagModal?.querySelector('#confirm-tag-action-button')?.addEventListener('click', handleAddTagsToSelectedImages);
        addTagModal?.querySelector('#cancel-tag-button')?.addEventListener('click', closeAddTagModal);
        modal?.querySelector('#modal-enhance-button')?.addEventListener('click', handleEnhanceImage);

        // 无限滚动
        window.addEventListener('scroll', handleInfiniteScroll);
    }

    // ===================================================================
    // ======================== 2. 视图切换管理 ========================
    // ===================================================================

    function switchToFaceView() {
        if (currentView === 'face') return;
        currentView = 'face';

        galleryViewContainer.style.display = 'none';
        faceViewContainer.style.display = 'block';
        gallerySection.style.display = 'block'; // 确保图库结果区可见
        
        galleryTitle.innerHTML = `人脸相册 <span id="search-results-title-face" style="display:none;">- 搜索结果</span>`;
        
        clearAllSelections();
        imageGallery.innerHTML = ''; // 清空之前的图片
        noMoreResultsDiv.style.display = 'none';

        loadFaceClusters();
    }

    function switchToGalleryView(forceRefresh = false) {
        currentView = 'gallery';

        faceViewContainer.style.display = 'none';
        galleryViewContainer.style.display = 'block';
        gallerySection.style.display = 'block';
        
        galleryTitle.innerHTML = `图片库 (<span id="total-images-count">${galleryTotalImages}</span> 张) <span id="search-results-title" style="display:none;">- 搜索结果</span>`;

        // 清理搜索状态
        clearImageSearchFile();
        clearFaceSearchFile();
        currentSearchResults = []; 
        displayedSearchResultsCount = 0;
        searchInput.value = '';
        searchStatus.textContent = '';
        mainUploadStatus.textContent = ''; 
        noMoreResultsDiv.style.display = 'none';
        
        if (forceRefresh) {
            imageGallery.innerHTML = ''; 
            galleryCurrentPage = 1;
            displayedGalleryImagesCount = 0;
            galleryTotalImages = 0; 
            clearAllSelections();
            loadGalleryImagesBatch(); 
        }
    }


    // ===================================================================
    // ==================== 3. 人脸视图核心功能 ====================
    // ===================================================================

    function loadFaceClusters() {
        loadingClusters.style.display = 'block';
        faceClusterCarousel.innerHTML = '';
        
        // TODO: 后端需要实现 /faces/clusters API
        fetch('/faces/clusters')
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    faceClusterCarousel.innerHTML = `<p>加载人脸相册失败: ${data.error}</p>`;
                    return;
                }
                renderFaceClusters(data.clusters || []);
            })
            .catch(error => {
                console.error("加载人脸聚类失败:", error);
                faceClusterCarousel.innerHTML = `<p>加载人脸相册时发生网络错误。</p>`;
            })
            .finally(() => {
                loadingClusters.style.display = 'none';
            });
    }

    function renderFaceClusters(clusters) {
        faceClusterCarousel.innerHTML = '';
        if (clusters.length === 0) {
            faceClusterCarousel.innerHTML = `<p style="color: #666;">暂无人脸相册，上传更多包含人脸的图片后将自动创建。</p>`;
            updateCarouselArrows(false);
            return;
        }

        clusters.forEach(cluster => {
            const item = document.createElement('div');
            item.className = 'face-cluster-item';
            item.dataset.clusterId = cluster.cluster_id;
            item.innerHTML = `
                <div class="face-cluster-folder">
                    <img src="${cluster.cover_thumbnail_url || 'https://placehold.co/140x110/eee/ccc?text=NoFace'}" class="face-cluster-cover-image" alt="Cluster ${cluster.cluster_id}">
                </div>
                <div class="face-cluster-info">
                    <p class="name">${cluster.name || `人物 ${cluster.cluster_id}`}</p>
                    <p class="count">${cluster.face_count} 张照片</p>
                </div>
            `;
            item.addEventListener('click', () => {
                // TODO: 后端需要实现 /faces/clusters/{id}/images API
                loadImagesForCluster(cluster.cluster_id);
            });
            faceClusterCarousel.appendChild(item);
        });

        // 延迟检查以确保DOM渲染完毕
        setTimeout(() => updateCarouselArrows(true), 100);
    }
    
    function updateCarouselArrows(hasClusters) {
        if (!hasClusters || !faceClusterCarousel) {
            carouselArrowLeft.style.display = 'none';
            carouselArrowRight.style.display = 'none';
            return;
        }
        const isScrollable = faceClusterCarousel.scrollWidth > faceClusterCarousel.clientWidth;
        carouselArrowLeft.style.display = isScrollable ? 'flex' : 'none';
        carouselArrowRight.style.display = isScrollable ? 'flex' : 'none';
    }

    function scrollCarousel(direction) {
        if (!faceClusterCarousel) return;
        const scrollAmount = faceClusterCarousel.clientWidth * 0.8; // 每次滚动80%的可见宽度
        faceClusterCarousel.scrollBy({ left: scrollAmount * direction, behavior: 'smooth' });
    }

    function loadImagesForCluster(clusterId) {
        clearAllSelections();
        imageGallery.innerHTML = '';
        loadingGallery.style.display = 'flex';
        faceSearchStatus.textContent = `正在加载人物 ${clusterId} 的照片...`;
        
        // TODO: 实现后端 API
        fetch(`/faces/clusters/${clusterId}/images`)
            .then(response => response.json())
            .then(data => {
                if(data.error) {
                    faceSearchStatus.textContent = `加载失败: ${data.error}`;
                    return;
                }
                faceSearchStatus.textContent = `显示人物 ${clusterId} 的 ${data.results.length} 张照片。`;
                displayImages(data.results, false, false);
            })
            .catch(error => {
                console.error(`加载聚类 ${clusterId} 图片失败:`, error);
                faceSearchStatus.textContent = '加载照片时发生网络错误。';
            })
            .finally(() => {
                loadingGallery.style.display = 'none';
            });
    }

    function performFaceSearch() {
        clearAllSelections();
        imageGallery.innerHTML = '';
        loadingGallery.style.display = 'flex';
        faceSearchStatus.textContent = '正在搜索...';

        if (uploadedImageForFaceSearchFile) {
            // 人脸图片搜索
            const formData = new FormData();
            formData.append('face_query_file', uploadedImageForFaceSearchFile);
            faceSearchStatus.textContent = `正在通过图片 "${uploadedImageForFaceSearchFile.name}" 搜索...`;

            fetch('/faces/search_by_face', { method: 'POST', body: formData })
                .then(response => response.json())
                .then(data => {
                    if (data.error) throw new Error(data.error);
                    faceSearchStatus.textContent = data.message;
                    currentSearchResults = data.results || [];
                    displayedSearchResultsCount = 0;
                    if(currentSearchResults.length > 0) {
                        loadMoreSearchResults();
                    } else {
                         imageGallery.innerHTML = `<p>未找到匹配的相似人脸。</p>`;
                    }
                })
                .catch(error => {
                    faceSearchStatus.textContent = `人脸搜索失败: ${error.message}`;
                })
                .finally(() => loadingGallery.style.display = 'none');
        } else {
            // 人名文本搜索
            const queryName = faceSearchInputText.value.trim();
            if (!queryName) {
                faceSearchStatus.textContent = '请输入要搜索的人名。';
                loadingGallery.style.display = 'none';
                return;
            }
            faceSearchStatus.textContent = `正在搜索人名: "${queryName}"...`;
            // TODO: 后端需要实现 /faces/search?name=... API
            fetch(`/faces/search?name=${encodeURIComponent(queryName)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) throw new Error(data.error);
                    faceSearchStatus.textContent = `为 "${queryName}" 找到 ${data.results.length} 张照片。`;
                    currentSearchResults = data.results || [];
                    displayedSearchResultsCount = 0;
                    if(currentSearchResults.length > 0) {
                        loadMoreSearchResults();
                    } else {
                        imageGallery.innerHTML = `<p>未找到与人名 "${queryName}" 相关的照片。</p>`;
                    }
                })
                .catch(error => {
                    faceSearchStatus.textContent = `人名搜索失败: ${error.message}`;
                })
                .finally(() => loadingGallery.style.display = 'none');
        }
    }


    // ===================================================================
    // ==================== 4. 图库视图核心功能 ====================
    // ===================================================================
    
    // `performSearch`, `loadMoreSearchResults` (for text/image search) remains mostly the same,
    // but now they will be called only when in 'gallery' view context for the main search.
    function performSearch() {
        if (currentView !== 'gallery') return;
        // The rest of this function is identical to your original `performSearch`
        // It's just contextually called for the main gallery search.
        // [Copy your original `performSearch` function content here]
    }
    
    function loadGalleryImagesBatch() {
        if (isLoadingMoreGalleryImages || currentView !== 'gallery') return;
        
        // 检查是否已经加载完所有图片
        if (galleryTotalImages > 0 && displayedGalleryImagesCount >= galleryTotalImages) { 
            if(noMoreResultsDiv) noMoreResultsDiv.style.display = 'block';
            return;
        }

        isLoadingMoreGalleryImages = true;
        loadingGallery.style.display = 'flex';

        fetch(`/images?page=${galleryCurrentPage}&limit=${GALLERY_IMAGES_PER_FETCH}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    imageGallery.innerHTML = `<p>加载图片库失败: ${data.error}</p>`;
                    return;
                }
                
                // 只在第一次加载时清空图库
                if (galleryCurrentPage === 1 && displayedGalleryImagesCount === 0) { 
                    imageGallery.innerHTML = ''; 
                }
                
                // 检查是否有新图片要显示
                if (data.images && data.images.length > 0) {
                    displayImages(data.images, false, true); 
                    displayedGalleryImagesCount += data.images.length;
                    galleryCurrentPage++; // 只有在成功加载图片后才增加页码
                }
                
                galleryTotalImages = data.total_count;
                if(totalImagesCountSpan) totalImagesCountSpan.textContent = galleryTotalImages;
                // Also update the gallery title which might have been changed by face view
                galleryTitle.innerHTML = `图片库 (<span id="total-images-count">${galleryTotalImages}</span> 张)`;

                // 检查是否显示"没有更多"消息
                if (displayedGalleryImagesCount >= galleryTotalImages || (data.images && data.images.length === 0)) {
                    if(noMoreResultsDiv) noMoreResultsDiv.style.display = 'block';
                } else {
                    if(noMoreResultsDiv) noMoreResultsDiv.style.display = 'none';
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

    // ===================================================================
    // ================= 5. 通用/共享功能 (上传, 展示, 弹窗等) =================
    // ===================================================================

    // Re-pasting performSearch from your original file for completeness, as it's needed for gallery view.
    function performSearch() {
        clearAllSelections();
        imageGallery.innerHTML = '';
        currentSearchResults = [];
        displayedSearchResultsCount = 0;
        loadingGallery.style.display = 'flex';
        searchButton.disabled = true;
        searchStatus.textContent = '正在搜索...';
        mainUploadStatus.textContent = '';
        const searchResultsTitle = document.getElementById('search-results-title');
        if (searchResultsTitle) searchResultsTitle.style.display = 'inline';
        if(noMoreResultsDiv) noMoreResultsDiv.style.display = 'none';

        if (uploadedImageForSearchFile) {
            const formData = new FormData();
            formData.append('image_query_file', uploadedImageForSearchFile);
            searchStatus.textContent = `正在以图搜图: ${uploadedImageForSearchFile.name}...`;

            fetch('/search_by_uploaded_image', { method: 'POST', body: formData })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    searchStatus.textContent = `图搜图失败: ${data.error}`;
                    imageGallery.innerHTML = `<p>图搜图失败: ${data.error}</p>`;
                } else {
                    currentSearchResults = data.results; 
                    const queryFileNameDisplay = data.query_filename || "上传的图片";
                    if (currentSearchResults.length > 0) {
                        searchStatus.textContent = `图搜图 "${queryFileNameDisplay}": 找到 ${currentSearchResults.length} 张相似图片。`;
                        loadMoreSearchResults();
                    } else {
                        searchStatus.textContent = `图搜图 "${queryFileNameDisplay}": 未找到相似度足够高的图片。`;
                        imageGallery.innerHTML = `<p>未找到与图片 "${queryFileNameDisplay}" 匹配且相似度足够高的图片。</p>`;
                    }
                }
            })
            .catch(error => {
                console.error('图搜图API错误:', error);
                searchStatus.textContent = '图搜图过程中发生网络错误。';
                imageGallery.innerHTML = '<p>图搜图过程中发生网络错误。</p>';
            })
            .finally(() => {
                loadingGallery.style.display = 'none';
                searchButton.disabled = false;
            });

        } else {
            const queryText = searchInput.value.trim();
            if (!queryText) {
                searchStatus.textContent = '请输入搜索描述。';
                loadingGallery.style.display = 'none';
                searchButton.disabled = false;
                return;
            }
            searchStatus.textContent = `正在文搜图: "${queryText}"...`;

            fetch('/search_images', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query_text: queryText, top_k: 200 }) 
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    searchStatus.textContent = `搜索失败: ${data.error}`;
                    imageGallery.innerHTML = `<p>搜索失败: ${data.error}</p>`;
                } else {
                    const activeSimilarityThreshold = data.search_mode_is_enhanced ? ENHANCED_SEARCH_THRESHOLD : CLIP_ONLY_SEARCH_THRESHOLD;
                    currentSearchResults = data.results.filter(img => img.similarity >= activeSimilarityThreshold);
                    
                    if (currentSearchResults.length > 0) {
                        searchStatus.textContent = `文搜图 "${queryText}": 找到 ${currentSearchResults.length} 张相关图片。`;
                        loadMoreSearchResults(); 
                    } else {
                        searchStatus.textContent = `文搜图 "${queryText}": 未找到相似度足够高的图片。`;
                        imageGallery.innerHTML = `<p>未找到与描述 "${queryText}" 匹配且相似度足够高的图片。</p>`;
                    }
                }
            })
            .catch(error => {
                console.error('文搜图API错误:', error);
                searchStatus.textContent = '文搜图过程中发生网络错误。';
                imageGallery.innerHTML = '<p>文搜图过程中发生网络错误。</p>';
            })
            .finally(() => {
                loadingGallery.style.display = 'none';
                searchButton.disabled = false;
            });
        }
    }
    
    function loadMoreSearchResults() {
        if (isLoadingMoreSearchResults || displayedSearchResultsCount >= currentSearchResults.length) return;
        isLoadingMoreSearchResults = true;
        loadingGallery.style.display = 'flex';

        const nextBatch = currentSearchResults.slice(displayedSearchResultsCount, displayedSearchResultsCount + searchResultsBatchSize);

        if (nextBatch.length > 0) {
            displayImages(nextBatch, true, true); 
            displayedSearchResultsCount += nextBatch.length;
            noMoreResultsDiv.style.display = 'none';
        }
        
        if (displayedSearchResultsCount >= currentSearchResults.length) {
            noMoreResultsDiv.style.display = 'block';
        }

        isLoadingMoreSearchResults = false;
        loadingGallery.style.display = 'none';
    }

    function handleUnifiedUpload(files) {
        // [Copy your original `handleUnifiedUpload` function here, but with one change]
        // In the .then() block, call switchToGalleryView(true) instead of just reloading.
        // This ensures if the user was in face view, they are switched back to the main gallery
        // to see their newly uploaded photos.
        if (!files || files.length === 0) return;
        
        navUploadAbortController?.abort();
        navUploadAbortController = new AbortController();

        const formData = new FormData();
        for (const file of files) {
            if (file.type?.startsWith('image/')) {
                formData.append('files', file);
            }
        }
        
        const fileCount = formData.getAll('files').length;
        if (fileCount === 0) {
            mainUploadStatus.textContent = '选择的文件中没有有效的图片文件。';
            return;
        }

        mainUploadStatus.textContent = `正在上传 ${fileCount} 张图片...`;
        navUploadButton.disabled = true;

        fetch('/upload_images', {
            method: 'POST',
            body: formData,
            signal: navUploadAbortController.signal
        })
        .then(response => response.json())
        .then(data => {
            if (navUploadAbortController.signal.aborted) return;
            if (data.error) {
                mainUploadStatus.textContent = `上传失败: ${data.error}`;
            } else {
                mainUploadStatus.textContent = data.message || `成功处理 ${fileCount} 张图片。`;
                // ** THE CHANGE IS HERE **
                switchToGalleryView(true); // Force refresh of gallery view
            }
        })
        .catch(error => {
            if (error.name !== 'AbortError') {
                mainUploadStatus.textContent = '上传过程中发生网络错误。';
            }
        })
        .finally(() => {
            navUploadButton.disabled = false;
            navUploadAbortController = null;
            setTimeout(() => { mainUploadStatus.textContent = ''; }, 7000);
        });
    }

    function displayImages(images, isSearchResult = false, append = false) {
        // This function is almost identical to your original one.
        // [Copy your original `displayImages` function here]
        if (!append) imageGallery.innerHTML = '';
        
        images.forEach(img => {
            const item = document.createElement('div');
            item.className = 'gallery-item';
            item.dataset.imageId = img.id; 
            item.dataset.originalUrl = img.original_url;
            item.dataset.filename = img.filename;
            if (isSearchResult && img.similarity !== undefined) {
                item.dataset.similarity = img.similarity.toFixed(4);
            }

            item.innerHTML = `
                <img src="${img.thumbnail_url || 'https://placehold.co/160x130/eee/ccc?text=NoThumb'}" alt="${img.filename}" onerror="this.onerror=null;this.src='https://placehold.co/160x130/eee/ccc?text=Error';">
                <p>${img.filename.length > 20 ? img.filename.substring(0, 17) + '...' : img.filename}</p>
                ${isSearchResult && img.similarity !== undefined ? `<p class="similarity">相似度: ${img.similarity.toFixed(4)}</p>` : ''}
                ${img.is_enhanced ? `<span class="enhanced-badge">已增强</span>` : ''}
            `;

            item.addEventListener('click', (e) => toggleImageSelection(img.id, item));
            item.addEventListener('dblclick', () => openImageDetailModal(img.id, img.original_url, img.filename, isSearchResult, item.dataset.similarity));

            if (selectedImageIds.has(String(img.id))) {
                item.classList.add('selected');
            }

            imageGallery.appendChild(item);
        });
    }

    function handleInfiniteScroll() {
        const nearBottom = (window.innerHeight + window.scrollY) >= document.body.offsetHeight - 400;
        if (!nearBottom) return;

        if (currentView === 'gallery') {
            const isSearching = currentSearchResults.length > 0;
            if (isSearching && !isLoadingMoreSearchResults) {
                loadMoreSearchResults();
            } else if (!isSearching && !isLoadingMoreGalleryImages) {
                loadGalleryImagesBatch();
            }
        } else if (currentView === 'face') {
            // If face search results are also paginated and use the same mechanism
            if (currentSearchResults.length > 0 && !isLoadingMoreSearchResults) {
                loadMoreSearchResults();
            }
        }
    }

    function handleImageSearchFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;
        uploadedImageForSearchFile = file;
        imageSearchFilenameHero.textContent = file.name.length > 20 ? file.name.substring(0, 17) + '...' : file.name;
        imageSearchPreviewHero.style.display = 'flex';
        searchInput.disabled = true;
        searchInput.placeholder = '已选择图片，将进行图搜图';
        imageSearchUploadButtonHero.style.display = 'none';
    }

    function clearImageSearchFile() {
        uploadedImageForSearchFile = null;
        imageSearchInputHero.value = null;
        imageSearchPreviewHero.style.display = 'none';
        searchInput.disabled = false;
        searchInput.placeholder = '输入中文描述搜索图片...';
        imageSearchUploadButtonHero.style.display = 'inline-flex';
    }

    function handleFaceSearchFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;
        uploadedImageForFaceSearchFile = file;
        faceSearchFilename.textContent = file.name.length > 20 ? file.name.substring(0, 17) + '...' : file.name;
        faceSearchPreview.style.display = 'flex';
        faceSearchInputText.disabled = true;
        faceSearchInputText.placeholder = '已选择图片，将进行人脸搜索';
        faceSearchUploadButton.style.display = 'none';
    }

    function clearFaceSearchFile() {
        uploadedImageForFaceSearchFile = null;
        faceSearchInputImage.value = null;
        faceSearchPreview.style.display = 'none';
        faceSearchInputText.disabled = false;
        faceSearchInputText.placeholder = '输入人名搜索或上传左侧图片进行搜索...';
        faceSearchUploadButton.style.display = 'inline-flex';
    }

    // All other helper functions (toggleImageSelection, updateSelectionControls, modals, etc.)
    // are assumed to be copied from your original file as they don't need significant changes.
    // For brevity, I am not re-pasting them here, but they MUST be in the final script.
    // [ENSURE all other functions from your original script.js are included here]
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
        selectedCountSpan.textContent = count;
        const display = count > 0 ? 'inline-flex' : 'none';
        batchDeleteButton.style.display = display;
        batchTagButton.style.display = display;
        clearSelectionButton.style.display = display;
        selectionInfoSpan.style.display = count > 0 ? 'inline' : 'none';
    }
    function clearAllSelections() {
        selectedImageIds.forEach(id => {
            const item = imageGallery.querySelector(`.gallery-item[data-image-id='${id}']`);
            if (item) item.classList.remove('selected');
        });
        selectedImageIds.clear();
        updateSelectionControls();
    }
    function openImageDetailModal(imageId, originalUrl, filename, isSearchResult, similarityScore) {
        currentModalImageId = imageId;
        const modalImageElement = document.getElementById('modal-image-element');
        modalImageElement.src = originalUrl || 'https://placehold.co/600x400?text=No+Image';
        document.getElementById('modal-filename').textContent = filename || '未知文件';
        const simContainer = document.getElementById('modal-similarity-container');
        if (isSearchResult && similarityScore) {
            document.getElementById('modal-similarity').textContent = similarityScore;
            simContainer.style.display = 'block';
        } else {
            simContainer.style.display = 'none';
        }
        modal.style.display = 'flex';
        fetch(`/image_details/${imageId}`)
            .then(res => res.json())
            .then(data => {
                document.getElementById('modal-qwen-description').textContent = data.qwen_description || '无';
                document.getElementById('modal-qwen-keywords').textContent = data.qwen_keywords?.join(', ') || '无';
                document.getElementById('modal-user-tags').textContent = data.user_tags?.join(', ') || '无';
                const isEnhanced = data.is_enhanced;
                document.getElementById('modal-is-enhanced').textContent = isEnhanced ? '是' : '否';
                document.getElementById('modal-enhance-button').style.display = isEnhanced ? 'none' : 'inline-block';
            });
    }
    function closeImageDetailModal() { modal.style.display = 'none'; }
    function openConfirmDeleteModal() {
        if (selectedImageIds.size === 0) return;
        document.getElementById('delete-count').textContent = selectedImageIds.size;
        confirmDeleteModal.style.display = 'flex';
    }
    function closeConfirmDeleteModal() { confirmDeleteModal.style.display = 'none'; }
    function handleDeleteSelectedImages() {
        const idsToDelete = Array.from(selectedImageIds);
        fetch('/delete_images_batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_ids: idsToDelete })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                switchToGalleryView(true); // Refresh after delete
            } else {
                alert(`删除失败: ${data.error}`);
            }
        })
        .finally(() => closeConfirmDeleteModal());
    }
    function openAddTagModal() {
        if (selectedImageIds.size === 0) return;
        document.getElementById('tag-target-count').textContent = selectedImageIds.size;
        addTagModal.style.display = 'flex';
    }
    function closeAddTagModal() { addTagModal.style.display = 'none'; }
    function handleAddTagsToSelectedImages() {
        const idsToTag = Array.from(selectedImageIds);
        const tagsString = document.getElementById('user-tags-input').value.trim();
        const tagsArray = tagsString.split(',').map(t => t.trim()).filter(Boolean);
        if (tagsArray.length === 0) return;
        fetch('/add_user_tags_batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_ids: idsToTag, user_tags: tagsArray })
        })
        .then(res => res.json())
        .then(data => {
            if (data.success) alert('标签添加成功');
        })
        .finally(() => closeAddTagModal());
    }
    function handleEnhanceImage() {
        const enhanceButton = document.getElementById('modal-enhance-button');
        enhanceButton.disabled = true;
        fetch(`/enhance_image/${currentModalImageId}`, { method: 'POST' })
        .then(res => res.json())
        .then(data => {
            if (!data.error) {
                document.getElementById('modal-is-enhanced').textContent = '是';
                enhanceButton.style.display = 'none';
            }
        })
        .finally(() => enhanceButton.disabled = false);
    }


    // ---- App Entry Point ----
    initializeEventListeners();
    switchToGalleryView(true); // Start with a fresh gallery view
    updateSelectionControls();
});