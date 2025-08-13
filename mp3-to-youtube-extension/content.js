// YouTube用コンテンツスクリプト
// YouTubeページでの追加機能を提供

class YouTubeEnhancer {
    constructor() {
        this.isYouTubePage = window.location.hostname === 'www.youtube.com';
        this.uploadButton = null;
        
        if (this.isYouTubePage) {
            this.init();
        }
    }

    init() {
        // YouTubeの読み込み完了を待つ
        this.waitForYouTubeLoad();
        
        // URLの変更を監視（SPAのため）
        this.observeURLChanges();
    }

    waitForYouTubeLoad() {
        const checkInterval = setInterval(() => {
            if (document.querySelector('ytd-app')) {
                clearInterval(checkInterval);
                this.enhanceYouTubePage();
            }
        }, 1000);
    }

    observeURLChanges() {
        let currentUrl = window.location.href;
        
        const observer = new MutationObserver(() => {
            if (window.location.href !== currentUrl) {
                currentUrl = window.location.href;
                setTimeout(() => this.enhanceYouTubePage(), 1000);
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    enhanceYouTubePage() {
        // アップロードページの場合
        if (window.location.pathname.includes('/upload')) {
            this.enhanceUploadPage();
        }
        
        // 通常のYouTubeページの場合
        this.addQuickUploadButton();
    }

    enhanceUploadPage() {
        // アップロードページに拡張機能へのリンクを追加
        const uploadContainer = document.querySelector('#upload-input-container');
        if (uploadContainer && !document.querySelector('.mp3-converter-hint')) {
            this.addConverterHint(uploadContainer);
        }
    }

    addConverterHint(container) {
        const hint = document.createElement('div');
        hint.className = 'mp3-converter-hint';
        hint.innerHTML = `
            <div style="
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: white;
                padding: 12px 16px;
                border-radius: 8px;
                margin: 16px 0;
                display: flex;
                align-items: center;
                gap: 12px;
                font-size: 14px;
                cursor: pointer;
                transition: transform 0.2s ease;
            " id="mp3-converter-banner">
                <div style="font-size: 20px;">🎵</div>
                <div>
                    <strong>MP3ファイルをお持ちですか？</strong><br>
                    <span style="opacity: 0.9;">拡張機能で簡単に動画に変換できます</span>
                </div>
                <div style="
                    background: rgba(255,255,255,0.2);
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 12px;
                    margin-left: auto;
                ">開く</div>
            </div>
        `;

        hint.addEventListener('click', () => {
            this.openExtensionPopup();
        });

        hint.addEventListener('mouseenter', () => {
            hint.style.transform = 'translateY(-2px)';
        });

        hint.addEventListener('mouseleave', () => {
            hint.style.transform = 'translateY(0)';
        });

        container.parentNode.insertBefore(hint, container);
    }

    addQuickUploadButton() {
        // YouTubeヘッダーにクイックアップロードボタンを追加
        const header = document.querySelector('#end');
        if (header && !document.querySelector('.mp3-quick-upload')) {
            this.createQuickUploadButton(header);
        }
    }

    createQuickUploadButton(header) {
        const button = document.createElement('button');
        button.className = 'mp3-quick-upload';
        button.innerHTML = `
            <div style="
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 8px 12px;
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: white;
                border: none;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 500;
                cursor: pointer;
                transition: all 0.2s ease;
                margin-right: 8px;
            ">
                <span>🎵</span>
                <span>MP3→動画</span>
            </div>
        `;

        button.addEventListener('click', () => {
            this.openExtensionPopup();
        });

        button.addEventListener('mouseenter', () => {
            button.firstElementChild.style.transform = 'scale(1.05)';
            button.firstElementChild.style.boxShadow = '0 4px 12px rgba(79, 172, 254, 0.4)';
        });

        button.addEventListener('mouseleave', () => {
            button.firstElementChild.style.transform = 'scale(1)';
            button.firstElementChild.style.boxShadow = 'none';
        });

        // YouTubeのヘッダーボタンの前に挿入
        const firstButton = header.querySelector('*');
        if (firstButton) {
            header.insertBefore(button, firstButton);
        } else {
            header.appendChild(button);
        }
    }

    openExtensionPopup() {
        // Chrome拡張機能のポップアップを開く
        chrome.runtime.sendMessage({
            action: 'openPopup'
        });
    }

    // ドラッグ&ドロップでMP3ファイルを検出
    setupDragAndDropDetection() {
        document.addEventListener('dragover', (e) => {
            e.preventDefault();
        });

        document.addEventListener('drop', (e) => {
            e.preventDefault();
            
            const files = Array.from(e.dataTransfer.files);
            const audioFiles = files.filter(file => file.type.startsWith('audio/'));
            
            if (audioFiles.length > 0) {
                this.showMP3ConversionOffer(audioFiles);
            }
        });
    }

    showMP3ConversionOffer(files) {
        // MP3ファイルがドロップされた時の変換提案
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        modal.innerHTML = `
            <div style="
                background: white;
                padding: 24px;
                border-radius: 12px;
                max-width: 400px;
                text-align: center;
                box-shadow: 0 20px 40px rgba(0,0,0,0.3);
            ">
                <div style="font-size: 48px; margin-bottom: 16px;">🎵</div>
                <h3 style="margin-bottom: 12px; color: #333;">MP3ファイルを検出しました</h3>
                <p style="color: #666; margin-bottom: 20px;">
                    ${files.length}個の音声ファイルをYouTube用動画に変換しますか？
                </p>
                <div style="display: flex; gap: 12px; justify-content: center;">
                    <button id="convert-files" style="
                        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                        color: white;
                        border: none;
                        padding: 10px 20px;
                        border-radius: 6px;
                        cursor: pointer;
                        font-weight: 500;
                    ">変換する</button>
                    <button id="cancel-conversion" style="
                        background: #f5f5f5;
                        color: #333;
                        border: 1px solid #ddd;
                        padding: 10px 20px;
                        border-radius: 6px;
                        cursor: pointer;
                    ">キャンセル</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // イベントリスナー
        modal.querySelector('#convert-files').addEventListener('click', () => {
            this.openExtensionPopup();
            document.body.removeChild(modal);
        });

        modal.querySelector('#cancel-conversion').addEventListener('click', () => {
            document.body.removeChild(modal);
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
    }
}

// YouTubeページの場合のみ初期化
if (window.location.hostname === 'www.youtube.com') {
    new YouTubeEnhancer();
}

// メッセージリスナー
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'getPageInfo') {
        sendResponse({
            url: window.location.href,
            title: document.title,
            isYouTube: window.location.hostname === 'www.youtube.com'
        });
    }
});