import logging
import os
from contextlib import suppress
from pathlib import Path
from shutil import copytree, ignore_patterns, make_archive, rmtree

import click
from click import ClickException

from yappa.packaging.common import validate_requirements_file
from yappa.settings import (
    DEFAULT_CONFIG_FILENAME, DEFAULT_IGNORED_FILES,
    DEFAULT_PACKAGE_DIR,
    DEFAULT_REQUIREMENTS_FILE,
    HANDLERS_DIR, )
from yappa.utils import get_yc_entrypoint, load_yaml

logger = logging.getLogger(__name__)


def prepare_package(requirements_file=DEFAULT_REQUIREMENTS_FILE,
                    ignored_files=DEFAULT_IGNORED_FILES,
                    config_filename=DEFAULT_CONFIG_FILENAME,
                    tmp_dir=DEFAULT_PACKAGE_DIR,
                    ):
    """
    prepares package folder
    - copy project files
    - copy handler.py
    - copy requirements file and rename it to 'requirements.txt'
    """
    if requirements_file in ignored_files:
        raise ClickException(f"Oops. {requirements_file} file should not be in"
                             f" excluded paths (at {config_filename})")
    validate_requirements_file(requirements_file)

    logger.info('Copying project files to %s', tmp_dir)
    with suppress(FileExistsError):
        os.mkdir(tmp_dir)
    copytree(os.getcwd(), tmp_dir,
             ignore=ignore_patterns(*ignored_files, tmp_dir),
             dirs_exist_ok=True)
    copytree(Path(Path(__file__).resolve().parent.parent, HANDLERS_DIR),
             Path(tmp_dir, "handlers"), dirs_exist_ok=True)
    os.rename(Path(tmp_dir, config_filename),
              Path(tmp_dir, DEFAULT_CONFIG_FILENAME))

    os.rename(Path(tmp_dir, requirements_file),
              Path(tmp_dir, "requirements.txt"))
    return tmp_dir


def create_function_version(yc, config, config_filename):
    click.echo("Preparing package...")
    package_dir = prepare_package(config["requirements_file"],
                                  config["excluded_paths"],
                                  config_filename,
                                  )
    archive_path = make_archive(package_dir, 'zip', package_dir)
    try:
        click.echo(f"Creating new function version for "
                   + click.style(config["project_slug"], bold=True))
        with open(archive_path, "rb") as f:
            content = f.read()
            function_version = yc.create_function_version(
                config["project_slug"],
                runtime=config["runtime"],
                description=config["description"],
                content=content,
                entrypoint=get_yc_entrypoint(config["application_type"],
                                             config["entrypoint"]),
                memory=config["memory_limit"],
                service_account_id=config["service_account_id"],
                timeout=config["timeout"],
                named_service_accounts=config["named_service_accounts"],
                environment=config["environment"],
            )
            click.echo(f"Created function version")
            if config["django_settings_module"]:
                click.echo("Creating new function version for management"
                           " commands")
                yc.create_function_version(
                    config["manage_function_name"],
                    runtime=config["runtime"],
                    description=config["description"],
                    content=content,
                    entrypoint=get_yc_entrypoint("manage",
                                                 config["entrypoint"]),
                    memory=config["memory_limit"],
                    service_account_id=config["service_account_id"],
                    timeout=60*10,
                    named_service_accounts=config["named_service_accounts"],
                    environment=config["environment"],
                )
    finally:
        os.remove(archive_path)
        rmtree(package_dir)
    access_changed = yc.set_function_access(
        function_name=config["project_slug"], is_public=config["is_public"])
    if access_changed:
        click.echo(f"Changed function access. Now it is "
                   f" {'not' if config['is_public'] else 'open to'} public")


