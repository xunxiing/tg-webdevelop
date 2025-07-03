// static/eventHandlers.js
import {
    appendMessage, finalizeStreamingMessage, updateApiKeyStatus, showAiError, hideAiError,
    toggleAdvancedToolModal, toggleFeaturesSection, toggleSidebar, cacheDomElements,
    populateModelDropdown, setModelLoadStatus, updateCurrentSetModelDisplay, applySidebarState,
    setInputDisabledState // 导入新函数
} from './uiUpdater.js';
import {
    triggerDiagramGenerationAPI, requestAiGenerationStream, saveApiKeyAPI,
    fetchAiModelsAPI
} from './apiService.js';

// DOM 元素声明
let userInput, sendButton, apiKeyInput, saveApiKeyButton, chipJsonTextarea,
    generateDiagramButton, clearJsonButton, appSidebar, mainMenuButton, sidebarMenuButton, newChatBtn,
    advancedToolsModal, apiKeySettingsLink, jsonEditorLink, featuresLink, modalCloseButton,
    aiModelSelect, refreshModelsBtn, sidebarOverlay;

// 状态变量
let aiResponseMessageDiv = null; // 用于追踪当前正在流式输出的AI回复消息元素

async function loadAndDisplayModels() {
    // ... (此函数与上一版本相同) ...
    if (!window.current_user_is_authenticated_from_server) { setModelLoadStatus("请先登录以加载和选择模型。", true); if(aiModelSelect) aiModelSelect.innerHTML = '<option value="">请先登录</option>'; updateCurrentSetModelDisplay("未登录"); return; }
    setModelLoadStatus("正在加载模型列表...", false);
    try {
        const models = await fetchAiModelsAPI();
        const defaultModelFromService = models.length > 0 ? models[0] : null;
        populateModelDropdown(models, defaultModelFromService);
        setModelLoadStatus(models.length > 0 ? "模型列表已加载。" : "未能从API获取模型，显示预设列表。", false);
        const storedModel = localStorage.getItem('selectedAiModel');
        if (storedModel && models.includes(storedModel)) {
             if(aiModelSelect) aiModelSelect.value = storedModel;
             updateCurrentSetModelDisplay(storedModel);
        } else if (aiModelSelect && aiModelSelect.value) {
            updateCurrentSetModelDisplay(aiModelSelect.value);
            localStorage.setItem('selectedAiModel', aiModelSelect.value);
        } else { updateCurrentSetModelDisplay("默认"); }
    } catch (error) {
        console.error("加载或填充模型列表失败:", error);
        setModelLoadStatus(`加载模型列表失败: ${error.message}`, true);
        updateCurrentSetModelDisplay("加载失败");
    }
}

// ============================================
// ===           核心修改部分             ===
// ============================================
function handleUserInput() {
    if (!userInput || userInput.disabled) return;
    const messageText = userInput.value.trim();
    if (!messageText) return;

    appendMessage(messageText, 'user');
    userInput.value = '';
    userInput.style.height = 'auto';
    userInput.focus();
    hideAiError();

    const activeModel = (aiModelSelect ? aiModelSelect.value : null) || localStorage.getItem('selectedAiModel');
    
    if (messageText.startsWith('{') && messageText.endsWith('}') && messageText.includes('"nodes":')) {
        appendMessage("检测到您输入了JSON，将尝试直接生成图表。", 'system');
        if (chipJsonTextarea) chipJsonTextarea.value = messageText;
        triggerDiagramGenerationAPI(messageText, false);
    } else {
        // 重置AI回复占位符
        aiResponseMessageDiv = null;

        requestAiGenerationStream(
            messageText,
            apiKeyInput ? apiKeyInput.value.trim() : '',
            activeModel,
            (chunkData) => { // onChunkReceived
                // 只处理最终内容 (思维链已回滚)
                if (chunkData.type === "content") {
                    // 如果是第一个内容块，创建新的AI消息
                    if (!aiResponseMessageDiv) {
                        aiResponseMessageDiv = appendMessage("", 'bot', true);
                    }
                    // 将内容块追加到这个消息中
                    if (aiResponseMessageDiv) {
                        appendMessage(chunkData.data, 'bot', true, aiResponseMessageDiv);
                    }
                }
            },
            (accumulatedContentResponse) => { // onStreamEnd
                if (aiResponseMessageDiv) {
                    finalizeStreamingMessage(aiResponseMessageDiv);
                }
                if (accumulatedContentResponse && accumulatedContentResponse.trim() !== "") {
                    tryToParseAndTriggerDiagram(accumulatedContentResponse);
                } else {
                    console.log("AI未返回有效的最终内容以生成图表。");
                    // 如果AI的最终回复为空，可能需要给用户一个提示
                    if (!aiResponseMessageDiv) { // 确保即使回复为空，也有个气泡
                        appendMessage("...", 'bot');
                    }
                }
                aiResponseMessageDiv = null;
            },
            (errorMessage) => { // onError
                showAiError(errorMessage);
                // 确保即使在错误发生时，如果已经创建了回复气泡，也要处理它
                if (aiResponseMessageDiv) {
                    finalizeStreamingMessage(aiResponseMessageDiv);
                    const textDiv = aiResponseMessageDiv.querySelector('.text');
                    if(textDiv) {
                        textDiv.innerHTML = `<strong style="color: var(--gemini-error-text);">抱歉，处理时发生错误。</strong>`;
                    }
                }
                aiResponseMessageDiv = null;
            }
        );
    }
}

