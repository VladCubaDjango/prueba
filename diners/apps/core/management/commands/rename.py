import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Rename a Django project'

    # Entry point for subclassed commands to add custom arguments.
    def add_arguments(self, parser):
        parser.add_argument(
            'current',
            type=str,
            help='The current Django project name'
        )
        parser.add_argument(
            'new',
            type=str,
            help='The new Django project name'
        )

    # The actual logic of the command. Subclasses must implement this method.
    def handle(self, *args, **kwargs):
        current_project_name = kwargs['current']
        new_project_name = kwargs['new']

        files_to_rename = [
            f'{current_project_name}/settings/base.py',
            f'{current_project_name}/wsgi.py',
            f'{current_project_name}/apps/core/apps.py',
            'manage.py'
        ]

        # open each one files of file_to_rename
        for f in files_to_rename:
            # read file data in read mode ('r')
            with open(f, 'r') as file:
                filedata = file.read()

            # replacing data with new project name, in read data
            filedata = filedata.replace(current_project_name, new_project_name)

            # write file data in write mode ('w') with new data
            with open(f, 'w') as file:
                file.write(filedata)

        os.rename(current_project_name, new_project_name)

        self.stdout.write(
            self.style.SUCCESS('Project has been renamed to %s' % new_project_name))
