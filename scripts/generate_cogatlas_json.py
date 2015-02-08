# This script will generate the cognitive atlas tasks json
# This is a json of tasks with contrasts assigned, along with description
# This should ultimately be a celery task, so the list is updated

from cognitiveatlas import views,template
import neurovault

cogat_json = os.path.join(neurovault.settings.STATIC_ROOT,"cogatlas","cognitiveatlas_tasks.json")
task_list = views.create_contrast_task_definition_json()
template.save_text(task_list,cogat_json)

# After this you will need to collect static files to move the cognitiveatlas_tasks.json into the correct place
# /opt/nv_env/NeuroVault manage.py collectstatic