// ... (tryToParseAndTriggerDiagram 与上一版本相同) ...
function tryToParseAndTriggerDiagram(jsonString) {
    let parsedJson; let finalJsonString = jsonString.trim(); hideAiError();
    if (finalJsonString.startsWith("```json")) { finalJsonString = finalJsonString.substring(7).trim(); }
    if (finalJsonString.endsWith("```")) { finalJsonString = finalJsonString.slice(0, -3).trim(); }
    const firstBrace = finalJsonString.indexOf('{'); const lastBrace = finalJsonString.lastIndexOf('}');
    if (firstBrace !== -1 && lastBrace !== -1 && firstBrace < lastBrace) {
        finalJsonString = finalJsonString.substring(firstBrace, lastBrace + 1);
    } else {
        if (jsonString && jsonString.trim() !== "") { showAiError("AI未能生成有效的JSON结构。"); appendMessage("AI未能生成有效的JSON结构。", 'bot'); } 
        else { console.log("tryToParseAndTriggerDiagram: 接收到空的jsonString，不执行图表生成。"); }
        return false;
    }
    try {
        parsedJson = JSON.parse(finalJsonString);
        if (chipJsonTextarea) chipJsonTextarea.value = JSON.stringify(parsedJson, null, 2);
        appendMessage("AI已成功生成JSON。现在将自动为您生成图表...", 'system');
        triggerDiagramGenerationAPI(JSON.stringify(parsedJson, null, 2), true);
        return true;
    } catch (e) {
        showAiError("AI返回的内容无法解析为JSON: " + e.message);
        appendMessage("AI返回的内容无法解析为JSON: " + e.message, 'bot');
        if (chipJsonTextarea) chipJsonTextarea.value = jsonString;
        return false;
    }
}


