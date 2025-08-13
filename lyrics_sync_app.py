#!/usr/bin/env python3
"""
音楽再生と歌詞同期表示デスクトップアプリ
WAVファイルから自動で歌詞を検出し、リアルタイムで表示
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pygame
import speech_recognition as sr
import threading
import time
import wave
import os
from pathlib import Path

class LyricsSyncApp:
    def __init__(self, root):
        self.root = root
        self.root.title("歌詞同期アプリ")
        self.root.geometry("800x600")
        
        # 音楽再生関連
        pygame.mixer.init()
        self.current_file = None
        self.is_playing = False
        self.is_paused = False
        self.start_time = None
        self.pause_time = 0
        
        # 音声認識関連
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.lyrics_data = []
        self.current_lyrics_index = 0
        
        # GUI要素を作成
        self.setup_gui()
        
        # 更新用スレッド
        self.update_thread = None
        self.stop_update = False
        
    def setup_gui(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # ファイル選択フレーム
        file_frame = ttk.Frame(main_frame)
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(file_frame, text="WAVファイルを選択", command=self.select_file).grid(row=0, column=0, padx=(0, 10))
        self.file_label = ttk.Label(file_frame, text="ファイルが選択されていません")
        self.file_label.grid(row=0, column=1, sticky=tk.W)
        
        # 制御ボタンフレーム
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        
        self.play_button = ttk.Button(control_frame, text="再生", command=self.play_pause, state="disabled")
        self.play_button.grid(row=0, column=0, padx=(0, 5))
        
        self.stop_button = ttk.Button(control_frame, text="停止", command=self.stop, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=(0, 5))
        
        self.analyze_button = ttk.Button(control_frame, text="歌詞解析", command=self.analyze_lyrics, state="disabled")
        self.analyze_button.grid(row=0, column=2, padx=(0, 5))
        
        # 進行状況バー
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, length=400)
        self.progress_bar.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 時間表示
        self.time_label = ttk.Label(main_frame, text="00:00 / 00:00")
        self.time_label.grid(row=3, column=0, columnspan=2, pady=(0, 10))
        
        # 歌詞表示エリア
        lyrics_frame = ttk.LabelFrame(main_frame, text="歌詞", padding="10")
        lyrics_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 歌詞テキスト表示
        self.lyrics_text = tk.Text(lyrics_frame, height=15, width=70, wrap=tk.WORD, font=("Arial", 12))
        scrollbar = ttk.Scrollbar(lyrics_frame, orient="vertical", command=self.lyrics_text.yview)
        self.lyrics_text.configure(yscrollcommand=scrollbar.set)
        
        self.lyrics_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # ステータスバー
        self.status_label = ttk.Label(main_frame, text="準備完了")
        self.status_label.grid(row=5, column=0, columnspan=2, sticky=tk.W)
        
        # グリッド設定
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        lyrics_frame.columnconfigure(0, weight=1)
        lyrics_frame.rowconfigure(0, weight=1)
        
    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="WAVファイルを選択",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )
        
        if file_path:
            self.current_file = file_path
            filename = os.path.basename(file_path)
            self.file_label.config(text=f"選択中: {filename}")
            self.play_button.config(state="normal")
            self.analyze_button.config(state="normal")
            self.status_label.config(text="ファイルが選択されました")
            
    def play_pause(self):
        if not self.current_file:
            return
            
        if not self.is_playing:
            # 再生開始
            try:
                pygame.mixer.music.load(self.current_file)
                pygame.mixer.music.play()
                self.is_playing = True
                self.is_paused = False
                self.start_time = time.time()
                self.play_button.config(text="一時停止")
                self.stop_button.config(state="normal")
                self.status_label.config(text="再生中...")
                
                # 更新スレッド開始
                self.stop_update = False
                self.update_thread = threading.Thread(target=self.update_progress)
                self.update_thread.daemon = True
                self.update_thread.start()
                
            except pygame.error as e:
                messagebox.showerror("エラー", f"ファイルの再生に失敗しました: {e}")
                
        elif self.is_paused:
            # 一時停止から再開
            pygame.mixer.music.unpause()
            self.is_paused = False
            self.start_time = time.time() - self.pause_time
            self.play_button.config(text="一時停止")
            self.status_label.config(text="再生中...")
            
        else:
            # 一時停止
            pygame.mixer.music.pause()
            self.is_paused = True
            self.pause_time = time.time() - self.start_time
            self.play_button.config(text="再生")
            self.status_label.config(text="一時停止中")
            
    def stop(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.is_paused = False
        self.start_time = None
        self.pause_time = 0
        self.play_button.config(text="再生")
        self.stop_button.config(state="disabled")
        self.progress_var.set(0)
        self.time_label.config(text="00:00 / 00:00")
        self.status_label.config(text="停止")
        self.stop_update = True
        
    def update_progress(self):
        while self.is_playing and not self.stop_update:
            if not self.is_paused and pygame.mixer.music.get_busy():
                current_time = time.time() - self.start_time
                duration = self.get_audio_duration()
                
                if duration > 0:
                    progress = (current_time / duration) * 100
                    self.progress_var.set(min(progress, 100))
                    
                    current_str = self.format_time(current_time)
                    duration_str = self.format_time(duration)
                    self.time_label.config(text=f"{current_str} / {duration_str}")
                    
                    # 歌詞表示更新
                    self.update_lyrics_display(current_time)
                    
                time.sleep(0.1)
            else:
                if not pygame.mixer.music.get_busy() and self.is_playing:
                    # 再生終了
                    self.root.after(0, self.stop)
                time.sleep(0.1)
                
    def get_audio_duration(self):
        try:
            with wave.open(self.current_file, 'rb') as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                duration = frames / float(sample_rate)
                return duration
        except:
            return 0
            
    def format_time(self, seconds):
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
        
    def analyze_lyrics(self):
        if not self.current_file:
            return
            
        self.status_label.config(text="歌詞解析中...")
        self.analyze_button.config(state="disabled")
        
        # 解析を別スレッドで実行
        analysis_thread = threading.Thread(target=self._analyze_lyrics_thread)
        analysis_thread.daemon = True
        analysis_thread.start()
        
    def _analyze_lyrics_thread(self):
        try:
            # 音声ファイルを分割して音声認識
            self.lyrics_data = []
            
            # 10秒ごとに分割して解析
            duration = self.get_audio_duration()
            segment_length = 10  # 10秒ごと
            
            with wave.open(self.current_file, 'rb') as wav_file:
                sample_rate = wav_file.getframerate()
                
                for start_time in range(0, int(duration), segment_length):
                    end_time = min(start_time + segment_length, duration)
                    
                    # セグメントを抽出
                    wav_file.setpos(int(start_time * sample_rate))
                    frames = wav_file.readframes(int((end_time - start_time) * sample_rate))
                    
                    # 一時ファイルとして保存
                    temp_file = "/tmp/temp_segment.wav"
                    with wave.open(temp_file, 'wb') as temp_wav:
                        temp_wav.setnchannels(wav_file.getnchannels())
                        temp_wav.setsampwidth(wav_file.getsampwidth())
                        temp_wav.setframerate(sample_rate)
                        temp_wav.writeframes(frames)
                    
                    # 音声認識
                    try:
                        with sr.AudioFile(temp_file) as source:
                            audio = self.recognizer.record(source)
                            text = self.recognizer.recognize_google(audio, language='ja-JP')
                            
                            self.lyrics_data.append({
                                'start_time': start_time,
                                'end_time': end_time,
                                'text': text
                            })
                            
                    except sr.UnknownValueError:
                        # 音声が認識できない場合
                        self.lyrics_data.append({
                            'start_time': start_time,
                            'end_time': end_time,
                            'text': '[音楽]'
                        })
                    except sr.RequestError:
                        # API エラー
                        self.lyrics_data.append({
                            'start_time': start_time,
                            'end_time': end_time,
                            'text': '[認識エラー]'
                        })
                    
                    # 進捗更新
                    progress = (start_time / duration) * 100
                    self.root.after(0, lambda p=progress: self.status_label.config(text=f"解析中... {p:.0f}%"))
            
            # 結果表示
            self.root.after(0, self._display_lyrics_result)
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("エラー", f"歌詞解析に失敗しました: {e}"))
            self.root.after(0, lambda: self.analyze_button.config(state="normal"))
            
    def _display_lyrics_result(self):
        self.lyrics_text.delete(1.0, tk.END)
        
        for lyric in self.lyrics_data:
            time_str = self.format_time(lyric['start_time'])
            self.lyrics_text.insert(tk.END, f"[{time_str}] {lyric['text']}\n")
            
        self.status_label.config(text="歌詞解析完了")
        self.analyze_button.config(state="normal")
        
    def update_lyrics_display(self, current_time):
        # 現在の時間に対応する歌詞をハイライト
        for i, lyric in enumerate(self.lyrics_data):
            if lyric['start_time'] <= current_time < lyric['end_time']:
                if i != self.current_lyrics_index:
                    self.current_lyrics_index = i
                    # ハイライト表示を更新
                    self.root.after(0, lambda: self._highlight_current_lyrics(i))
                break
                
    def _highlight_current_lyrics(self, index):
        self.lyrics_text.tag_remove('highlight', 1.0, tk.END)
        
        if 0 <= index < len(self.lyrics_data):
            line_start = f"{index + 1}.0"
            line_end = f"{index + 1}.end"
            self.lyrics_text.tag_add('highlight', line_start, line_end)
            self.lyrics_text.tag_config('highlight', background='yellow')
            self.lyrics_text.see(line_start)

def main():
    root = tk.Tk()
    app = LyricsSyncApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()