// static/uiUpdater.js

// [cacheDomElements, finalizeStreamingMessage, setupDownloadButton, displayChipDiagram 等函数与您上一版本相同，此处为确保完整性再次提供]
let chatMessagesElem, aiLoadingIndicatorElem, aiErrorBoxElem,
    jsonErrorBoxManualElem, loadingIndicatorManualElem,
    diagramResultContainerTemplateElem, apiKeyMessageElem,
    featuresSectionElem, advancedToolsModalElem, apiKeySectionModalElem,
    jsonEditorSectionModalElem,
    aiModelSelectElem, modelLoadStatusElem, currentSetModelDisplayElem,
    sidebarOverlayElem, mainAppContentElem,
    userInputElem, sendButtonElem;


export function cacheDomElements(elements) {
    chatMessagesElem = elements.chatMessages;
    aiLoadingIndicatorElem = elements.aiLoadingIndicator;
    aiErrorBoxElem = elements.aiErrorBox;
    jsonErrorBoxManualElem = elements.jsonErrorBoxManual;
    loadingIndicatorManualElem = elements.loadingIndicatorManual;
    diagramResultContainerTemplateElem = elements.diagramResultContainerTemplate;
    apiKeyMessageElem = elements.apiKeyMessage;
    featuresSectionElem = elements.featuresSection;
    advancedToolsModalElem = elements.advancedToolsModal;
    apiKeySectionModalElem = elements.apiKeySectionModal;
    jsonEditorSectionModalElem = elements.jsonEditorSectionModal;
    aiModelSelectElem = elements.aiModelSelect;
    modelLoadStatusElem = elements.modelLoadStatus;
    currentSetModelDisplayElem = elements.currentSetModelDisplay;
    sidebarOverlayElem = elements.sidebarOverlay;
    mainAppContentElem = elements.mainAppContent;
    userInputElem = elements.userInput;
    sendButtonElem = elements.sendButton;
}

// ============================================
// ===           核心修改：appendMessage     ===
// ============================================
export function appendMessage(text, sender, isStreaming = false, targetTextDiv = null) {
    if (!chatMessagesElem) return null;

    // --- 流式更新逻辑 (保持不变) ---
    if (sender === 'bot' && isStreaming && targetTextDiv) {
        let currentText = targetTextDiv.innerHTML.replace(/<span class="typing-cursor">▍<\/span>$/, '');
        targetTextDiv.innerHTML = currentText + text.replace(/\n/g, "<br>") + '<span class="typing-cursor">▍</span>';
        // 滚动到包含目标div的消息的底部
        const parentMessage = targetTextDiv.closest('.message');
        if (parentMessage) parentMessage.scrollIntoView({ behavior: "smooth", block: "end" });
        else chatMessagesElem.scrollTop = chatMessagesElem.scrollHeight;
        return targetTextDiv;
    }

    // --- 创建新消息元素的逻辑 ---
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', `${sender}-message`);

    // --- 用户消息的特殊处理：添加标记 ---
    if (sender === 'user') {
        // 移除旧的标记
        const latestPrompt = chatMessagesElem.querySelector('.latest-user-prompt');
        if (latestPrompt) {
            latestPrompt.classList.remove('latest-user-prompt');
        }
        // 添加新标记
        messageDiv.classList.add('latest-user-prompt');
    }

    const avatarDiv = document.createElement('div');
    avatarDiv.classList.add('avatar', `${sender}-avatar`);
    if (sender === 'user') {
        const iconSpan = document.createElement('span');
        iconSpan.classList.add('material-icons');
        iconSpan.textContent = 'person';
        avatarDiv.appendChild(iconSpan);
    } // Bot 和 System 的头像由CSS设置

    const textDivToUse = document.createElement('div');
    textDivToUse.classList.add('text');

    if (isStreaming && sender === 'bot') {
        textDivToUse.innerHTML = text.replace(/\n/g, "<br>") + '<span class="typing-cursor">▍</span>';
    } else {
        textDivToUse.innerHTML = text.replace(/\n/g, "<br>");
    }

    messageDiv.appendChild(avatarDiv);
    messageDiv.appendChild(textDivToUse);

    // --- 决定将新消息插入到何处 ---
    const latestUserPrompt = chatMessagesElem.querySelector('.latest-user-prompt');
    
    // 如果是用户消息，或者没有找到最新的用户提示，则正常附加到末尾
    if (sender === 'user' || !latestUserPrompt) {
        chatMessagesElem.appendChild(messageDiv);
    } else {
        // 如果是AI或系统的消息，插入到最新用户提示的后面
        // nextSibling 会找到下一个兄弟节点，然后在其之前插入
        if (latestUserPrompt.nextSibling) {
            chatMessagesElem.insertBefore(messageDiv, latestUserPrompt.nextSibling);
        } else {
            // 如果用户提示是最后一个元素，则直接附加
            chatMessagesElem.appendChild(messageDiv);
        }
    }
    
    // 平滑滚动到新消息
    messageDiv.scrollIntoView({ behavior: "smooth", block: "end", inline: "nearest" });

    return textDivToUse;
}


