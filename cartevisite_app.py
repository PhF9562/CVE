"""Point d'entrée pour la construction de l'exécutable (PyInstaller).

PyInstaller fige ce script comme module ``__main__`` ; on utilise donc des
imports absolus (et non relatifs) pour lancer l'interface graphique.
"""

from cartevisite.gui import main

if __name__ == "__main__":
    main()
