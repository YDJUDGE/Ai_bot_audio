import logging
from typing import Dict, Any, Optional

import librosa
import requests
from my_proof.models.proof_response import ProofResponse
from audio_processor import AudioProcess


class Proof:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.audio_process = AudioProcess()
        dlp_id = self.config.get('dlp_id', None)
        self.proof_response = ProofResponse(dlp_id=dlp_id)

    def check_authenticity(self, audio_file: str) -> float:
        """Проверяет подлинность аудио на основе его длительности"""
        try:
            duration = librosa.get_duration(filename=audio_file)
            if duration < 5:
                return 0.3
            return 1.0
        except Exception as e:
            logging.error(f"Ошибка при проверке подлинности: {e}")
            return 0.5

    def generate(self, audio_files) -> ProofResponse:
        """Generate proofs for all input files."""
        logging.info("Starting proof generation")
        total_score = 0
        unique_scores = []

        for input_file in audio_files:
            uniqueness_scores, _ = self.audio_process.process_audio(input_file)
            unique_scores.append(uniqueness_scores)
            total_score += uniqueness_scores

        uniqueness_avg = sum(unique_scores) / len(unique_scores) if unique_scores else 0
        value_threshold = fetch_random_number()

        # Calculate proof-of-contribution scores: https://docs.vana.org/vana/core-concepts/key-elements/proof-of-contribution/example-implementation
        self.proof_response.uniqueness = uniqueness_avg
        self.proof_response.quality = min(total_score / value_threshold, 1.0)
        self.proof_response.score = 0.7 * self.proof_response.quality + 0.3 * self.proof_response.uniqueness
        self.proof_response.valid = total_score >= value_threshold

        self.proof_response.authenticity = self.check_authenticity(audio_files[0]) if audio_files else 0.0
        self.proof_response.ownership = 1.0

        self.proof_response.attributes = {
            'total_score': total_score,
            'score_threshold': value_threshold
        }

        dlp_id = self.config.get('dlp_id', None)
        if dlp_id is not None:
            self.proof_response.metadata = {'dlp_id': dlp_id}
        else:
            self.proof_response.metadata = {}

        return self.proof_response


def fetch_random_number() -> float:
    """Demonstrate HTTP requests by fetching a random number from random.org."""
    try:
        response = requests.get('https://www.random.org/decimal-fractions/?num=1&dec=2&col=1&format=plain&rnd=new')
        return float(response.text.strip())
    except requests.RequestException as e:
        logging.warning(f"Error fetching random number: {e}. Using local random.")
        return __import__('random').random()
