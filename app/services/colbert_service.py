from FlagEmbedding import BGEM3FlagModel
from app.config import get_settings
from loguru import logger
import torch

class ColbertService:
    def __init__(self):
        self.settings = get_settings()
        self.enabled = self.settings.colbert_enabled
        self.model = None
        
        if self.enabled:
            try:
                device = "cuda" if torch.cuda.is_available() else "cpu"
                if torch.backends.mps.is_available():
                    device = "mps"
                
                logger.info(f"Initializing BGE-M3 model on {device}...")
                self.model = BGEM3FlagModel(
                    self.settings.colbert_model,
                    use_fp16=True if device != "cpu" else False,
                    device=device
                )
                logger.info("BGE-M3 model initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize BGE-M3 model: {e}")
                self.enabled = False

    def generate_colbert_vectors(self, texts: list[str]) -> list[list[list[float]]]:
        """
        Generate ColBERT multi-vectors for a list of texts.
        Returns a list of lists of vectors (one list of vectors per text).
        """
        if not self.enabled or not self.model:
            logger.warning("ColBERT service is disabled or model not initialized")
            return []

        try:
            # BGE-M3 encode returns a dictionary with 'colbert_vecs'
            output = self.model.encode(
                texts, 
                return_dense=False, 
                return_sparse=False, 
                return_colbert_vecs=True
            )
            
            # output['colbert_vecs'] is a list of np.ndarrays
            # Convert to list of list of floats
            return [vec.tolist() for vec in output['colbert_vecs']]
            
        except Exception as e:
            logger.error(f"Error generating ColBERT vectors: {e}")
            raise