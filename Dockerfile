# ============================================================
# FR : Dockerfile pour déployer TrustGate sur Cloud Run
#      (Jour 5 du cours - "Spec-Driven Production Grade Development")
#      Image légère basée sur python:3.12-slim pour minimiser
#      le temps de build et la surface d'attaque.
#
# EN : Dockerfile for deploying TrustGate to Cloud Run
#      (Day 5 of the course - "Spec-Driven Production Grade Development")
#      Lightweight image based on python:3.12-slim to minimise
#      build time and attack surface.
# ============================================================

FROM python:3.12-slim

# FR : Métadonnées du projet (pas d'auteur pour la soumission au concours).
# EN : Project metadata (no author for competition submission).
LABEL project="TrustGate"
LABEL description="Continuous adversarial red-teaming pipeline for AI agents"
LABEL course="Kaggle 5-Day AI Agents Intensive 2026"

# FR : Crée un utilisateur non-root pour la sécurité (bonne pratique Docker).
# EN : Create a non-root user for security (Docker best practice).
RUN useradd --create-home --shell /bin/bash trustgate_user

WORKDIR /app

# FR : Copie d'abord les dépendances pour bénéficier du cache Docker.
#      Si requirements.txt ne change pas, pip install n'est pas relancé.
# EN : Copy dependencies first to leverage Docker cache.
#      If requirements.txt doesn't change, pip install is not re-run.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# FR : Copie ensuite le reste du code source.
# EN : Then copy the rest of the source code.
COPY src/ ./src/
COPY skills/ ./skills/
COPY main.py .

# FR : Crée le dossier reports/ avec les bonnes permissions.
# EN : Create the reports/ directory with correct permissions.
RUN mkdir -p reports && chown -R trustgate_user:trustgate_user /app

USER trustgate_user

# FR : PORT est la variable lue par Cloud Run. On expose 8080 par convention.
# EN : PORT is the variable read by Cloud Run. We expose 8080 by convention.
ENV PORT=8080

# FR : Lance le pipeline en mode standard. Pour une vraie API Cloud Run,
#      remplacez par : CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
# EN : Runs the pipeline in standard mode. For a real Cloud Run API,
#      replace with: CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8080"]
CMD ["python", "main.py"]
