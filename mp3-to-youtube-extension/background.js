// バックグラウンドスクリプト
// Chrome拡張機能のサービスワーカー

class BackgroundService {
    constructor() {
        this.setupEventListeners();
        this.initializeExtension();
    }

    setupEventListeners() {
        // 拡張機能のインストール時
        chrome.runtime.onInstalled.addListener((details) => {
            this.handleInstall(details);
        });

        // メッセージリスナー
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            this.handleMessage(request, sender, sendResponse);
            return true; // 非同期レスポンスを有効化
        });

        // コンテキストメニューのクリック
        chrome.contextMenus.onClicked.addListener((info, tab) => {
            this.handleContextMenuClick(info, tab);
        });

        // ダウンロード完了時
        chrome.downloads.onChanged.addListener((downloadDelta) => {
            this.handleDownloadChange(downloadDelta);
        });
    }

    initializeExtension() {
        // コンテキストメニューを作成
        this.createContextMenus();
        
        // 初期設定を保存
        this.setDefaultSettings();
    }

    handleInstall(details) {
        if (details.reason === 'install') {
            // 初回インストール時
            this.showWelcomeNotification();
            this.openWelcomePage();
        } else if (details.reason === 'update') {
            // アップデート時
            this.showUpdateNotification();
        }
    }

    async handleMessage(request, sender, sendResponse) {
        try {
            switch (request.action) {
                case 'openPopup':
                    await this.openPopup();
                    sendResponse({ success: true });
                    break;

                case 'saveConvertedVideo':
                    await this.saveConvertedVideo(request.data);
                    sendResponse({ success: true });
                    break;

                case 'getStorageData':
                    const data = await this.getStorageData(request.keys);
                    sendResponse({ data });
                    break;

                case 'setStorageData':
                    await this.setStorageData(request.data);
                    sendResponse({ success: true });
                    break;

                case 'openYouTubeUpload':
                    await this.openYouTubeUpload();
                    sendResponse({ success: true });
                    break;

                case 'showNotification':
                    await this.showNotification(request.notification);
                    sendResponse({ success: true });
                    break;

                default:
                    sendResponse({ error: 'Unknown action' });
            }
        } catch (error) {
            console.error('Background script error:', error);
            sendResponse({ error: error.message });
        }
    }

    createContextMenus() {
        // 右クリックメニューを作成
        chrome.contextMenus.create({
            id: 'mp3-to-youtube-convert',
            title: 'MP3ファイルを動画に変換',
            contexts: ['page', 'link'],
            documentUrlPatterns: ['*://*/*']
        });

        chrome.contextMenus.create({
            id: 'mp3-to-youtube-upload',
            title: 'YouTubeにアップロード',
            contexts: ['page'],
            documentUrlPatterns: ['*://www.youtube.com/*']
        });
    }

    async handleContextMenuClick(info, tab) {
        switch (info.menuItemId) {
            case 'mp3-to-youtube-convert':
                await this.openPopup();
                break;

            case 'mp3-to-youtube-upload':
                await this.openYouTubeUpload();
                break;
        }
    }

    async openPopup() {
        // ポップアップを開く（新しいタブで）
        await chrome.tabs.create({
            url: chrome.runtime.getURL('popup.html'),
            active: true
        });
    }

    async openYouTubeUpload() {
        // YouTubeアップロードページを開く
        await chrome.tabs.create({
            url: 'https://www.youtube.com/upload',
            active: true
        });
    }

    async saveConvertedVideo(videoData) {
        try {
            // Blobデータをダウンロード
            const blob = new Blob([videoData.data], { type: 'video/webm' });
            const url = URL.createObjectURL(blob);

            await chrome.downloads.download({
                url: url,
                filename: `${videoData.title || 'converted-video'}.webm`,
                saveAs: true
            });

            // 使用後にURLを解放
            setTimeout(() => URL.revokeObjectURL(url), 1000);

            await this.showNotification({
                type: 'success',
                title: '動画変換完了',
                message: 'MP3ファイルの動画変換が完了しました'
            });

        } catch (error) {
            console.error('Video save error:', error);
            await this.showNotification({
                type: 'error',
                title: '保存エラー',
                message: '動画の保存に失敗しました'
            });
        }
    }

    async getStorageData(keys) {
        return new Promise((resolve) => {
            chrome.storage.local.get(keys, (data) => {
                resolve(data);
            });
        });
    }

    async setStorageData(data) {
        return new Promise((resolve) => {
            chrome.storage.local.set(data, () => {
                resolve();
            });
        });
    }

    async setDefaultSettings() {
        const defaultSettings = {
            videoQuality: '720p',
            visualStyle: 'spectrum',
            colorTheme: 'vibrant',
            backgroundColor: '#000000',
            autoOpenYouTube: false,
            showNotifications: true
        };

        const currentSettings = await this.getStorageData(Object.keys(defaultSettings));
        
        // 未設定の項目のみデフォルト値を設定
        const newSettings = {};
        for (const [key, value] of Object.entries(defaultSettings)) {
            if (!(key in currentSettings)) {
                newSettings[key] = value;
            }
        }

        if (Object.keys(newSettings).length > 0) {
            await this.setStorageData(newSettings);
        }
    }

    async showNotification(notification) {
        const settings = await this.getStorageData(['showNotifications']);
        
        if (settings.showNotifications !== false) {
            chrome.notifications.create({
                type: 'basic',
                iconUrl: 'icons/icon48.png',
                title: notification.title,
                message: notification.message
            });
        }
    }

    showWelcomeNotification() {
        chrome.notifications.create({
            type: 'basic',
            iconUrl: 'icons/icon48.png',
            title: 'MP3 to YouTube Video Converter',
            message: 'インストールありがとうございます！MP3ファイルを簡単にYouTube用動画に変換できます。'
        });
    }

    showUpdateNotification() {
        chrome.notifications.create({
            type: 'basic',
            iconUrl: 'icons/icon48.png',
            title: 'MP3 to YouTube Video Converter',
            message: '拡張機能が更新されました。新機能をお試しください！'
        });
    }

    openWelcomePage() {
        chrome.tabs.create({
            url: chrome.runtime.getURL('welcome.html')
        });
    }

    handleDownloadChange(downloadDelta) {
        if (downloadDelta.state && downloadDelta.state.current === 'complete') {
            // ダウンロード完了時の処理
            this.showNotification({
                title: 'ダウンロード完了',
                message: '動画ファイルのダウンロードが完了しました'
            });
        }
    }

    // ユーティリティメソッド
    async getCurrentTab() {
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        return tab;
    }

    async isYouTubePage(tab) {
        return tab && tab.url && tab.url.includes('youtube.com');
    }

    async injectContentScript(tabId) {
        try {
            await chrome.scripting.executeScript({
                target: { tabId: tabId },
                files: ['content.js']
            });
        } catch (error) {
            console.error('Content script injection failed:', error);
        }
    }
}

// バックグラウンドサービスを初期化
new BackgroundService();