export function initializeEventHandlers() {
    // ... (DOM元素获取与上一版本相同) ...
    userInput = document.getElementById('userInput');
    sendButton = document.getElementById('sendButton');
    apiKeyInput = document.getElementById('apiKeyInput');
    saveApiKeyButton = document.getElementById('saveApiKeyButton');
    chipJsonTextarea = document.getElementById('chipJsonTextarea');
    generateDiagramButton = document.getElementById('generateDiagramButton');
    clearJsonButton = document.getElementById('clearJsonButton');
    appSidebar = document.getElementById('appSidebar');
    mainMenuButton = document.getElementById('mainMenuButton');
    sidebarMenuButton = document.getElementById('sidebarMenuButton');
    newChatBtn = document.getElementById('newChatBtn');
    advancedToolsModal = document.getElementById('advancedToolsModal');
    apiKeySettingsLink = document.getElementById('apiSettingsLink');
    jsonEditorLink = document.getElementById('jsonEditorLink');
    featuresLink = document.getElementById('featuresLink');
    modalCloseButton = advancedToolsModal?.querySelector('.modal-close-button');
    aiModelSelect = document.getElementById('aiModelSelect');
    refreshModelsBtn = document.getElementById('refreshModelsBtn');
    sidebarOverlay = document.getElementById('sidebarOverlay');
    const mainAppContent = document.getElementById('mainAppContent');

    const uiElementsToCache = {
        chatMessages: document.getElementById('chatMessages'),
        aiLoadingIndicator: document.getElementById('aiLoadingIndicator'),
        aiErrorBox: document.getElementById('aiErrorBox'),
        jsonErrorBoxManual: document.getElementById('jsonErrorBoxManual'),
        loadingIndicatorManual: document.getElementById('loadingIndicatorManual'),
        diagramResultContainerTemplate: document.getElementById('diagramResultContainerTemplate'),
        apiKeyMessage: document.getElementById('apiKeyMessage'),
        featuresSection: document.getElementById('featuresSection'),
        advancedToolsModal: advancedToolsModal,
        apiKeySectionModal: document.getElementById('apiKeySectionModal'),
        jsonEditorSectionModal: document.getElementById('jsonEditorSectionModal'),
        aiModelSelect: aiModelSelect,
        modelLoadStatus: document.getElementById('modelLoadStatus'),
        currentSetModelDisplay: document.getElementById('currentSetModelDisplay'),
        sidebarOverlay: sidebarOverlay,
        mainAppContent: mainAppContent,
        userInput: userInput,
        sendButton: sendButton
    };
    cacheDomElements(uiElementsToCache);

    // ... (其他事件监听器与上一版本相同) ...
    if (sendButton && userInput) { sendButton.addEventListener('click', handleUserInput); userInput.addEventListener('keypress', function(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleUserInput(); } }); userInput.addEventListener('input', () => { userInput.style.height = 'auto'; userInput.style.height = (userInput.scrollHeight) + 'px'; sendButton.classList.toggle('has-text', userInput.value.trim().length > 0); }); }
    if (saveApiKeyButton && apiKeyInput) { saveApiKeyButton.addEventListener('click', async () => { const apiKey = apiKeyInput.value.trim(); if (!apiKey) { updateApiKeyStatus('API Key不能为空！', 'error'); return; } updateApiKeyStatus('正在保存...', 'working'); try { const data = await saveApiKeyAPI(apiKey); if (data.success) { updateApiKeyStatus(data.message || 'API Key已保存！', 'success'); if (window.current_user_is_authenticated_from_server) loadAndDisplayModels(); } else { updateApiKeyStatus('保存失败: ' + (data.error || '未知错误'), 'error'); } } catch (error) { updateApiKeyStatus('保存请求出错: ' + error.message, 'error'); } }); }
    if (clearJsonButton && chipJsonTextarea) { clearJsonButton.addEventListener('click', () => { chipJsonTextarea.value = ''; chipJsonTextarea.focus(); appendMessage("JSON编辑器已清空。", 'system'); }); }
    if (generateDiagramButton && chipJsonTextarea) { generateDiagramButton.addEventListener('click', function() { triggerDiagramGenerationAPI(chipJsonTextarea.value, false); }); }
    const handleMenuToggle = () => toggleSidebar(appSidebar);
    if (mainMenuButton) mainMenuButton.addEventListener('click', handleMenuToggle);
    if (sidebarMenuButton) sidebarMenuButton.addEventListener('click', handleMenuToggle);
    if (sidebarOverlay) sidebarOverlay.addEventListener('click', () => toggleSidebar(appSidebar, false));
    window.addEventListener('resize', () => applySidebarState(appSidebar, window.innerWidth <= 1024));
    applySidebarState(appSidebar, window.innerWidth <= 1024);
    if (newChatBtn) { newChatBtn.addEventListener('click', () => window.location.reload()); }
    if (apiKeySettingsLink) { apiKeySettingsLink.addEventListener('click', (e) => { e.preventDefault(); toggleAdvancedToolModal(true, 'api'); if (window.current_user_is_authenticated_from_server) loadAndDisplayModels(); }); }
    if (jsonEditorLink) { jsonEditorLink.addEventListener('click', (e) => { e.preventDefault(); toggleAdvancedToolModal(true, 'json'); }); }
    if (featuresLink) { featuresLink.addEventListener('click', (e) => { e.preventDefault(); toggleAdvancedToolModal(false); toggleFeaturesSection(true); }); }
    if (modalCloseButton && advancedToolsModal) { modalCloseButton.addEventListener('click', () => toggleAdvancedToolModal(false)); advancedToolsModal.addEventListener('click', (e) => { if (e.target === advancedToolsModal) toggleAdvancedToolModal(false); }); }
    if (refreshModelsBtn) { refreshModelsBtn.addEventListener('click', () => { if (window.current_user_is_authenticated_from_server) loadAndDisplayModels(); }); }
    if (aiModelSelect) { aiModelSelect.addEventListener('change', (event) => { const newSelectedModel = event.target.value; localStorage.setItem('selectedAiModel', newSelectedModel); updateCurrentSetModelDisplay(newSelectedModel); if (newSelectedModel) appendMessage(`AI 模型已切换为: ${newSelectedModel}`, 'system'); }); }
    if (window.current_user_is_authenticated_from_server) { loadAndDisplayModels(); } else { if(aiModelSelect) aiModelSelect.innerHTML = '<option value="">请先登录</option>'; setModelLoadStatus("请登录以加载和选择模型。", true); updateCurrentSetModelDisplay("未登录"); }
}