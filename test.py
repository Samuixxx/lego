import requests
from googleapiclient.discovery import build
import cv2
import numpy as np
from io import BytesIO
from PIL import Image

# Impostazioni per l'API Custom Search
API_KEY = 'YOUR_GOOGLE_API_KEY'
CX = 'YOUR_CUSTOM_SEARCH_ENGINE_ID'

# Funzione per scaricare l'immagine da una URL
def download_image(url):
    try:
        response = requests.get(url)
        img = Image.open(BytesIO(response.content))
        img = np.array(img)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return img
    except Exception as e:
        print(f"Errore nel download dell'immagine: {e}")
        return None

# Funzione per ottenere URL immagini da Google Custom Search
def get_image_urls(query, num_images=5):
    service = build("customsearch", "v1", developerKey=API_KEY)
    res = service.cse().list(q=query, cx=CX, searchType="image", num=num_images).execute()
    
    image_urls = []
    if 'items' in res:
        for item in res['items']:
            image_urls.append(item['link'])
    return image_urls

# Preparare il pattern di scacchiera (dimensioni dei quadrati in millimetri)
pattern_size = (9, 6)  # Numero di intersezioni nel pattern (9x6)
square_size = 25  # Dimensione di un quadrato in millimetri

# Preparare gli oggetti 3D di riferimento (come punti 3D)
object_points = np.zeros((np.prod(pattern_size), 3), np.float32)
object_points[:, :2] = np.indices(pattern_size).T.reshape(-1, 2) * square_size

# Liste per punti 3D e 2D
obj_points = []  # Punti 3D nell'oggetto
img_points = []  # Punti 2D nell'immagine

# Cerca immagini di scacchiera su Google e scarica i risultati
search_query = "chessboard pattern"
image_urls = get_image_urls(search_query)

# Scarica e analizza ogni immagine trovata
for url in image_urls:
    print(f"Scaricando immagine da: {url}")
    img = download_image(url)

    if img is not None:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Trova i punti del pattern di scacchiera
        ret, corners = cv2.findChessboardCorners(gray, pattern_size, None)

        if ret:
            obj_points.append(object_points)
            img_points.append(corners)

            # Disegna i punti trovati
            cv2.drawChessboardCorners(img, pattern_size, corners, ret)
            cv2.imshow('img', img)
            cv2.waitKey(500)
        else:
            print(f"Nessun pattern trovato in: {url}")
    else:
        print(f"Immagine non valida da URL: {url}")

cv2.destroyAllWindows()

# Calibrazione della fotocamera
if len(obj_points) > 0:
    ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(obj_points, img_points, gray.shape[::-1], None, None)
    print("Matrice della fotocamera:")
    print(mtx)
else:
    print("Errore: Nessun pattern trovato nelle immagini per la calibrazione.")
