"""Capture d'une photo via la webcam (optionnel, basé sur OpenCV).

Une petite fenêtre de prévisualisation s'ouvre ; l'utilisateur appuie sur
*Espace* pour capturer, ou *Échap* pour annuler. L'image est enregistrée dans
un fichier temporaire dont le chemin est renvoyé.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional


def capture_to_temp(camera_index: int = 0) -> Optional[str]:
    """Ouvre la caméra, capture une image et renvoie le chemin du fichier.

    Renvoie ``None`` si l'utilisateur annule la capture.
    Lève une ``RuntimeError`` si la caméra est indisponible.
    """
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError(
            "OpenCV (opencv-python) est requis pour la prise de photo."
        ) from exc

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        raise RuntimeError("Aucune caméra détectée sur cet appareil.")

    window = "Prendre une photo - Espace: capturer, Echap: annuler"
    saved_path: Optional[str] = None
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError("Impossible de lire le flux de la caméra.")
            cv2.imshow(window, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # Échap
                break
            if key == 32:  # Espace
                tmp = tempfile.NamedTemporaryFile(
                    suffix=".png", delete=False
                )
                tmp.close()
                cv2.imwrite(tmp.name, frame)
                saved_path = tmp.name
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()

    return saved_path
