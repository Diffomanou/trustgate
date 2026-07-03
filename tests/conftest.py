"""
FR : Configuration globale de pytest. Ce fichier est automatiquement chargé
     par pytest avant tout test. Il s'assure que le répertoire racine du
     projet est dans sys.path, ce qui évite les ImportError même si on
     lance pytest depuis un sous-dossier.

EN : Global pytest configuration. This file is automatically loaded by pytest
     before any test. It ensures the project root directory is in sys.path,
     which prevents ImportError even when pytest is run from a subdirectory.
"""
import sys
import os

# FR : Ajoute la racine du projet à sys.path une fois pour toutes.
# EN : Add the project root to sys.path once and for all.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
