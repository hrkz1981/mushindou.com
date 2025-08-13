class MP3ToVideoConverter {
    constructor() {
        this.currentStep = 1;
        this.maxStep = 4;
        this.selectedFiles = [];
        this.currentAudio = null;
        this.canvas = null;
        this.ctx = null;
        this.audioContext = null;
        this.analyser = null;
        this.frequencyData = null;
        this.isPreviewPlaying = false;
        this.animationId = null;
        
        this.initializeElements();
        this.setupEventListeners();
        this.updateStepVisibility();
    }

    initializeElements() {
        this.elements = {
            audioFile: document.getElementById('audioFile'),
            fileList: document.getElementById('fileList'),
            videoQuality: document.getElementById('videoQuality'),
            visualStyle: document.getElementById('visualStyle'),
            colorTheme: document.getElementById('colorTheme'),
            backgroundColor: document.getElementById('backgroundColor'),
            videoTitle: document.getElementById('videoTitle'),
            artistName: document.getElementById('artistName'),
            previewCanvas: document.getElementById('previewCanvas'),
            previewPlay: document.getElementById('previewPlay'),
            previewStop: document.getElementById('previewStop'),
            progressContainer: document.getElementById('progressContainer'),
            progressFill: document.getElementById('progressFill'),
            progressText: document.getElementById('progressText'),
            statusMessage: document.getElementById('statusMessage'),
            convertBtn: document.getElementById('convertBtn'),
            downloadBtn: document.getElementById('downloadBtn'),
            prevBtn: document.getElementById('prevBtn'),
            nextBtn: document.getElementById('nextBtn')
        };

        this.canvas = this.elements.previewCanvas;
        this.ctx = this.canvas.getContext('2d');
    }

    setupEventListeners() {
        // ファイル選択
        this.elements.audioFile.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // ドラッグ&ドロップ
        const uploadArea = document.querySelector('.upload-area');
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#00f2fe';
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.style.borderColor = '#4facfe';
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#4facfe';
            this.handleFileSelect({ target: { files: e.dataTransfer.files } });
        });

        // プレビュー制御
        this.elements.previewPlay.addEventListener('click', () => this.togglePreview());
        this.elements.previewStop.addEventListener('click', () => this.stopPreview());

        // 変換・ダウンロード
        this.elements.convertBtn.addEventListener('click', () => this.convertToVideo());
        this.elements.downloadBtn.addEventListener('click', () => this.downloadVideo());

        // ナビゲーション
        this.elements.prevBtn.addEventListener('click', () => this.previousStep());
        this.elements.nextBtn.addEventListener('click', () => this.nextStep());

        // 設定変更時のプレビュー更新
        ['visualStyle', 'colorTheme', 'backgroundColor'].forEach(id => {
            this.elements[id].addEventListener('change', () => this.updatePreview());
        });
    }

    handleFileSelect(event) {
        const files = Array.from(event.target.files);
        
        files.forEach(file => {
            if (file.type.startsWith('audio/')) {
                this.selectedFiles.push(file);
            }
        });

        this.displayFileList();
        this.updateNavigationButtons();
        
        if (this.selectedFiles.length > 0) {
            this.loadFirstAudio();
        }
    }

    displayFileList() {
        this.elements.fileList.innerHTML = '';
        
        this.selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            
            fileItem.innerHTML = `
                <div class="file-info">
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${this.formatFileSize(file.size)}</span>
                </div>
                <button class="file-remove" onclick="removeFile(${index})">削除</button>
            `;
            
            this.elements.fileList.appendChild(fileItem);
        });
    }

    removeFile(index) {
        this.selectedFiles.splice(index, 1);
        this.displayFileList();
        this.updateNavigationButtons();
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async loadFirstAudio() {
        if (this.selectedFiles.length === 0) return;

        const file = this.selectedFiles[0];
        const url = URL.createObjectURL(file);
        
        this.currentAudio = new Audio(url);
        this.currentAudio.crossOrigin = 'anonymous';
        
        // ファイル名から自動でタイトルを設定
        const filename = file.name.replace(/\.[^/.]+$/, "");
        this.elements.videoTitle.value = filename;

        await this.setupAudioAnalysis();
    }

    async setupAudioAnalysis() {
        try {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            const source = this.audioContext.createMediaElementSource(this.currentAudio);
            this.analyser = this.audioContext.createAnalyser();
            
            this.analyser.fftSize = 512;
            this.frequencyData = new Uint8Array(this.analyser.frequencyBinCount);
            
            source.connect(this.analyser);
            this.analyser.connect(this.audioContext.destination);
            
            this.updatePreview();
        } catch (error) {
            console.error('Audio analysis setup failed:', error);
        }
    }

    updatePreview() {
        if (!this.ctx) return;

        this.drawVisualization();
    }

    drawVisualization() {
        const width = this.canvas.width;
        const height = this.canvas.height;
        
        // 背景をクリア
        const bgColor = this.elements.backgroundColor.value;
        this.ctx.fillStyle = bgColor;
        this.ctx.fillRect(0, 0, width, height);

        // 音声データを取得（プレビュー用はランダムデータ）
        const dataArray = new Uint8Array(256);
        if (this.frequencyData && this.isPreviewPlaying) {
            this.analyser.getByteFrequencyData(this.frequencyData);
            dataArray.set(this.frequencyData.slice(0, 256));
        } else {
            // デモ用ランダムデータ
            for (let i = 0; i < dataArray.length; i++) {
                dataArray[i] = Math.random() * 128 + Math.sin(Date.now() * 0.001 + i * 0.1) * 64;
            }
        }

        const visualStyle = this.elements.visualStyle.value;
        const colorTheme = this.elements.colorTheme.value;

        switch (visualStyle) {
            case 'spectrum':
                this.drawSpectrum(dataArray, colorTheme);
                break;
            case 'waveform':
                this.drawWaveform(dataArray, colorTheme);
                break;
            case 'particles':
                this.drawParticles(dataArray, colorTheme);
                break;
            case 'abstract':
                this.drawAbstract(dataArray, colorTheme);
                break;
            case 'minimal':
                this.drawMinimal(dataArray, colorTheme);
                break;
        }

        // タイトルとアーティスト名を描画
        this.drawText();
    }

    drawSpectrum(dataArray, colorTheme) {
        const width = this.canvas.width;
        const height = this.canvas.height;
        const barWidth = width / dataArray.length * 2;

        for (let i = 0; i < dataArray.length; i++) {
            const barHeight = (dataArray[i] / 255) * height * 0.8;
            const x = i * barWidth;
            const y = height - barHeight;

            const color = this.getColor(i, dataArray.length, colorTheme);
            this.ctx.fillStyle = color;
            this.ctx.fillRect(x, y, barWidth - 2, barHeight);
        }
    }

    drawWaveform(dataArray, colorTheme) {
        const width = this.canvas.width;
        const height = this.canvas.height;
        const centerY = height / 2;

        this.ctx.beginPath();
        this.ctx.lineWidth = 3;
        this.ctx.strokeStyle = this.getColor(0, 1, colorTheme);

        for (let i = 0; i < dataArray.length; i++) {
            const x = (i / dataArray.length) * width;
            const y = centerY + ((dataArray[i] - 128) / 128) * centerY * 0.8;

            if (i === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        }

        this.ctx.stroke();
    }

    drawParticles(dataArray, colorTheme) {
        const width = this.canvas.width;
        const height = this.canvas.height;
        const centerX = width / 2;
        const centerY = height / 2;

        for (let i = 0; i < dataArray.length; i += 4) {
            const amplitude = dataArray[i] / 255;
            const angle = (i / dataArray.length) * Math.PI * 2;
            const radius = amplitude * 200;

            const x = centerX + Math.cos(angle) * radius;
            const y = centerY + Math.sin(angle) * radius;

            this.ctx.fillStyle = this.getColor(i, dataArray.length, colorTheme);
            this.ctx.beginPath();
            this.ctx.arc(x, y, amplitude * 8 + 2, 0, Math.PI * 2);
            this.ctx.fill();
        }
    }

    drawAbstract(dataArray, colorTheme) {
        const width = this.canvas.width;
        const height = this.canvas.height;

        // 複数の円を描画
        for (let i = 0; i < dataArray.length; i += 8) {
            const size = (dataArray[i] / 255) * 100;
            const x = Math.random() * width;
            const y = Math.random() * height;

            const gradient = this.ctx.createRadialGradient(x, y, 0, x, y, size);
            const color1 = this.getColor(i, dataArray.length, colorTheme);
            const color2 = this.getColor(i + 4, dataArray.length, colorTheme);

            gradient.addColorStop(0, color1 + '80');
            gradient.addColorStop(1, color2 + '20');

            this.ctx.fillStyle = gradient;
            this.ctx.beginPath();
            this.ctx.arc(x, y, size, 0, Math.PI * 2);
            this.ctx.fill();
        }
    }

    drawMinimal(dataArray, colorTheme) {
        const width = this.canvas.width;
        const height = this.canvas.height;
        const centerX = width / 2;
        const centerY = height / 2;

        // 平均音量を計算
        const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
        const intensity = average / 255;

        // 中央に円を描画
        const radius = 50 + intensity * 150;
        const gradient = this.ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, radius);

        const color = this.getColor(0, 1, colorTheme);
        gradient.addColorStop(0, color + 'CC');
        gradient.addColorStop(1, color + '00');

        this.ctx.fillStyle = gradient;
        this.ctx.beginPath();
        this.ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
        this.ctx.fill();
    }

    drawText() {
        const width = this.canvas.width;
        const height = this.canvas.height;
        const title = this.elements.videoTitle.value;
        const artist = this.elements.artistName.value;

        if (title) {
            this.ctx.fillStyle = '#FFFFFF';
            this.ctx.font = 'bold 24px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'bottom';
            
            // 影を追加
            this.ctx.fillStyle = '#00000080';
            this.ctx.fillText(title, width / 2 + 2, height - 62);
            
            this.ctx.fillStyle = '#FFFFFF';
            this.ctx.fillText(title, width / 2, height - 60);
        }

        if (artist) {
            this.ctx.fillStyle = '#CCCCCC';
            this.ctx.font = '16px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'bottom';
            
            // 影を追加
            this.ctx.fillStyle = '#00000080';
            this.ctx.fillText(artist, width / 2 + 1, height - 31);
            
            this.ctx.fillStyle = '#CCCCCC';
            this.ctx.fillText(artist, width / 2, height - 30);
        }
    }

    getColor(index, total, theme) {
        const hue = (index / total) * 360;

        switch (theme) {
            case 'vibrant':
                return `hsl(${hue}, 80%, 60%)`;
            case 'neon':
                return `hsl(${hue}, 100%, 50%)`;
            case 'pastel':
                return `hsl(${hue}, 50%, 80%)`;
            case 'monochrome':
                const gray = Math.floor((index / total) * 255);
                return `rgb(${gray}, ${gray}, ${gray})`;
            case 'sunset':
                const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'];
                return colors[index % colors.length];
            default:
                return `hsl(${hue}, 70%, 50%)`;
        }
    }

    togglePreview() {
        if (!this.currentAudio) return;

        if (this.isPreviewPlaying) {
            this.stopPreview();
        } else {
            this.startPreview();
        }
    }

    async startPreview() {
        if (!this.currentAudio) return;

        try {
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }

            await this.currentAudio.play();
            this.isPreviewPlaying = true;
            this.elements.previewPlay.textContent = '⏸️ 一時停止';

            this.animatePreview();
        } catch (error) {
            console.error('Preview playback failed:', error);
        }
    }

    stopPreview() {
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
        }

        this.isPreviewPlaying = false;
        this.elements.previewPlay.textContent = '▶️ プレビュー再生';

        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
    }

    animatePreview() {
        if (this.isPreviewPlaying) {
            this.drawVisualization();
            this.animationId = requestAnimationFrame(() => this.animatePreview());
        }
    }

    async convertToVideo() {
        if (this.selectedFiles.length === 0) return;

        this.elements.convertBtn.disabled = true;
        this.elements.progressContainer.style.display = 'block';
        this.elements.statusMessage.textContent = '動画変換中...';

        try {
            // MediaRecorderを使用して動画を作成
            const stream = this.canvas.captureStream(30); // 30fps
            
            // 音声ストリームを追加（実際の実装では音声ファイルから取得）
            if (this.currentAudio && this.audioContext) {
                const audioDestination = this.audioContext.createMediaStreamDestination();
                const source = this.audioContext.createMediaElementSource(this.currentAudio);
                source.connect(audioDestination);
                
                // 音声トラックを追加
                audioDestination.stream.getAudioTracks().forEach(track => {
                    stream.addTrack(track);
                });
            }

            const mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'video/webm; codecs=vp9,opus'
            });

            const chunks = [];
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    chunks.push(event.data);
                }
            };

            mediaRecorder.onstop = () => {
                const blob = new Blob(chunks, { type: 'video/webm' });
                this.videoBlob = blob;
                
                this.elements.progressFill.style.width = '100%';
                this.elements.progressText.textContent = '100%';
                this.elements.statusMessage.textContent = '変換完了！';
                this.elements.downloadBtn.style.display = 'inline-block';
                this.elements.convertBtn.disabled = false;
            };

            // 録画開始
            mediaRecorder.start();
            
            // プレビューアニメーションを開始
            this.startRecordingAnimation();

            // 音声の長さに応じて録画時間を調整（デモでは10秒）
            const recordingDuration = this.currentAudio ? this.currentAudio.duration * 1000 : 10000;
            
            setTimeout(() => {
                mediaRecorder.stop();
                this.stopPreview();
            }, Math.min(recordingDuration, 30000)); // 最大30秒

        } catch (error) {
            console.error('Video conversion failed:', error);
            this.elements.statusMessage.textContent = '変換に失敗しました';
            this.elements.convertBtn.disabled = false;
        }
    }

    startRecordingAnimation() {
        this.isPreviewPlaying = true;
        let progress = 0;
        const duration = this.currentAudio ? this.currentAudio.duration : 10;

        const updateProgress = () => {
            if (progress < 100) {
                progress += (100 / (duration * 30)); // 30fps
                this.elements.progressFill.style.width = `${Math.min(progress, 100)}%`;
                this.elements.progressText.textContent = `${Math.floor(progress)}%`;
                
                this.drawVisualization();
                requestAnimationFrame(updateProgress);
            }
        };

        if (this.currentAudio) {
            this.currentAudio.currentTime = 0;
            this.currentAudio.play();
        }

        updateProgress();
    }

    downloadVideo() {
        if (!this.videoBlob) return;

        const url = URL.createObjectURL(this.videoBlob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${this.elements.videoTitle.value || 'music-video'}.webm`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        this.elements.statusMessage.textContent = 'ダウンロード完了！';
    }

    // ステップナビゲーション
    nextStep() {
        if (this.currentStep < this.maxStep) {
            this.currentStep++;
            this.updateStepVisibility();
            this.updateNavigationButtons();
        }
    }

    previousStep() {
        if (this.currentStep > 1) {
            this.currentStep--;
            this.updateStepVisibility();
            this.updateNavigationButtons();
        }
    }

    updateStepVisibility() {
        for (let i = 1; i <= this.maxStep; i++) {
            const stepElement = document.getElementById(`step${i}`);
            stepElement.style.display = i === this.currentStep ? 'block' : 'none';
        }
    }

    updateNavigationButtons() {
        this.elements.prevBtn.disabled = this.currentStep === 1;
        
        if (this.currentStep === 1) {
            this.elements.nextBtn.disabled = this.selectedFiles.length === 0;
        } else {
            this.elements.nextBtn.disabled = this.currentStep === this.maxStep;
        }
    }
}

// グローバル関数
function removeFile(index) {
    if (window.converter) {
        window.converter.removeFile(index);
    }
}

// 初期化
document.addEventListener('DOMContentLoaded', () => {
    window.converter = new MP3ToVideoConverter();
});