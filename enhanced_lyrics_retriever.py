import time
import logging
from lyrics_ovh_extractor import LyricsOvhExtractor

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("lyrics_retriever.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("EnhancedLyricsRetriever")

class EnhancedLyricsRetriever:
    """
    Versión mejorada del recuperador de letras con manejo de errores y validación
    """
    
    def __init__(self, max_retries=3, retry_delay=2):
        """
        Inicializa el recuperador de letras con el extractor de lyrics.ovh
        
        Args:
            max_retries (int): Número máximo de intentos para obtener letras
            retry_delay (int): Tiempo de espera entre intentos en segundos
        """
        self.extractor = LyricsOvhExtractor()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
    
    def validate_input(self, title, artist):
        """
        Valida los parámetros de entrada
        
        Args:
            title (str): Título de la canción
            artist (str): Nombre del artista o banda
            
        Returns:
            tuple: (bool, str) - (es_válido, mensaje_error)
        """
        if not title:
            return False, "El título de la canción es obligatorio"
        
        if not artist:
            return False, "El nombre del artista es obligatorio"
        
        if len(title) < 2:
            return False, "El título de la canción debe tener al menos 2 caracteres"
        
        if len(artist) < 2:
            return False, "El nombre del artista debe tener al menos 2 caracteres"
        
        return True, ""
    
    def get_lyrics_with_retry(self, title, artist):
        """
        Obtiene las letras de una canción con reintentos en caso de error
        
        Args:
            title (str): Título de la canción
            artist (str): Nombre del artista o banda
            
        Returns:
            dict: Diccionario con el estado de la búsqueda y las letras o mensaje de error
        """
        # Validar parámetros de entrada
        is_valid, error_message = self.validate_input(title, artist)
        if not is_valid:
            logger.error(f"Error de validación: {error_message}")
            return {
                "status": False,
                "error": error_message
            }
        
        # Intentar obtener las letras con reintentos
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"Intento {attempt}/{self.max_retries} para obtener letras de '{title}' por '{artist}'")
                
                # Intentar obtener las letras usando el extractor
                result = self.extractor.get_lyrics(title, artist)
                
                # Si se encontraron las letras, formatear la salida
                if result["status"]:
                    logger.info(f"Letras encontradas para '{title}' por '{artist}'")
                    
                    # Formatear la información de la canción
                    formatted_title = title.title()
                    formatted_artist = artist.title()
                    
                    # Formatear las letras
                    lyrics = result["lyrics"]
                    
                    return {
                        "status": True,
                        "title": formatted_title,
                        "artist": formatted_artist,
                        "lyrics": lyrics
                    }
                
                # Si no se encontraron las letras pero no es un error de conexión, no reintentar
                if "No se encontraron letras" in result.get("error", ""):
                    logger.warning(f"No se encontraron letras para '{title}' por '{artist}'")
                    return result
                
                # Si es otro tipo de error, esperar y reintentar
                logger.warning(f"Error al obtener letras (intento {attempt}): {result.get('error', 'Error desconocido')}")
                
                if attempt < self.max_retries:
                    logger.info(f"Esperando {self.retry_delay} segundos antes de reintentar...")
                    time.sleep(self.retry_delay)
            
            except Exception as e:
                logger.error(f"Excepción al obtener letras (intento {attempt}): {str(e)}")
                
                if attempt < self.max_retries:
                    logger.info(f"Esperando {self.retry_delay} segundos antes de reintentar...")
                    time.sleep(self.retry_delay)
        
        # Si se agotaron los reintentos, devolver error
        error_msg = f"No se pudieron obtener las letras después de {self.max_retries} intentos"
        logger.error(error_msg)
        return {
            "status": False,
            "error": error_msg
        }
    
    def format_lyrics_output(self, result):
        """
        Formatea el resultado de la búsqueda de letras para mostrar en consola
        
        Args:
            result (dict): Resultado de la búsqueda de letras
            
        Returns:
            str: Texto formateado para mostrar
        """
        if result["status"]:
            output = f"\n{'=' * 50}\n"
            output += f"TÍTULO: {result['title']}\n"
            output += f"ARTISTA: {result['artist']}\n"
            output += f"{'=' * 50}\n\n"
            output += result['lyrics']
            output += f"\n\n{'=' * 50}\n"
            return output
        else:
            return f"\nError: {result['error']}\n"
