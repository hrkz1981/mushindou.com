#!/bin/bash

echo "歌詞同期アプリのセットアップを開始します..."

# Pythonの仮想環境を作成
echo "仮想環境を作成中..."
python3 -m venv lyrics_app_env

# 仮想環境を有効化
echo "仮想環境を有効化中..."
source lyrics_app_env/bin/activate

# 必要なライブラリをインストール
echo "必要なライブラリをインストール中..."
pip install --upgrade pip

# macOS用のpyaudio依存関係
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macOS用の依存関係をインストール中..."
    brew install portaudio
fi

# 基本ライブラリをインストール
pip install pygame==2.5.2
pip install SpeechRecognition==3.10.0
pip install pyaudio==0.2.11

echo "セットアップ完了！"
echo ""
echo "アプリを起動するには以下のコマンドを実行してください:"
echo "source lyrics_app_env/bin/activate"
echo "python lyrics_sync_app.py"
echo ""
echo "使用方法:"
echo "1. 'WAVファイルを選択'でWAVファイルを選択"
echo "2. '歌詞解析'ボタンで自動歌詞検出を実行"
echo "3. '再生'ボタンで音楽を再生すると歌詞が同期表示されます"