// static/apiService.js
import { showAiLoading, showAiError, hideAiError, showManualLoading, hideManualJsonError, showManualJsonError, appendMessage, setInputDisabledState } from './uiUpdater.js';
import { displayChipDiagram } from './uiUpdater.js';

export async function triggerDiagramGenerationAPI(jsonString, isAiCall) {
    hideManualJsonError();
    const currentErrorBoxDisplayFunc = isAiCall ? showAiError : showManualJsonError;
    const chatMessages = document.getElementById('chatMessages');
    if(chatMessages){
        const existingDiagram = chatMessages.querySelector('.diagram-output-file:not(#diagramResultContainerTemplate)');
        if(existingDiagram) existingDiagram.remove();
    }
    if (!jsonString || !jsonString.trim()) {
        currentErrorBoxDisplayFunc('错误：JSON内容不能为空！');
        return;
    }
    try {
        const parsed = JSON.parse(jsonString);
        if (typeof parsed !== 'object' || !parsed.nodes) throw new Error("JSON结构不正确，缺少'nodes'键。");
    } catch (e) {
        currentErrorBoxDisplayFunc((isAiCall ? 'AI生成的JSON格式无效: ' : '编辑器中JSON格式无效: ') + e.message);
        return;
    }
    showManualLoading(true);
    if (isAiCall) showAiLoading(false);
    try {
        const response = await fetch('/generate_manual', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: new URLSearchParams({'chip_json': jsonString})
        });
        showManualLoading(false);
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error('服务器错误: ' + response.status + '\n' + errorText);
        }
        const htmlFragment = await response.text();
        displayChipDiagram(htmlFragment, isAiCall);
    } catch (error) {
        showManualLoading(false);
        currentErrorBoxDisplayFunc('图表生成失败: ' + error.message);
        appendMessage('图表生成过程中发生错误: ' + error.message, 'system');
    }
}

export async function fetchAiModelsAPI() {
    try {
        const response = await fetch('/get_ai_models');
        if (!response.ok) {
            let errorData = { error: `获取模型列表失败 (HTTP ${response.status})` };
            try { const errJson = await response.json(); errorData.error = errJson.error || errorData.error; } catch (e) { /* 忽略 */ }
            console.error("fetchAiModelsAPI HTTP error:", errorData.error);
            throw new Error(errorData.error);
        }
        const data = await response.json();
        if (!data.success) {
            console.error("fetchAiModelsAPI API returned success=false:", data.error);
            throw new Error(data.error || "获取模型列表时发生未知错误。");
        }
        return data.models;
    } catch (error) {
        console.error("fetchAiModelsAPI fetch/catch error:", error);
        throw error;
    }
}

export async function requestAiGenerationStream(description, apiKey, modelName, onChunkReceived, onStreamEnd, onError) {
    let accumulatedContentResponse = "";
    showAiLoading(true);
    setInputDisabledState(true); // 禁用输入
    hideAiError();
    try {
        const response = await fetch('/generate_chip_ai_stream', {
            method: 'POST',
            body: new URLSearchParams({
                'description': description,
                'api_key': apiKey,
                'model_name': modelName || ''
            })
        });
        if (!response.ok) {
            let errorData;
            try { errorData = await response.json(); } catch (e) {
                errorData = { error: `AI服务器通信错误: ${response.status} ${response.statusText}` };
            }
            throw new Error(errorData.error || JSON.stringify(errorData));
        }
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let cancelled = false;
        async function push() {
            try {
                const { done, value } = await reader.read();
                if (done || cancelled) {
                    if (!cancelled) onStreamEnd(accumulatedContentResponse);
                    showAiLoading(false);
                    setInputDisabledState(false); // 启用输入
                    return;
                }
                const chunkText = decoder.decode(value, { stream: true });
                const lines = chunkText.split('\n\n');
                for (const line of lines) {
                    if (cancelled) break;
                    if (line.startsWith('data: ')) {
                        try {
                            const jsonData = JSON.parse(line.substring(5).trim());
                            if (jsonData.error) {
                                console.error("AI Stream Error from backend:", jsonData.error);
                                onError("AI处理错误: " + jsonData.error);
                                cancelled = true; 
                                if(reader && typeof reader.cancel === 'function') reader.cancel().catch(e => console.warn("Error cancelling reader:", e));
                                showAiLoading(false);
                                setInputDisabledState(false); // 启用输入
                                return;
                            } else if (jsonData.content) { 
                                accumulatedContentResponse += jsonData.content;
                                onChunkReceived({ type: "content", data: jsonData.content });
                            }
                        } catch (e) {
                            console.warn("解析SSE数据块时非JSON内容或格式错误:", line, e);
                        }
                    }
                }
                if (!cancelled) await push();
            } catch (streamError) {
                console.error('读取AI响应流时出错:', streamError);
                if (!cancelled) onError("读取AI响应流时出错: " + streamError.message);
                showAiLoading(false);
                setInputDisabledState(false); // 启用输入
            }
        }
        await push();
    } catch (fetchError) {
        console.error("连接AI服务失败:", fetchError);
        onError("连接AI服务失败: " + fetchError.message);
        showAiLoading(false);
        setInputDisabledState(false); // 启用输入
    }
}

export async function saveApiKeyAPI(apiKey) {
    try {
        const response = await fetch('/save_api_key', {
            method: 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: new URLSearchParams({'api_key': apiKey})
        });
        if (!response.ok) {
             const errorText = await response.text();
             throw new Error(`保存API Key请求失败: ${response.status} ${errorText || response.statusText}`);
        }
        return response.json();
    } catch (error) {
        console.error("saveApiKeyAPI Error:", error);
        return { success: false, error: error.message || "网络或未知错误" };
    }
}