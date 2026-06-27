"""Capture d'une photo via la webcam (OpenCV).

Module optionnel : si OpenCV ou la caméra ne sont pas disponibles, les
fonctions lèvent une exception que l'interface intercepte pour proposer
l'import de fichier à la place.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional


def capture_photo(save_dir: Optional[str] = None, camera_index: int = 0) -> Optional[str]:
    """Ouvre la webcam, laisse l'utilisateur cadrer puis capture une image.

    Touches : ``Espace`` pour capturer, ``Échap`` pour annuler.

    :returns: le chemin de l'image enregistrée, ou ``None`` si annulé.
    """
    import cv2  # import paresseux : déclenche une erreur si absent

    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        raise RuntimeError("Aucune caméra détectée.")

    window = "Carte de visite - Espace: capturer / Echap: annuler"
    saved_path: Optional[str] = None
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                raise RuntimeError("Lecture du flux caméra impossible.")
            cv2.imshow(window, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  # Échap
                break
            if key == 32:  # Espace
                target_dir = Path(save_dir) if save_dir else Path(tempfile.gettempdir())
                target_dir.mkdir(parents=True, exist_ok=True)
                out = target_dir / "carte_capturee.png"
                cv2.imwrite(str(out), frame)
                saved_path = str(out)
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()
    return saved_path