// [ 其他 uiUpdater.js 函数 (finalizeStreamingMessage, setupDownloadButton, displayChipDiagram 等) 保持不变 ]
// [ 为了简洁，此处省略这些函数的重复代码，请确保您拥有它们在我之前回复中的完整版本 ]
export function finalizeStreamingMessage(targetTextDiv) { if (targetTextDiv) { targetTextDiv.innerHTML = targetTextDiv.innerHTML.replace(/<span class="typing-cursor">▍<\/span>$/, ''); } }
export function setupDownloadButton(buttonId, svgId, svgBgColor) { const downloadButton = document.getElementById(buttonId); if (!downloadButton) { console.warn(`下载按钮 ${buttonId} 未找到`); return; } const newButton = downloadButton.cloneNode(true); if (downloadButton.parentNode) { downloadButton.parentNode.replaceChild(newButton, downloadButton); } newButton.addEventListener('click', function() { const currentSvgElement = document.getElementById(svgId); if (!currentSvgElement) { alert("错误: SVG元素已消失，无法下载。"); return; } const svgXml = new XMLSerializer().serializeToString(currentSvgElement); const img = new Image(); const svgData = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgXml); img.onload = function() { const canvas = document.createElement('canvas'); const viewBoxValues = currentSvgElement.getAttribute('viewBox')?.split(' ') || []; let originalWidth = currentSvgElement.width?.baseVal?.value || 600; let originalHeight = currentSvgElement.height?.baseVal?.value || 400; if (viewBoxValues.length === 4) { originalWidth = parseFloat(viewBoxValues[2]); originalHeight = parseFloat(viewBoxValues[3]); } const scaleFactor = 2.5; canvas.width = originalWidth * scaleFactor; canvas.height = originalHeight * scaleFactor; const ctx = canvas.getContext('2d'); ctx.fillStyle = svgBgColor || 'white'; ctx.fillRect(0, 0, canvas.width, canvas.height); ctx.drawImage(img, 0, 0, canvas.width, canvas.height); const jpgDataUrl = canvas.toDataURL('image/jpeg', 0.95); const downloadLink = document.createElement('a'); downloadLink.href = jpgDataUrl; downloadLink.download = 'chip_diagram.jpg'; document.body.appendChild(downloadLink); downloadLink.click(); document.body.removeChild(downloadLink); }; img.onerror = function() { alert("错误: 无法加载SVG图像进行转换。"); }; img.src = svgData; }); }
export function displayChipDiagram(htmlFragment, isAiGenerated) {
    if (!diagramResultContainerTemplateElem || !chatMessagesElem) { console.error("图表模板或聊天消息区域未正确缓存!"); return; }
    const existingDiagram = chatMessagesElem.querySelector('.diagram-output-file:not(#diagramResultContainerTemplate)');
    if (existingDiagram) { existingDiagram.remove(); }
    const newDiagramDisplay = diagramResultContainerTemplateElem.cloneNode(true);
    newDiagramDisplay.id = ''; newDiagramDisplay.style.display = 'block';
    const fileContentDiv = newDiagramDisplay.querySelector('.file-content');
    if (fileContentDiv) {
        fileContentDiv.innerHTML = htmlFragment;
    } else {
        newDiagramDisplay.innerHTML += htmlFragment; 
    }
    
    // **重要修改**: 将图表也插入到最新用户消息之后
    const latestUserPrompt = chatMessagesElem.querySelector('.latest-user-prompt');
    const insertBeforeTarget = aiLoadingIndicatorElem?.style.display !== 'none' ? aiLoadingIndicatorElem : (aiErrorBoxElem?.style.display !== 'none' ? aiErrorBoxElem : null);
    
    if (insertBeforeTarget && insertBeforeTarget.parentNode === chatMessagesElem) {
        chatMessagesElem.insertBefore(newDiagramDisplay, insertBeforeTarget);
    } else if (latestUserPrompt && latestUserPrompt.nextSibling) {
        chatMessagesElem.insertBefore(newDiagramDisplay, latestUserPrompt.nextSibling);
    } else if (latestUserPrompt) {
        chatMessagesElem.appendChild(newDiagramDisplay);
    } else {
       chatMessagesElem.appendChild(newDiagramDisplay);
    }
    newDiagramDisplay.scrollIntoView({ behavior: "smooth", block: "end" });

    setTimeout(() => {
        const downloadBtnInFragment = newDiagramDisplay.querySelector('#downloadGeneratedBtn');
        const svgInFragment = newDiagramDisplay.querySelector('#chipDiagramSvg_inner');
        if (downloadBtnInFragment && svgInFragment) {
            const instanceTime = Date.now();
            const uniqueDownloadBtnId = `downloadBtn_instance_${instanceTime}`;
            const uniqueSvgId = `svg_instance_${instanceTime}`;
            downloadBtnInFragment.id = uniqueDownloadBtnId; svgInFragment.id = uniqueSvgId;
            setupDownloadButton(uniqueDownloadBtnId, uniqueSvgId, 'white');
        } else { console.error("未能找到新图表中的下载按钮或SVG元素。"); }
    }, 100);
}
export function showAiLoading(show) { if (aiLoadingIndicatorElem) { aiLoadingIndicatorElem.style.display = show ? 'flex' : 'none'; if (show && chatMessagesElem) { const latestUserPrompt = chatMessagesElem.querySelector('.latest-user-prompt'); if (latestUserPrompt && latestUserPrompt.nextSibling) { chatMessagesElem.insertBefore(aiLoadingIndicatorElem, latestUserPrompt.nextSibling); } else if (latestUserPrompt) { chatMessagesElem.appendChild(aiLoadingIndicatorElem); } else { chatMessagesElem.appendChild(aiLoadingIndicatorElem); } aiLoadingIndicatorElem.scrollIntoView({ behavior: "smooth", block: "end" }); } } }
export function showAiError(message) { if (aiErrorBoxElem) { const textElement = aiErrorBoxElem.querySelector('.text') || aiErrorBoxElem; textElement.textContent = message; aiErrorBoxElem.style.display = 'flex'; if (chatMessagesElem) { const latestUserPrompt = chatMessagesElem.querySelector('.latest-user-prompt'); if (latestUserPrompt && latestUserPrompt.nextSibling) { chatMessagesElem.insertBefore(aiErrorBoxElem, latestUserPrompt.nextSibling); } else if (latestUserPrompt) { chatMessagesElem.appendChild(aiErrorBoxElem); } else { chatMessagesElem.appendChild(aiErrorBoxElem); } aiErrorBoxElem.scrollIntoView({ behavior: "smooth", block: "end" }); } } }
export function hideAiError() { if(aiErrorBoxElem) aiErrorBoxElem.style.display = 'none'; }
export function showManualLoading(show) { if (loadingIndicatorManualElem) loadingIndicatorManualElem.style.display = show ? 'block' : 'none'; }
export function showManualJsonError(message) { if (jsonErrorBoxManualElem) { jsonErrorBoxManualElem.textContent = message; jsonErrorBoxManualElem.style.display = 'block'; } }
export function hideManualJsonError() { if (jsonErrorBoxManualElem) jsonErrorBoxManualElem.style.display = 'none'; }
export function updateApiKeyStatus(message, type) { if (apiKeyMessageElem) { apiKeyMessageElem.textContent = message; apiKeyMessageElem.className = 'api-key-message'; if (type) apiKeyMessageElem.classList.add(type); apiKeyMessageElem.style.display = message ? 'block' : 'none'; } }
export function toggleAdvancedToolModal(show, toolToShow) { if (!advancedToolsModalElem || !apiKeySectionModalElem || !jsonEditorSectionModalElem) { console.error("模态框组件未缓存。"); return; } if (show) { apiKeySectionModalElem.style.display = toolToShow === 'api' ? 'block' : 'none'; jsonEditorSectionModalElem.style.display = toolToShow === 'json' ? 'block' : 'none'; advancedToolsModalElem.style.display = 'flex'; } else { advancedToolsModalElem.style.display = 'none'; } }
export function toggleFeaturesSection(show) { if (!featuresSectionElem || !chatMessagesElem) return; featuresSectionElem.style.display = show ? 'block' : 'none'; if (show) { const existingDiagram = chatMessagesElem.querySelector('.diagram-output-file:not(#diagramResultContainerTemplate)'); if(existingDiagram) existingDiagram.remove(); featuresSectionElem.scrollIntoView({ behavior: 'smooth' }); } }
export function applySidebarState(sidebarElement, isSmallScreen) { if (!sidebarElement) return; const wantsCollapsed = localStorage.getItem('sidebarCollapsed') === 'true'; if (isSmallScreen) { sidebarElement.classList.remove('collapsed', 'push-content'); } else { sidebarElement.classList.remove('open'); sidebarElement.classList.toggle('collapsed', wantsCollapsed); if (mainAppContentElem) { mainAppContentElem.classList.toggle('push-content', !wantsCollapsed); } } }
export function toggleSidebar(sidebarElement) { if (!sidebarElement) return; const isSmallScreen = window.innerWidth <= 1024; if (isSmallScreen) { sidebarElement.classList.toggle('open'); if (sidebarOverlayElem) sidebarOverlayElem.style.display = sidebarElement.classList.contains('open') ? 'block' : 'none'; } else { const isCollapsed = sidebarElement.classList.contains('collapsed'); sidebarElement.classList.toggle('collapsed', !isCollapsed); if (mainAppContentElem) { mainAppContentElem.classList.toggle('push-content', isCollapsed); } localStorage.setItem('sidebarCollapsed', !isCollapsed); } }
export function populateModelDropdown(models = [], defaultModelIdFromService = null) { if (!aiModelSelectElem) { console.warn("AI模型选择下拉框元素未找到。"); return; } aiModelSelectElem.innerHTML = '<option value="">— 请选择一个AI模型 —</option>'; const storedModel = localStorage.getItem('selectedAiModel'); let modelToSelect = defaultModelIdFromService; if (storedModel && models.includes(storedModel)) { modelToSelect = storedModel; } else if (defaultModelIdFromService && models.includes(defaultModelIdFromService)) { modelToSelect = defaultModelIdFromService; } else if (models.length > 0) { const defaultPyModel = "deepseek-ai/DeepSeek-V2-Chat"; if (models.includes(defaultPyModel)) modelToSelect = defaultPyModel; else modelToSelect = models[0]; } models.forEach(modelId => { const option = document.createElement('option'); option.value = modelId; option.textContent = modelId; if (modelId === modelToSelect) option.selected = true; aiModelSelectElem.appendChild(option); }); if (modelToSelect) { updateCurrentSetModelDisplay(modelToSelect); } else { updateCurrentSetModelDisplay("未选择"); } }
export function setModelLoadStatus(message, isError = false) { if (modelLoadStatusElem) { modelLoadStatusElem.textContent = message; modelLoadStatusElem.style.color = isError ? 'var(--gemini-error-text)' : 'var(--gemini-text-tertiary)'; modelLoadStatusElem.style.display = message ? 'block' : 'none'; } }
export function updateCurrentSetModelDisplay(modelName) { if (currentSetModelDisplayElem) { currentSetModelDisplayElem.textContent = modelName || "默认"; } }
export function setInputDisabledState(disabled) { if (userInputElem) { userInputElem.disabled = disabled; userInputElem.placeholder = disabled ? "AI 正在回复中..." : "在此输入您的芯片逻辑描述..."; } if (sendButtonElem) { sendButtonElem.disabled = disabled; sendButtonElem.style.cursor = disabled ? 'not-allowed' : 'pointer'; sendButtonElem.style.opacity = disabled ? '0.5' : '1'; } }