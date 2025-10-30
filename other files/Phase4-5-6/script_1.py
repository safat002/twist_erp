
# Create Django app configs for Phase 4-6 modules

# Form Builder app config
form_builder_apps = """from django.apps import AppConfig

class FormBuilderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.form_builder'
    verbose_name = 'Form & Module Builder'
    
    def ready(self):
        import apps.form_builder.signals
"""

# Workflows app config
workflows_apps = """from django.apps import AppConfig

class WorkflowsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.workflows'
    verbose_name = 'Workflow Automation'
    
    def ready(self):
        import apps.workflows.signals
"""

# AI Companion app config
ai_companion_apps = """from django.apps import AppConfig

class AICompanionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai_companion'
    verbose_name = 'AI Companion'
    
    def ready(self):
        import apps.ai_companion.signals
        # Initialize AI models on startup
        from apps.ai_companion.services import ai_service
"""

# Assets app config
assets_apps = """from django.apps import AppConfig

class AssetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.assets'
    verbose_name = 'Asset Management'
    
    def ready(self):
        import apps.assets.signals
"""

# Budgeting app config
budgeting_apps = """from django.apps import AppConfig

class BudgetingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.budgeting'
    verbose_name = 'Cost Centers & Budgeting'
    
    def ready(self):
        import apps.budgeting.signals
"""

# HR app config
hr_apps = """from django.apps import AppConfig

class HRConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.hr'
    verbose_name = 'Human Resources & Payroll'
    
    def ready(self):
        import apps.hr.signals
"""

# Projects app config
projects_apps = """from django.apps import AppConfig

class ProjectsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.projects'
    verbose_name = 'Project Management'
    
    def ready(self):
        import apps.projects.signals
"""

files = {
    'form_builder_apps.py': form_builder_apps,
    'workflows_apps.py': workflows_apps,
    'ai_companion_apps.py': ai_companion_apps,
    'assets_apps.py': assets_apps,
    'budgeting_apps.py': budgeting_apps,
    'hr_apps.py': hr_apps,
    'projects_apps.py': projects_apps,
}

for filename, content in files.items():
    with open(filename, 'w') as f:
        f.write(content)

print("✓ Created Django app configuration files:")
for f in files.keys():
    print(f"  - {f}")
