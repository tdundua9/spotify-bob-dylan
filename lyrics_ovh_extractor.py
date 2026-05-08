import requests
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("lyrics_retriever.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("LyricsOvhExtractor")

class LyricsOvhExtractor:
    """
    Clase para extraer letras de canciones usando la API de lyrics.ovh
    """
    
    def __init__(self):
        """
        Inicializa el extractor de letras con la URL base de la API
        """
        self.api_base_url = 'https://api.lyrics.ovh/v1'
    
    def get_lyrics(self, title, artist):
        """
        Obtiene las letras de una canción basada en su título y artista
        
        Args:
            title (str): Título de la canción
            artist (str): Nombre del artista o banda
            
        Returns:
            dict: Diccionario con el estado de la búsqueda y las letras o mensaje de error
        """
        try:
            # Normalizar los parámetros de búsqueda
            title = title.lower().strip()
            artist = artist.lower().strip()
            
            # Construir la URL de la API
            url = f"{self.api_base_url}/{artist}/{title}"
            logger.info(f"Consultando API: {url}")
            
            # Realizar la solicitud a la API
            response = requests.get(url)
            
            # Verificar si la solicitud fue exitosa
            if response.status_code == 200:
                data = response.json()
                
                # Verificar si se encontraron letras
                if 'lyrics' in data and data['lyrics']:
                    logger.info(f"Letras encontradas para '{title}' por '{artist}'")
                    return {
                        "status": True,
                        "title": title,
                        "artist": artist,
                        "lyrics": data['lyrics']
                    }
                else:
                    logger.warning(f"La API no devolvió letras para '{title}' por '{artist}'")
                    return {
                        "status": False,
                        "error": "No se encontraron letras para esta canción"
                    }
            elif response.status_code == 404:
                logger.warning(f"No se encontraron letras para '{title}' por '{artist}'")
                return {
                    "status": False,
                    "error": "No se encontraron letras para esta canción"
                }
            else:
                logger.error(f"Error al consultar la API: Código {response.status_code}")
                return {
                    "status": False,
                    "error": f"Error al consultar la API: Código {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Error inesperado: {str(e)}")
            return {
                "status": False,
                "error": f"Error inesperado: {str(e)}"
            }
