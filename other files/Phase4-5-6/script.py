
# Create additional requirements for Phase 4-6

phase4_6_requirements = """# Phase 4-6 Additional Requirements

# No-Code Form Builder (Phase 4)
jsonschema==4.20.0
django-jsonfield==1.4.1

# Workflow Engine (Phase 4)
python-statemachine==2.1.2
celery-beat==2.5.0

# AI Companion (Phase 5)
rasa==3.6.13
transformers==4.36.2
torch==2.1.2
sentence-transformers==2.2.2
chromadb==0.4.22
spacy==3.7.2
fastapi==0.108.0
uvicorn==0.25.0

# Vector Database
qdrant-client==1.7.0
faiss-cpu==1.7.4

# NLP
nltk==3.8.1
textblob==0.17.1

# Advanced Modules (Phase 6)
python-dateutil==2.8.2
holidays==0.38

# Data Science for Anomaly Detection
scikit-learn==1.3.2
numpy==1.26.2
scipy==1.11.4

# Biometric Integration (HR Module)
pyfingerprint==1.5

# Reporting
reportlab==4.0.8
xlsxwriter==3.1.9

# Task Scheduling
apscheduler==3.10.4
"""

with open('phase4-6-requirements.txt', 'w') as f:
    f.write(phase4_6_requirements.strip())

print("✓ Created phase4-6-requirements.txt")
print(f"  Total additional packages: {len([l for l in phase4_6_requirements.split('\\n') if '==' in l])}")
