import os
import numpy as np
import librosa
from scipy.spatial.distance import cosine
import soundfile as sf

AUDIO_DIR = "data/audio"

class AudioProcess:
    def __init__(self):
        self.processed_features = []  # Храним признаки обработаных аудио

    @staticmethod
    def convert_to_wav(input_path: str, output_path: str):
        """Конвертирует файд в wav формат"""
        y, sr = librosa.load(input_path, sr=16000)
        sf.write(output_path, y, sr)

    def extract_features(self, file_path: str):
        """Извлекает MFCC признаки из файла"""
        y, sr = librosa.load(file_path, sr=16000)  # Загружает аудио с 16kHz
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)  # Берем 20 MFCC
        return np.mean(mfcc, axis=1)  # Усредняем по временной оси

    def calculate_uniqueness(self, features):
        """Сравнивает признаки текущего аудио со всеми предыдущими"""
        if not self.processed_features:
            return 1.0
        similarities = [1 - cosine(features, f) for f in self.processed_features]
        uniqueness = 1 - max(similarities)  # Чем меньше похожих, тем больше уникальность
        return uniqueness

    def process_audio(self, file_path: str):
        """Обрабатывает аудио и вычисляет его уникальность"""
        features = self.extract_features(file_path)
        uniqueness = self.calculate_uniqueness(features)

        return uniqueness, features

if __name__ == "__main__":
    processor = AudioProcess()
    for file_name in os.listdir(AUDIO_DIR):
        if file_name.endswith((".mp3", ".wav", ".ogg")):
            file_path = os.path.join(AUDIO_DIR, file_name)
            uniqueness = processor.process_audio(file_path)
            print(f"Файл {file_name}: уникалность {uniqueness:.2f}")


